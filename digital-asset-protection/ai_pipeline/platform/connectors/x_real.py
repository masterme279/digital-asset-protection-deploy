from __future__ import annotations

import os
import time
from typing import Any

from ai_pipeline.platform.models import MediaType, Platform, SocialPost


class XRealConnector:
    """Fetches recent posts from X (Twitter) API v2.

    Required env var:
      - X_BEARER_TOKEN

    Notes:
      - This uses the recent search endpoint (limited window).
      - Media URLs require expansions; this connector returns the first media URL
        (photo/video) when available.
    """

    SEARCH_URL = "https://api.x.com/2/tweets/search/recent"

    def __init__(self, bearer_token: str | None = None) -> None:
        self.bearer_token = bearer_token or os.getenv("X_BEARER_TOKEN", "").strip()

    def fetch_recent(
        self,
        *,
        query: str,
        max_results: int = 10,
        since_id: str | None = None,
    ) -> tuple[list[SocialPost], str | None]:
        if not self.bearer_token:
            raise RuntimeError("Missing X_BEARER_TOKEN")

        try:
            import requests
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError("X connector requires 'requests' (pip install requests)") from exc

        max_results = int(max(10, min(100, max_results)))

        params: dict[str, Any] = {
            "query": query,
            "max_results": max_results,
            "tweet.fields": "created_at,author_id,attachments",
            "expansions": "attachments.media_keys,author_id",
            "media.fields": "type,url,preview_image_url,variants",
            "user.fields": "username",
        }
        if since_id:
            params["since_id"] = since_id

        headers = {"Authorization": f"Bearer {self.bearer_token}"}
        r = requests.get(self.SEARCH_URL, params=params, headers=headers, timeout=30)
        r.raise_for_status()
        payload = r.json()

        users = {u.get("id"): u for u in (payload.get("includes") or {}).get("users", [])}
        media_by_key = {m.get("media_key"): m for m in (payload.get("includes") or {}).get("media", [])}

        posts: list[SocialPost] = []
        newest_id: str | None = None

        for tweet in payload.get("data", []) or []:
            tid = tweet.get("id")
            if not tid:
                continue
            if newest_id is None:
                newest_id = tid

            author_id = tweet.get("author_id") or "unknown"
            username = (users.get(author_id) or {}).get("username") or author_id

            created_at = tweet.get("created_at")
            ts = time.time()
            if created_at:
                try:
                    ts = time.mktime(time.strptime(created_at, "%Y-%m-%dT%H:%M:%S.%fZ"))
                except Exception:
                    try:
                        ts = time.mktime(time.strptime(created_at, "%Y-%m-%dT%H:%M:%SZ"))
                    except Exception:
                        ts = time.time()

            media_url, media_type = self._pick_media(tweet, media_by_key)
            if not media_url:
                continue

            posts.append(
                SocialPost(
                    platform=Platform.X,
                    post_id=tid,
                    account_id=str(username),
                    timestamp=ts,
                    media_type=media_type,
                    media_url=media_url,
                    caption=tweet.get("text", "") or "",
                    hashtags=[],
                )
            )

        return posts, newest_id

    @staticmethod
    def _pick_media(tweet: dict[str, Any], media_by_key: dict[str, Any]) -> tuple[str | None, MediaType]:
        keys = (((tweet.get("attachments") or {}).get("media_keys")) or [])
        for k in keys:
            m = media_by_key.get(k) or {}
            m_type = (m.get("type") or "").lower()

            if m_type == "photo" and m.get("url"):
                return m["url"], MediaType.IMAGE

            if m_type in {"video", "animated_gif"}:
                # Prefer an MP4 variant if present, else fallback to preview image.
                variants = m.get("variants") or []
                mp4s = [v for v in variants if (v.get("content_type") == "video/mp4" and v.get("url"))]
                if mp4s:
                    best = sorted(mp4s, key=lambda v: int(v.get("bit_rate") or 0), reverse=True)[0]
                    return best["url"], MediaType.VIDEO
                if m.get("preview_image_url"):
                    return m["preview_image_url"], MediaType.IMAGE

        return None, MediaType.IMAGE
