from __future__ import annotations

import json
import sqlite3
from threading import Lock
from pathlib import Path
from typing import Any

from ai_pipeline.platform.models import DetectionCase, IngestionJob


class CaseRepository:
    def __init__(self, db_path: Path) -> None:
        self._lock = Lock()
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self._db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        with self._lock:
            cur = self._conn.cursor()
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS ingestion_jobs (
                    job_id TEXT PRIMARY KEY,
                    platform TEXT NOT NULL,
                    post_id TEXT NOT NULL,
                    account_id TEXT NOT NULL,
                    timestamp REAL NOT NULL,
                    media_type TEXT NOT NULL,
                    media_url TEXT NOT NULL,
                    source_url TEXT NOT NULL DEFAULT '',
                    caption TEXT NOT NULL,
                    hashtags_json TEXT NOT NULL,
                    received_at REAL NOT NULL
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS detection_cases (
                    case_id TEXT PRIMARY KEY,
                    job_id TEXT NOT NULL,
                    platform TEXT NOT NULL,
                    post_id TEXT NOT NULL,
                    account_id TEXT NOT NULL,
                    media_type TEXT NOT NULL,
                    media_url TEXT NOT NULL,
                    status TEXT NOT NULL,
                    confidence_tier TEXT NOT NULL,
                    matched_asset_id TEXT NOT NULL,
                    score REAL NOT NULL,
                    action TEXT NOT NULL,
                    explanation TEXT NOT NULL,
                    evidence_json TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS audit_events (
                    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    entity_type TEXT NOT NULL,
                    entity_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at REAL NOT NULL
                )
                """
            )

            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS platform_state (
                    state_key TEXT PRIMARY KEY,
                    state_value TEXT NOT NULL,
                    updated_at REAL NOT NULL
                )
                """
            )

            # Lightweight migrations for existing DBs.
            cur.execute("PRAGMA table_info(ingestion_jobs)")
            cols = {row[1] for row in cur.fetchall()}  # (cid, name, type, notnull, dflt_value, pk)
            if "source_url" not in cols:
                cur.execute("ALTER TABLE ingestion_jobs ADD COLUMN source_url TEXT NOT NULL DEFAULT ''")
            self._conn.commit()

    def get_state(self, key: str) -> str | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT state_value FROM platform_state WHERE state_key = ?",
                (key,),
            ).fetchone()
            return row["state_value"] if row else None

    def set_state(self, key: str, value: str, updated_at: float) -> None:
        with self._lock:
            self._conn.execute(
                """
                INSERT INTO platform_state (state_key, state_value, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(state_key) DO UPDATE SET
                    state_value=excluded.state_value,
                    updated_at=excluded.updated_at
                """,
                (key, value, updated_at),
            )
            self._conn.commit()

    def save_job(self, job: IngestionJob) -> None:
        with self._lock:
            self._conn.execute(
                """
                INSERT OR REPLACE INTO ingestion_jobs (
                    job_id, platform, post_id, account_id, timestamp,
                    media_type, media_url, source_url, caption, hashtags_json, received_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    job.job_id,
                    job.post.platform.value,
                    job.post.post_id,
                    job.post.account_id,
                    job.post.timestamp,
                    job.post.media_type.value,
                    job.post.media_url,
                    getattr(job.post, "source_url", ""),
                    job.post.caption,
                    json.dumps(job.post.hashtags),
                    job.received_at,
                ),
            )
            self._conn.commit()

    def add_audit_event(
        self,
        entity_type: str,
        entity_id: str,
        event_type: str,
        payload: dict[str, Any],
        created_at: float,
    ) -> None:
        with self._lock:
            self._conn.execute(
                """
                INSERT INTO audit_events (
                    entity_type, entity_id, event_type, payload_json, created_at
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    entity_type,
                    entity_id,
                    event_type,
                    json.dumps(payload),
                    created_at,
                ),
            )
            self._conn.commit()

    def upsert(self, case: DetectionCase) -> None:
        with self._lock:
            self._conn.execute(
                """
                INSERT INTO detection_cases (
                    case_id, job_id, platform, post_id, account_id, media_type,
                    media_url, status, confidence_tier, matched_asset_id, score,
                    action, explanation, evidence_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(case_id) DO UPDATE SET
                    status=excluded.status,
                    confidence_tier=excluded.confidence_tier,
                    matched_asset_id=excluded.matched_asset_id,
                    score=excluded.score,
                    action=excluded.action,
                    explanation=excluded.explanation,
                    evidence_json=excluded.evidence_json,
                    updated_at=excluded.updated_at
                """,
                (
                    case.case_id,
                    case.job_id,
                    case.platform,
                    case.post_id,
                    case.account_id,
                    case.media_type,
                    case.media_url,
                    case.status,
                    case.confidence_tier,
                    case.matched_asset_id,
                    case.score,
                    case.action,
                    case.explanation,
                    json.dumps(case.evidence),
                    case.created_at,
                    case.created_at,
                ),
            )
            self._conn.commit()

    def list_cases(self, limit: int = 100, status: str | None = None) -> list[DetectionCase]:
        with self._lock:
            if status:
                rows = self._conn.execute(
                    """
                    SELECT * FROM detection_cases
                    WHERE status = ?
                    ORDER BY created_at DESC
                    LIMIT ?
                    """,
                    (status, limit),
                ).fetchall()
            else:
                rows = self._conn.execute(
                    """
                    SELECT * FROM detection_cases
                    ORDER BY created_at DESC
                    LIMIT ?
                    """,
                    (limit,),
                ).fetchall()

            return [self._row_to_case(row) for row in rows]

    def get_case(self, case_id: str) -> DetectionCase | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM detection_cases WHERE case_id = ?",
                (case_id,),
            ).fetchone()
            return self._row_to_case(row) if row else None

    def list_audit_events(self, limit: int = 100) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._conn.execute(
                """
                SELECT event_id, entity_type, entity_id, event_type, payload_json, created_at
                FROM audit_events
                ORDER BY event_id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        events: list[dict[str, Any]] = []
        for row in rows:
            events.append(
                {
                    "event_id": row["event_id"],
                    "entity_type": row["entity_type"],
                    "entity_id": row["entity_id"],
                    "event_type": row["event_type"],
                    "payload": json.loads(row["payload_json"]),
                    "created_at": row["created_at"],
                }
            )
        return events

    @staticmethod
    def _row_to_case(row: sqlite3.Row) -> DetectionCase:
        return DetectionCase(
            case_id=row["case_id"],
            job_id=row["job_id"],
            platform=row["platform"],
            post_id=row["post_id"],
            account_id=row["account_id"],
            media_type=row["media_type"],
            media_url=row["media_url"],
            status=row["status"],
            confidence_tier=row["confidence_tier"],
            matched_asset_id=row["matched_asset_id"],
            score=row["score"],
            action=row["action"],
            explanation=row["explanation"],
            evidence=json.loads(row["evidence_json"]),
            created_at=row["created_at"],
        )
