from __future__ import annotations

import time
import uuid
from pathlib import Path

from ai_pipeline.platform.connectors.base import PlatformConnector
from ai_pipeline.platform.models import MediaType, Platform, SocialPost


class YouTubeConnector(PlatformConnector):
    """
    Phase 1 connector with deterministic mock ingestion from local folders.

    For production, replace fetch_latest with YouTube Data API + PubSub.
    """

    def __init__(self, sample_root: Path):
        self.sample_root = Path(sample_root)

    def fetch_latest(self, limit: int = 20) -> list[SocialPost]:
        return self.fetch_mock_posts(limit=limit)

    def fetch_mock_posts(self, limit: int = 20) -> list[SocialPost]:
        posts: list[SocialPost] = []

        image_dirs = [
            self.sample_root / "image" / "positive",
            self.sample_root / "image" / "negative",
        ]
        video_dirs = [
            self.sample_root / "video" / "positive",
            self.sample_root / "video" / "negative",
        ]

        now = time.time()

        for folder in image_dirs:
            if not folder.exists():
                continue
            for path in sorted(folder.glob("*")):
                if not path.is_file():
                    continue
                posts.append(
                    SocialPost(
                        platform=Platform.YOUTUBE,
                        post_id=f"yt_img_{uuid.uuid4().hex[:10]}",
                        account_id="mock_channel",
                        timestamp=now,
                        media_type=MediaType.IMAGE,
                        media_url=str(path.resolve()),
                        caption=f"Mock image ingest: {path.name}",
                        hashtags=["#mock", "#image"],
                    )
                )

        for folder in video_dirs:
            if not folder.exists():
                continue
            for path in sorted(folder.glob("*")):
                if not path.is_file():
                    continue
                posts.append(
                    SocialPost(
                        platform=Platform.YOUTUBE,
                        post_id=f"yt_vid_{uuid.uuid4().hex[:10]}",
                        account_id="mock_channel",
                        timestamp=now,
                        media_type=MediaType.VIDEO,
                        media_url=str(path.resolve()),
                        caption=f"Mock video ingest: {path.name}",
                        hashtags=["#mock", "#video"],
                    )
                )

        return posts[:limit]
