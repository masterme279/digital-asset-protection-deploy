from __future__ import annotations

import time
import uuid
from pathlib import Path
from queue import Empty
from threading import Event
from typing import Any

from ai_pipeline.platform.models import DetectionCase, IngestionJob, MediaType
from ai_pipeline.platform.queue import JobQueue
from ai_pipeline.platform.repository import CaseRepository
from ai_pipeline.utils.logger import get_logger

logger = get_logger(__name__)


class DetectorWorker:
    IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
    VIDEO_EXTS = {".mp4", ".avi", ".mov", ".mkv", ".flv"}
    AUDIO_EXTS = {".wav", ".mp3", ".flac", ".ogg", ".aac", ".m4a", ".mp4", ".opus", ".webm"}

    def __init__(self, sample_root: Path, queue: JobQueue, repo: CaseRepository):
        self.sample_root = Path(sample_root)
        self.queue = queue
        self.repo = repo

        self._image_originals = self._list_files(
            self.sample_root / "image" / "original", self.IMAGE_EXTS
        )
        self._video_originals = self._list_files(
            self.sample_root / "video" / "original", self.VIDEO_EXTS
        )
        self._audio_originals = self._list_files(
            self.sample_root / "audio" / "original", self.AUDIO_EXTS
        )

        self._image_processor = None
        self._image_detector = None
        self._video_processor = None
        self._video_analyzer = None
        self._video_fp_cache: dict[str, dict[str, Any]] = {}

        self._audio_processor = None
        self._audio_analyzer = None
        self._audio_cache: dict[str, dict[str, Any]] = {}

        self._init_image_stack()
        self._init_video_stack()
        self._init_audio_stack()

    @staticmethod
    def _list_files(folder: Path, allowed_exts: set[str] | None = None) -> list[Path]:
        if not folder.exists():
            return []
        items = [p for p in folder.glob("*") if p.is_file()]
        if allowed_exts is not None:
            items = [p for p in items if p.suffix.lower() in allowed_exts]
        return sorted(items)

    def _init_image_stack(self) -> None:
        try:
            from ai_pipeline.image.processor import ImageProcessor
            from ai_pipeline.image.detector import ImageDetector

            self._image_processor = ImageProcessor()
            self._image_detector = ImageDetector(processor=self._image_processor)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Image detector unavailable: %s", exc)

    def _init_video_stack(self) -> None:
        try:
            from ai_pipeline.video.analyzer import VideoAnalyzer
            from ai_pipeline.video.frame_extractor import FrameExtractor
            from ai_pipeline.video.processor import VideoProcessor

            if not self._image_processor:
                from ai_pipeline.image.processor import ImageProcessor

                self._image_processor = ImageProcessor()

            self._video_processor = VideoProcessor(
                image_processor=self._image_processor,
                frame_extractor=FrameExtractor(),
            )
            self._video_analyzer = VideoAnalyzer()

            for original in self._video_originals:
                self._video_fp_cache[str(original)] = self._video_processor.fingerprint_video(original)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Video stack unavailable: %s", exc)

    def _init_audio_stack(self) -> None:
        try:
            from ai_pipeline.audio.analyzer import AudioAnalyzer
            from ai_pipeline.audio.processor import AudioProcessor

            self._audio_processor = AudioProcessor()
            # Default to CPU for broad compatibility in server mode.
            self._audio_analyzer = AudioAnalyzer(device="cpu")

            # Cache original chunks+meta once.
            for original in self._audio_originals:
                chunks, meta = self._audio_processor.process_file(original)
                self._audio_cache[str(original)] = {
                    "chunks": chunks,
                    "meta": meta,
                }
        except Exception as exc:  # noqa: BLE001
            logger.warning("Audio stack unavailable: %s", exc)

    def run_forever(self, stop_event: Event) -> None:
        while not stop_event.is_set():
            try:
                job = self.queue.get(timeout=0.5)
            except Empty:
                continue

            try:
                case = self.process_job(job)
            except Exception as exc:  # noqa: BLE001
                logger.exception("Worker failed processing job %s: %s", job.job_id, exc)
                case = self._build_error_case(
                    job,
                    "WORKER_ERROR",
                    f"Unhandled worker exception: {type(exc).__name__}: {exc}",
                )

            try:
                self.repo.upsert(case)
                self.repo.add_audit_event(
                    entity_type="case",
                    entity_id=case.case_id,
                    event_type="CASE_UPSERTED",
                    payload={
                        "job_id": case.job_id,
                        "status": case.status,
                        "score": case.score,
                        "action": case.action,
                    },
                    created_at=time.time(),
                )
            finally:
                self.queue.task_done()

    def process_job(self, job: IngestionJob) -> DetectionCase:
        if job.post.media_type == MediaType.IMAGE:
            return self._process_image(job)
        if job.post.media_type == MediaType.VIDEO:
            return self._process_video(job)
        if job.post.media_type == MediaType.AUDIO:
            return self._process_audio(job)
        return self._build_error_case(job, "UNSUPPORTED_MEDIA", "Unsupported media type")

    def _process_audio(self, job: IngestionJob) -> DetectionCase:
        if not self._audio_processor or not self._audio_analyzer:
            return self._build_error_case(job, "STACK_UNAVAILABLE", "Audio stack failed to initialize")
        if not self._audio_originals:
            return self._build_error_case(job, "NO_REFERENCES", "No audio originals found")

        try:
            from ai_pipeline.utils.media_fetch import ensure_local_media

            suspect_path = ensure_local_media(job.post.media_url, kind="audio").local_path
        except Exception as exc:  # noqa: BLE001
            return self._build_error_case(job, "FETCH_FAILED", f"Failed to fetch audio: {exc}")

        try:
            suspect_chunks, suspect_meta = self._audio_processor.process_file(suspect_path)
        except Exception as exc:  # noqa: BLE001
            return self._build_error_case(job, "PROCESS_FAILED", f"Audio processing failed: {exc}")

        best_score = -1.0
        best_report: Any | None = None
        best_original = ""

        for original in self._audio_originals:
            cached = self._audio_cache.get(str(original))
            if not cached:
                continue
            try:
                report = self._audio_analyzer.detect_piracy(
                    cached["chunks"],
                    cached["meta"],
                    suspect_chunks,
                    suspect_meta,
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning("Skipping audio reference %s: %s", original, exc)
                continue

            score = float(getattr(report, "overall_score", 0.0))
            if score > best_score:
                best_score = score
                best_report = report
                best_original = str(original)

        if best_report is None:
            return self._build_error_case(job, "NO_VALID_REFERENCES", "No valid audio references were processable")

        tier, status, action = self._tier(best_score)
        explanation = f"Matched against {best_original} with score={best_score:.4f}; verdict={getattr(best_report, 'verdict', 'UNKNOWN')}."

        report_payload: dict[str, Any]
        try:
            from dataclasses import asdict

            report_payload = asdict(best_report)
        except Exception:
            report_payload = {"repr": repr(best_report)}

        return DetectionCase(
            case_id=uuid.uuid4().hex,
            job_id=job.job_id,
            platform=job.post.platform.value,
            post_id=job.post.post_id,
            account_id=job.post.account_id,
            media_type=job.post.media_type.value,
            media_url=str(suspect_path),
            status=status,
            confidence_tier=tier,
            matched_asset_id=best_original,
            score=round(best_score, 4),
            action=action,
            explanation=explanation,
            evidence={
                "audio_report": report_payload,
                "matched_asset": best_original,
                "source_url": getattr(job.post, "source_url", ""),
            },
            created_at=time.time(),
        )

    def _process_image(self, job: IngestionJob) -> DetectionCase:
        if not self._image_detector:
            return self._build_error_case(job, "STACK_UNAVAILABLE", "Image detector failed to initialize")
        if not self._image_originals:
            return self._build_error_case(job, "NO_REFERENCES", "No image originals found")

        best_score = -1.0
        best_result: dict[str, Any] | None = None
        best_original = ""

        for original in self._image_originals:
            try:
                result = self._image_detector.compare(original, job.post.media_url)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Skipping image reference %s: %s", original, exc)
                continue
            score = float(result.get("combined_score", 0.0))
            if score > best_score:
                best_score = score
                best_result = result
                best_original = str(original)

        if best_result is None:
            return self._build_error_case(
                job,
                "NO_VALID_REFERENCES",
                "No valid image references were processable",
            )

        return self._build_case_from_result(job, best_result or {}, best_original)

    def _process_video(self, job: IngestionJob) -> DetectionCase:
        if not self._video_processor or not self._video_analyzer:
            return self._build_error_case(job, "STACK_UNAVAILABLE", "Video stack failed to initialize")
        if not self._video_originals:
            return self._build_error_case(job, "NO_REFERENCES", "No video originals found")

        query_fp = self._video_processor.fingerprint_video(job.post.media_url)

        best_score = -1.0
        best_result: dict[str, Any] | None = None
        best_original = ""

        for original in self._video_originals:
            original_key = str(original)
            original_fp = self._video_fp_cache[original_key]
            result = self._video_analyzer.compare(original_fp, query_fp)
            score = float(result.get("combined_score", 0.0))
            if score > best_score:
                best_score = score
                best_result = result
                best_original = original_key

        return self._build_case_from_result(job, best_result or {}, best_original)

    def _build_case_from_result(
        self,
        job: IngestionJob,
        result: dict[str, Any],
        matched_asset: str,
    ) -> DetectionCase:
        score = float(result.get("combined_score", 0.0))
        tier, status, action = self._tier(score)

        explanation = (
            f"Matched against {matched_asset} with score={score:.4f}; "
            f"is_match={result.get('is_match', False)}."
        )

        return DetectionCase(
            case_id=uuid.uuid4().hex,
            job_id=job.job_id,
            platform=job.post.platform.value,
            post_id=job.post.post_id,
            account_id=job.post.account_id,
            media_type=job.post.media_type.value,
            media_url=job.post.media_url,
            status=status,
            confidence_tier=tier,
            matched_asset_id=matched_asset,
            score=round(score, 4),
            action=action,
            explanation=explanation,
            evidence={
                "result": result,
                "matched_asset": matched_asset,
                "source_url": getattr(job.post, "source_url", ""),
            },
            created_at=time.time(),
        )

    def _build_error_case(self, job: IngestionJob, status: str, explanation: str) -> DetectionCase:
        return DetectionCase(
            case_id=uuid.uuid4().hex,
            job_id=job.job_id,
            platform=job.post.platform.value,
            post_id=job.post.post_id,
            account_id=job.post.account_id,
            media_type=job.post.media_type.value,
            media_url=job.post.media_url,
            status=status,
            confidence_tier="NONE",
            matched_asset_id="",
            score=0.0,
            action="IGNORE",
            explanation=explanation,
            evidence={"source_url": getattr(job.post, "source_url", "")},
            created_at=time.time(),
        )

    @staticmethod
    def _tier(score: float) -> tuple[str, str, str]:
        if score >= 0.95:
            return "HIGH", "AUTO_NOTICE", "AUTO_TAKEDOWN"
        if score >= 0.85:
            return "MEDIUM", "HUMAN_REVIEW", "FLAG_FOR_REVIEW"
        if score >= 0.75:
            return "LOW", "MONITOR", "MONITOR"
        return "NONE", "NO_MATCH", "IGNORE"
