from __future__ import annotations

import os
import time
from typing import Any

from ai_pipeline.platform.models import MediaType, Platform, SocialPost


class InstagramRealConnector:
    """Fetches recent Instagram media via the Instagram Graph API.

    Required env vars:
      - IG_ACCESS_TOKEN
      - IG_USER_ID

    This connector returns media_url values from Graph API; downloading is done
    downstream by `ensure_local_media()`.
    """

    def __init__(self, access_token: str | None = None, user_id: str | None = None) -> None:
        self.access_token = access_token or os.getenv("IG_ACCESS_TOKEN", "").strip()
        self.user_id = user_id or os.getenv("IG_USER_ID", "").strip()

    def fetch_recent_media(
        self,
        *,
        limit: int = 10,
        since_timestamp: float | None = None,
    ) -> tuple[list[SocialPost], float | None]:
        if not self.access_token:
            raise RuntimeError("Missing IG_ACCESS_TOKEN")
        if not self.user_id:
            raise RuntimeError("Missing IG_USER_ID")

        try:
            import requests
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError("Instagram connector requires 'requests' (pip install requests)") from exc

        limit = int(max(1, min(50, limit)))

        url = f"https://graph.facebook.com/v19.0/{self.user_id}/media"
        params: dict[str, Any] = {
            "fields": "id,caption,media_type,media_url,permalink,timestamp,username",
            "limit": limit,
            "access_token": self.access_token,
        }

        r = requests.get(url, params=params, timeout=30)
        r.raise_for_status()
        payload = r.json()

        posts: list[SocialPost] = []
        newest_ts: float | None = since_timestamp

        for item in payload.get("data", []) or []:
            mid = item.get("id")
            if not mid:
                continue

            media_url = item.get("media_url")
            mtype = (item.get("media_type") or "").upper()
            if not media_url:
                continue

            ts = time.time()
            raw_ts = item.get("timestamp")
            if raw_ts:
                try:
                    ts = time.mktime(time.strptime(raw_ts, "%Y-%m-%dT%H:%M:%S%z"))
                except Exception:
                    try:
                        ts = time.mktime(time.strptime(raw_ts, "%Y-%m-%dT%H:%M:%S%z"))
                    except Exception:
                        ts = time.time()

            if since_timestamp and ts <= since_timestamp:
                continue

            if newest_ts is None or ts > newest_ts:
                newest_ts = ts

            media_type = MediaType.IMAGE
            if mtype in {"VIDEO"}:
                media_type = MediaType.VIDEO
            elif mtype in {"IMAGE"}:
                media_type = MediaType.IMAGE
            elif mtype in {"CAROUSEL_ALBUM"}:
                # Without fetching children, treat as image for now.
                media_type = MediaType.IMAGE

            posts.append(
                SocialPost(
                    platform=Platform.INSTAGRAM,
                    post_id=str(mid),
                    account_id=str(item.get("username") or self.user_id),
                    timestamp=ts,
                    media_type=media_type,
                    media_url=str(media_url),
                    source_url=str(item.get("permalink") or ""),
                    caption=str(item.get("caption") or ""),
                    hashtags=[],
                )
            )

        return posts, newest_ts
