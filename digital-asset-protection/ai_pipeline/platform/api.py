from __future__ import annotations

from pathlib import Path
import os

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel

from ai_pipeline.platform.models import MediaType, Platform, SocialPost
from ai_pipeline.platform.service import Phase1PipelineService


class EnqueuePostRequest(BaseModel):
    platform: Platform
    post_id: str
    account_id: str
    timestamp: float
    media_type: MediaType
    media_url: str
    caption: str = ""
    hashtags: list[str] = []


def create_app(sample_root: Path) -> FastAPI:
    service = Phase1PipelineService(sample_root=sample_root)

    app = FastAPI(title="Digital Asset Protection - Phase 1")

    @app.on_event("startup")
    def on_startup() -> None:
        service.start()

    @app.on_event("shutdown")
    def on_shutdown() -> None:
        service.stop()

    @app.get("/health")
    def health() -> dict:
        return service.health()

    @app.post("/ingest/youtube/mock")
    def ingest_youtube_mock(limit: int = Query(default=20, ge=1, le=200)) -> dict:
        return service.ingest_youtube_mock(limit=limit)

    @app.get("/ingest/youtube/mock")
    def ingest_youtube_mock_get(limit: int = Query(default=20, ge=1, le=200)) -> dict:
        return service.ingest_youtube_mock(limit=limit)

    @app.post("/ingest/youtube/real")
    def ingest_youtube_real(
        limit: int = Query(default=10, ge=1, le=50),
        query: str | None = Query(default=None),
        channel_id: str | None = Query(default=None),
    ) -> dict:
        return service.ingest_youtube_real(limit=limit, query=query, channel_id=channel_id)

    @app.get("/ingest/youtube/real")
    def ingest_youtube_real_get(
        limit: int = Query(default=10, ge=1, le=50),
        query: str | None = Query(default=None),
        channel_id: str | None = Query(default=None),
    ) -> dict:
        return service.ingest_youtube_real(limit=limit, query=query, channel_id=channel_id)

    @app.post("/ingest/x/real")
    def ingest_x_real(
        limit: int = Query(default=25, ge=10, le=100),
        query: str | None = Query(default=None),
    ) -> dict:
        effective = query or os.getenv("X_QUERY", "").strip()
        if not effective:
            raise HTTPException(status_code=400, detail="Missing X query. Provide ?query=... or set X_QUERY env var.")
        return service.ingest_x_real(limit=limit, query=effective)

    @app.get("/ingest/x/real")
    def ingest_x_real_get(
        limit: int = Query(default=25, ge=10, le=100),
        query: str | None = Query(default=None),
    ) -> dict:
        effective = query or os.getenv("X_QUERY", "").strip()
        if not effective:
            raise HTTPException(status_code=400, detail="Missing X query. Provide ?query=... or set X_QUERY env var.")
        return service.ingest_x_real(limit=limit, query=effective)

    @app.post("/ingest/instagram/real")
    def ingest_instagram_real(limit: int = Query(default=10, ge=1, le=50)) -> dict:
        return service.ingest_instagram_real(limit=limit)

    @app.get("/ingest/instagram/real")
    def ingest_instagram_real_get(limit: int = Query(default=10, ge=1, le=50)) -> dict:
        return service.ingest_instagram_real(limit=limit)

    @app.post("/ingest/reddit/real")
    def ingest_reddit_real(
        limit: int = Query(default=25, ge=1, le=100),
        query: str | None = Query(default=None),
        subreddit: str | None = Query(default=None),
    ) -> dict:
        effective_query = (query or os.getenv("REDDIT_QUERY", "").strip()) or None
        effective_sub = (subreddit or os.getenv("REDDIT_SUBREDDIT", "").strip()) or None
        if not effective_query and not effective_sub:
            raise HTTPException(
                status_code=400,
                detail="Missing Reddit selector. Provide ?query=... or ?subreddit=... (or set REDDIT_QUERY / REDDIT_SUBREDDIT).",
            )
        return service.ingest_reddit_real(limit=limit, query=effective_query, subreddit=effective_sub)

    @app.get("/ingest/reddit/real")
    def ingest_reddit_real_get(
        limit: int = Query(default=25, ge=1, le=100),
        query: str | None = Query(default=None),
        subreddit: str | None = Query(default=None),
    ) -> dict:
        effective_query = (query or os.getenv("REDDIT_QUERY", "").strip()) or None
        effective_sub = (subreddit or os.getenv("REDDIT_SUBREDDIT", "").strip()) or None
        if not effective_query and not effective_sub:
            raise HTTPException(
                status_code=400,
                detail="Missing Reddit selector. Provide ?query=... or ?subreddit=... (or set REDDIT_QUERY / REDDIT_SUBREDDIT).",
            )
        return service.ingest_reddit_real(limit=limit, query=effective_query, subreddit=effective_sub)

    @app.post("/ingest/post")
    def enqueue_post(request: EnqueuePostRequest) -> dict:
        post = SocialPost(
            platform=request.platform,
            post_id=request.post_id,
            account_id=request.account_id,
            timestamp=request.timestamp,
            media_type=request.media_type,
            media_url=request.media_url,
            caption=request.caption,
            hashtags=request.hashtags,
        )
        job_id = service.enqueue_post(post)
        return {"enqueued": True, "job_id": job_id}

    @app.get("/cases")
    def list_cases(
        limit: int = Query(default=100, ge=1, le=500),
        status: str | None = None,
    ) -> dict:
        return {"items": service.list_cases(limit=limit, status=status)}

    @app.get("/cases/{case_id}")
    def get_case(case_id: str) -> dict:
        case = service.get_case(case_id)
        if not case:
            raise HTTPException(status_code=404, detail="Case not found")
        return case

    @app.get("/audit")
    def list_audit(limit: int = Query(default=100, ge=1, le=500)) -> dict:
        return {"items": service.list_audit_events(limit=limit)}

    return app
