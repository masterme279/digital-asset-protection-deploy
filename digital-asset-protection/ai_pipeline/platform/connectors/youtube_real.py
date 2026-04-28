from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Any, Optional

from ai_pipeline.platform.models import MediaType, Platform, SocialPost


@dataclass
class YouTubeFetchConfig:
    api_key: str
    query: str | None = None
    channel_id: str | None = None
    max_results: int = 10


class YouTubeRealConnector:
    """Fetches recent YouTube videos using the YouTube Data API v3.

    This connector only *discovers* content (IDs + metadata). Downloading the
    actual media is handled downstream by `ensure_local_media()` (via yt-dlp).

    Required env var (or pass explicitly):
      - YOUTUBE_API_KEY
    """

    SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = (api_key or os.getenv("YOUTUBE_API_KEY") or "").strip()

    def fetch_recent_videos(
        self,
        *,
        query: str | None = None,
        channel_id: str | None = None,
        max_results: int = 10,
        published_after: float | None = None,
    ) -> list[SocialPost]:
        if not self.api_key:
            raise RuntimeError("Missing YOUTUBE_API_KEY")

        try:
            import requests
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError("YouTube connector requires 'requests' (pip install requests)") from exc

        params: dict[str, Any] = {
            "part": "snippet",
            "type": "video",
            "order": "date",
            "maxResults": int(max(1, min(50, max_results))),
            "key": self.api_key,
        }
        if query:
            params["q"] = query
        if channel_id:
            params["channelId"] = channel_id
        if published_after:
            # YouTube expects RFC3339
            params["publishedAfter"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(published_after))

        r = requests.get(self.SEARCH_URL, params=params, timeout=30)
        r.raise_for_status()
        payload = r.json()

        posts: list[SocialPost] = []
        for item in payload.get("items", []) or []:
            vid = (item.get("id") or {}).get("videoId")
            snippet = item.get("snippet") or {}
            if not vid:
                continue

            published_at = snippet.get("publishedAt")
            ts = time.time()
            if published_at:
                # Best-effort parse: 2020-01-01T00:00:00Z
                try:
                    ts = time.mktime(time.strptime(published_at, "%Y-%m-%dT%H:%M:%SZ"))
                except Exception:
                    ts = time.time()

            channel = snippet.get("channelId") or "unknown"
            title = snippet.get("title") or ""
            desc = snippet.get("description") or ""
            caption = (title + "\n" + desc).strip()

            posts.append(
                SocialPost(
                    platform=Platform.YOUTUBE,
                    post_id=vid,
                    account_id=channel,
                    timestamp=ts,
                    media_type=MediaType.VIDEO,
                    media_url=self.video_url(vid),
                    caption=caption,
                    hashtags=[],
                )
            )

        return posts

    @staticmethod
    def video_url(video_id: str) -> str:
        return f"https://www.youtube.com/watch?v={video_id}"
