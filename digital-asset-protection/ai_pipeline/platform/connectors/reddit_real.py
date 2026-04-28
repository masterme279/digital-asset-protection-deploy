from __future__ import annotations

import os
import time
import hashlib
from typing import Any

from ai_pipeline.platform.models import MediaType, Platform, SocialPost


class RedditRealConnector:
    """Fetch recent Reddit posts via Reddit's public JSON endpoints.

    This is a polling-friendly connector similar to YouTube/X/Instagram connectors.

    Supported modes:
      - Query search:   https://www.reddit.com/search.json?q=...&sort=new
      - Subreddit feed: https://www.reddit.com/r/<subreddit>/new.json

    Notes:
      - Requires a User-Agent (REDDIT_USER_AGENT) to avoid being blocked.
      - This uses unauthenticated endpoints; expect rate limits.
      - Media URLs are returned when an image or reddit-hosted video is detected.
        Downloading is handled downstream by ensure_local_media().

    Env vars:
      - REDDIT_USER_AGENT (recommended)
    """

    BASE_URL = "https://www.reddit.com"

    def __init__(self, user_agent: str | None = None) -> None:
        self.user_agent = (user_agent or os.getenv("REDDIT_USER_AGENT") or "").strip() or (
            "digital-asset-protection/0.1 (hackathon; contact: local)"
        )

    def fetch_recent(
        self,
        *,
        query: str | None = None,
        subreddit: str | None = None,
        limit: int = 25,
        after: str | None = None,
    ) -> tuple[list[SocialPost], str | None]:
        if not query and not subreddit:
            raise RuntimeError("Provide query or subreddit")

        try:
            import requests
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError("Reddit connector requires 'requests' (pip install requests)") from exc

        limit = int(max(1, min(100, limit)))

        if subreddit:
            safe_sub = subreddit.strip().lstrip("r/").strip("/")
            url = f"{self.BASE_URL}/r/{safe_sub}/new.json"
            params: dict[str, Any] = {"limit": limit, "raw_json": 1}
        else:
            url = f"{self.BASE_URL}/search.json"
            params = {
                "q": query,
                "sort": "new",
                "limit": limit,
                "restrict_sr": 0,
                "t": "day",
                "raw_json": 1,
            }

        if after:
            params["after"] = after

        headers = {"User-Agent": self.user_agent}
        r = requests.get(url, params=params, headers=headers, timeout=30)
        r.raise_for_status()
        payload = r.json() or {}

        data = payload.get("data") or {}
        children = data.get("children") or []
        new_after = data.get("after")

        posts: list[SocialPost] = []
        for child in children:
            c = (child or {}).get("data") or {}
            post = self._to_social_post(c)
            if post is not None:
                posts.append(post)

        return posts, new_after

    @staticmethod
    def _to_social_post(c: dict[str, Any]) -> SocialPost | None:
        post_id = c.get("id") or ""
        if not post_id:
            return None

        author = c.get("author") or "unknown"
        ts = float(c.get("created_utc") or time.time())

        title = str(c.get("title") or "")
        selftext = str(c.get("selftext") or "")
        caption = (title + ("\n" + selftext if selftext else "")).strip()

        permalink = str(c.get("permalink") or "").strip()
        source_url = f"https://www.reddit.com{permalink}" if permalink.startswith("/") else ""

        media_url, media_type = RedditRealConnector._pick_media(c)
        if not media_url:
            return None

        return SocialPost(
            platform=Platform.REDDIT,
            post_id=str(post_id),
            account_id=str(author),
            timestamp=ts,
            media_type=media_type,
            media_url=str(media_url),
            source_url=source_url,
            caption=caption,
            hashtags=[],
        )

    @staticmethod
    def _pick_media(c: dict[str, Any]) -> tuple[str | None, MediaType]:
        # Prefer reddit-hosted video.
        if bool(c.get("is_video")):
            media = c.get("media") or {}
            reddit_video = (media.get("reddit_video") or {})
            fallback = reddit_video.get("fallback_url")
            if fallback:
                return str(fallback), MediaType.VIDEO

        # Image posts.
        hint = (c.get("post_hint") or "").lower()
        url = c.get("url_overridden_by_dest") or c.get("url")
        if url and hint == "image":
            return str(url), MediaType.IMAGE

        # Some posts have preview images even when hint isn't set.
        preview = c.get("preview") or {}
        imgs = preview.get("images") or []
        if imgs:
            src = ((imgs[0] or {}).get("source") or {}).get("url")
            if src:
                return str(src), MediaType.IMAGE

        return None, MediaType.IMAGE


def reddit_cursor_key(*, query: str | None, subreddit: str | None) -> str:
    """Stable SQLite key for storing the 'after' cursor per stream."""
    if subreddit:
        ident = f"subreddit:{subreddit.strip().lower()}"
    else:
        ident = f"query:{(query or '').strip().lower()}"
    digest = hashlib.sha1(ident.encode("utf-8")).hexdigest()  # noqa: S324
    return f"reddit:after:{digest}"
