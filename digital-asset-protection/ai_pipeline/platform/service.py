from __future__ import annotations

import os
import time
import uuid
from pathlib import Path
from threading import Event, Thread

from ai_pipeline.platform.connectors.youtube import YouTubeConnector
from ai_pipeline.platform.connectors.youtube_real import YouTubeRealConnector
from ai_pipeline.platform.connectors.x_real import XRealConnector
from ai_pipeline.platform.connectors.instagram_real import InstagramRealConnector
from ai_pipeline.platform.connectors.reddit_real import RedditRealConnector, reddit_cursor_key
from ai_pipeline.platform.detector_worker import DetectorWorker
from ai_pipeline.platform.models import IngestionJob, SocialPost
from ai_pipeline.platform.queue import JobQueue
from ai_pipeline.platform.repository import CaseRepository


class Phase1PipelineService:
    def __init__(self, sample_root: Path):
        self.sample_root = Path(sample_root)
        self._data_root = self.sample_root.parent
        self._db_path = self._data_root / "processed" / "phase1_pipeline.db"
        self.queue = JobQueue()
        self.repo = CaseRepository(self._db_path)
        self.youtube = YouTubeConnector(self.sample_root)
        self.youtube_real = YouTubeRealConnector()
        self.x_real = XRealConnector()
        self.instagram_real = InstagramRealConnector()
        self.reddit_real = RedditRealConnector()

        self._ingest_cooldown_sec = float(os.getenv("PHASE1_INGEST_COOLDOWN_SEC", "60"))
        self._last_ingest_at: dict[str, float] = {}

        self._worker: DetectorWorker | None = None
        self._stop_event = Event()
        self._thread: Thread | None = None

        self._poller_threads: list[Thread] = []

    def _worker_main(self) -> None:
        # Heavy model/video initialization happens here so API startup is fast.
        self._worker = DetectorWorker(self.sample_root, self.queue, self.repo)
        self._worker.run_forever(self._stop_event)

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = Thread(target=self._worker_main, daemon=True)
        self._thread.start()

        if os.getenv("PHASE1_ENABLE_POLLERS", "0").strip() in {"1", "true", "True", "yes", "YES"}:
            self._start_pollers()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=2.0)
        for t in self._poller_threads:
            t.join(timeout=2.0)

    def enqueue_post(self, post: SocialPost) -> str:
        job_id = uuid.uuid4().hex
        job = IngestionJob(job_id=job_id, post=post, received_at=time.time())
        self.repo.save_job(job)
        self.repo.add_audit_event(
            entity_type="job",
            entity_id=job.job_id,
            event_type="JOB_ENQUEUED",
            payload={
                "platform": post.platform.value,
                "post_id": post.post_id,
                "media_type": post.media_type.value,
                "media_url": post.media_url,
                "source_url": getattr(post, "source_url", ""),
            },
            created_at=job.received_at,
        )
        self.queue.put(job)
        return job_id

    def enqueue_posts(self, posts: list[SocialPost]) -> list[str]:
        return [self.enqueue_post(post) for post in posts]

    def ingest_youtube_mock(self, limit: int = 20) -> dict:
        now = time.time()
        retry_after = self._cooldown_retry_after("youtube:mock", now)
        if retry_after is not None:
            self.repo.add_audit_event(
                entity_type="ingest",
                entity_id="youtube:mock",
                event_type="INGEST_DUPLICATE_BLOCKED",
                payload={
                    "requested": limit,
                    "retry_after_seconds": retry_after,
                },
                created_at=now,
            )
            return {
                "platform": "youtube",
                "mode": "mock",
                "requested": limit,
                "enqueued": 0,
                "job_ids": [],
                "dedup_blocked": True,
                "cooldown_seconds": self._ingest_cooldown_sec,
                "retry_after_seconds": retry_after,
                "message": "Duplicate ingest ignored due to cooldown guard.",
            }

        posts = self.youtube.fetch_mock_posts(limit=limit)
        job_ids = self.enqueue_posts(posts)
        self._last_ingest_at["youtube:mock"] = now
        self.repo.add_audit_event(
            entity_type="ingest",
            entity_id="youtube:mock",
            event_type="INGEST_ACCEPTED",
            payload={
                "requested": limit,
                "enqueued": len(job_ids),
            },
            created_at=now,
        )
        return {
            "platform": "youtube",
            "mode": "mock",
            "requested": limit,
            "enqueued": len(job_ids),
            "job_ids": job_ids,
            "dedup_blocked": False,
            "cooldown_seconds": self._ingest_cooldown_sec,
            "retry_after_seconds": 0,
            "message": "Ingest accepted.",
        }

    def ingest_youtube_real(
        self,
        *,
        limit: int = 10,
        query: str | None = None,
        channel_id: str | None = None,
    ) -> dict:
        now = time.time()
        retry_after = self._cooldown_retry_after("youtube:real", now)
        if retry_after is not None:
            return {
                "platform": "youtube",
                "mode": "real",
                "requested": limit,
                "enqueued": 0,
                "job_ids": [],
                "dedup_blocked": True,
                "cooldown_seconds": self._ingest_cooldown_sec,
                "retry_after_seconds": retry_after,
                "message": "Duplicate ingest ignored due to cooldown guard.",
            }

        last = self._get_state_float("youtube:published_after")
        posts = self.youtube_real.fetch_recent_videos(
            query=query,
            channel_id=channel_id,
            max_results=limit,
            published_after=last,
        )

        job_ids = self.enqueue_posts(posts)
        self._last_ingest_at["youtube:real"] = now

        if posts:
            newest = max(p.timestamp for p in posts)
            self.repo.set_state("youtube:published_after", str(newest), updated_at=now)

        self.repo.add_audit_event(
            entity_type="ingest",
            entity_id="youtube:real",
            event_type="INGEST_ACCEPTED",
            payload={"requested": limit, "enqueued": len(job_ids), "query": query, "channel_id": channel_id},
            created_at=now,
        )

        return {
            "platform": "youtube",
            "mode": "real",
            "requested": limit,
            "enqueued": len(job_ids),
            "job_ids": job_ids,
            "cursor_published_after": last,
            "dedup_blocked": False,
        }

    def ingest_x_real(self, *, limit: int = 10, query: str) -> dict:
        now = time.time()
        retry_after = self._cooldown_retry_after("x:real", now)
        if retry_after is not None:
            return {
                "platform": "x",
                "mode": "real",
                "requested": limit,
                "enqueued": 0,
                "job_ids": [],
                "dedup_blocked": True,
                "cooldown_seconds": self._ingest_cooldown_sec,
                "retry_after_seconds": retry_after,
                "message": "Duplicate ingest ignored due to cooldown guard.",
            }

        since_id = self.repo.get_state("x:since_id")
        posts, newest_id = self.x_real.fetch_recent(query=query, max_results=limit, since_id=since_id)
        job_ids = self.enqueue_posts(posts)
        self._last_ingest_at["x:real"] = now

        if newest_id:
            self.repo.set_state("x:since_id", newest_id, updated_at=now)

        self.repo.add_audit_event(
            entity_type="ingest",
            entity_id="x:real",
            event_type="INGEST_ACCEPTED",
            payload={"requested": limit, "enqueued": len(job_ids), "query": query, "since_id": since_id},
            created_at=now,
        )

        return {
            "platform": "x",
            "mode": "real",
            "requested": limit,
            "enqueued": len(job_ids),
            "job_ids": job_ids,
            "cursor_since_id": since_id,
            "cursor_newest_id": newest_id,
            "dedup_blocked": False,
        }

    def ingest_instagram_real(self, *, limit: int = 10) -> dict:
        now = time.time()
        retry_after = self._cooldown_retry_after("instagram:real", now)
        if retry_after is not None:
            return {
                "platform": "instagram",
                "mode": "real",
                "requested": limit,
                "enqueued": 0,
                "job_ids": [],
                "dedup_blocked": True,
                "cooldown_seconds": self._ingest_cooldown_sec,
                "retry_after_seconds": retry_after,
                "message": "Duplicate ingest ignored due to cooldown guard.",
            }

        since_ts = self._get_state_float("instagram:since_ts")
        posts, newest_ts = self.instagram_real.fetch_recent_media(limit=limit, since_timestamp=since_ts)
        job_ids = self.enqueue_posts(posts)
        self._last_ingest_at["instagram:real"] = now

        if newest_ts is not None:
            self.repo.set_state("instagram:since_ts", str(newest_ts), updated_at=now)

        self.repo.add_audit_event(
            entity_type="ingest",
            entity_id="instagram:real",
            event_type="INGEST_ACCEPTED",
            payload={"requested": limit, "enqueued": len(job_ids), "since_ts": since_ts},
            created_at=now,
        )

        return {
            "platform": "instagram",
            "mode": "real",
            "requested": limit,
            "enqueued": len(job_ids),
            "job_ids": job_ids,
            "cursor_since_ts": since_ts,
            "cursor_newest_ts": newest_ts,
            "dedup_blocked": False,
        }

    def ingest_reddit_real(
        self,
        *,
        limit: int = 25,
        query: str | None = None,
        subreddit: str | None = None,
    ) -> dict:
        now = time.time()
        retry_after = self._cooldown_retry_after("reddit:real", now)
        if retry_after is not None:
            return {
                "platform": "reddit",
                "mode": "real",
                "requested": limit,
                "enqueued": 0,
                "job_ids": [],
                "dedup_blocked": True,
                "cooldown_seconds": self._ingest_cooldown_sec,
                "retry_after_seconds": retry_after,
                "message": "Duplicate ingest ignored due to cooldown guard.",
            }

        key = reddit_cursor_key(query=query, subreddit=subreddit)
        after = self.repo.get_state(key)
        posts, new_after = self.reddit_real.fetch_recent(
            query=query,
            subreddit=subreddit,
            limit=limit,
            after=after,
        )

        job_ids = self.enqueue_posts(posts)
        self._last_ingest_at["reddit:real"] = now

        if new_after:
            self.repo.set_state(key, str(new_after), updated_at=now)

        self.repo.add_audit_event(
            entity_type="ingest",
            entity_id="reddit:real",
            event_type="INGEST_ACCEPTED",
            payload={
                "requested": limit,
                "enqueued": len(job_ids),
                "query": query,
                "subreddit": subreddit,
                "cursor_after": after,
                "cursor_new_after": new_after,
            },
            created_at=now,
        )

        return {
            "platform": "reddit",
            "mode": "real",
            "requested": limit,
            "enqueued": len(job_ids),
            "job_ids": job_ids,
            "cursor_after": after,
            "cursor_new_after": new_after,
            "dedup_blocked": False,
        }

    def list_cases(self, limit: int = 100, status: str | None = None) -> list[dict]:
        return [case.to_dict() for case in self.repo.list_cases(limit=limit, status=status)]

    def get_case(self, case_id: str) -> dict | None:
        case = self.repo.get_case(case_id)
        return case.to_dict() if case else None

    def health(self) -> dict:
        return {
            "worker_alive": bool(self._thread and self._thread.is_alive()),
            "queue_size": self.queue.qsize(),
            "sample_root": str(self.sample_root.resolve()),
            "db_path": str(self._db_path.resolve()),
            "pollers_enabled": os.getenv("PHASE1_ENABLE_POLLERS", "0"),
            "poller_threads": len(self._poller_threads),
        }

    def list_audit_events(self, limit: int = 100) -> list[dict]:
        return self.repo.list_audit_events(limit=limit)

    def _cooldown_retry_after(self, key: str, now: float) -> float | None:
        last = self._last_ingest_at.get(key, 0.0)
        if last <= 0:
            return None
        elapsed = now - last
        if elapsed < self._ingest_cooldown_sec:
            return round(self._ingest_cooldown_sec - elapsed, 2)
        return None

    def _get_state_float(self, key: str) -> float | None:
        raw = self.repo.get_state(key)
        if raw is None:
            return None
        try:
            return float(raw)
        except Exception:
            return None

    def _start_pollers(self) -> None:
        interval = float(os.getenv("PHASE1_POLL_INTERVAL_SEC", "30"))
        yt_query = os.getenv("YOUTUBE_QUERY", "").strip() or None
        yt_channel = os.getenv("YOUTUBE_CHANNEL_ID", "").strip() or None
        x_query = os.getenv("X_QUERY", "").strip()
        reddit_query = os.getenv("REDDIT_QUERY", "").strip() or None
        reddit_subreddit = os.getenv("REDDIT_SUBREDDIT", "").strip() or None

        def loop(name: str, fn) -> None:
            while not self._stop_event.is_set():
                try:
                    fn()
                except Exception as exc:  # noqa: BLE001
                    self.repo.add_audit_event(
                        entity_type="poller",
                        entity_id=name,
                        event_type="POLL_ERROR",
                        payload={"error": f"{type(exc).__name__}: {exc}"},
                        created_at=time.time(),
                    )
                self._stop_event.wait(timeout=interval)

        # YouTube poller
        if os.getenv("YOUTUBE_API_KEY", "").strip() and (yt_query or yt_channel):
            t = Thread(
                target=loop,
                args=(
                    "youtube:real",
                    lambda: self.ingest_youtube_real(limit=5, query=yt_query, channel_id=yt_channel),
                ),
                daemon=True,
            )
            t.start()
            self._poller_threads.append(t)

        # X poller
        if os.getenv("X_BEARER_TOKEN", "").strip() and x_query:
            t = Thread(
                target=loop,
                args=("x:real", lambda: self.ingest_x_real(limit=10, query=x_query)),
                daemon=True,
            )
            t.start()
            self._poller_threads.append(t)

        # Instagram poller
        if os.getenv("IG_ACCESS_TOKEN", "").strip() and os.getenv("IG_USER_ID", "").strip():
            t = Thread(
                target=loop,
                args=("instagram:real", lambda: self.ingest_instagram_real(limit=10)),
                daemon=True,
            )
            t.start()
            self._poller_threads.append(t)

        # Reddit poller
        if reddit_query or reddit_subreddit:
            t = Thread(
                target=loop,
                args=(
                    "reddit:real",
                    lambda: self.ingest_reddit_real(limit=25, query=reddit_query, subreddit=reddit_subreddit),
                ),
                daemon=True,
            )
            t.start()
            self._poller_threads.append(t)
