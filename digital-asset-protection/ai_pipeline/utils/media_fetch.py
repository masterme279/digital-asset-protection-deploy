from __future__ import annotations

import hashlib
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from ai_pipeline.utils.logger import get_logger

logger = get_logger(__name__)


_YOUTUBE_HOST_RE = re.compile(r"(^|\.)((youtube\.com)|(youtu\.be))$", re.IGNORECASE)


def is_http_url(value: str) -> bool:
    return value.startswith("http://") or value.startswith("https://")


def _safe_suffix_from_content_type(content_type: str | None) -> str:
    if not content_type:
        return ""
    content_type = content_type.split(";")[0].strip().lower()
    return {
        "image/jpeg": ".jpg",
        "image/jpg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
        "image/bmp": ".bmp",
        "video/mp4": ".mp4",
        "audio/mpeg": ".mp3",
        "audio/mp3": ".mp3",
        "audio/wav": ".wav",
        "audio/x-wav": ".wav",
        "audio/flac": ".flac",
        "audio/ogg": ".ogg",
    }.get(content_type, "")


def _url_to_cache_key(url: str) -> str:
    return hashlib.sha256(url.encode("utf-8")).hexdigest()


def _default_cache_dir() -> Path:
    # Prefer data/processed when running from repo root.
    return Path("data") / "processed" / "media_cache"


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def _host_from_url(url: str) -> str:
    # Minimal parser to avoid pulling in urllib for just netloc.
    # url is expected to start with http(s)://
    rest = url.split("//", 1)[1]
    host = rest.split("/", 1)[0]
    host = host.split(":", 1)[0]
    return host


def is_youtube_url(url: str) -> bool:
    if not is_http_url(url):
        return False
    host = _host_from_url(url)
    return bool(_YOUTUBE_HOST_RE.search(host))


@dataclass(frozen=True)
class FetchResult:
    source: str
    local_path: Path
    from_cache: bool


def ensure_local_media(
    path_or_url: str | Path,
    *,
    kind: str,
    cache_dir: Optional[Path] = None,
    timeout_sec: int = 30,
) -> FetchResult:
    """Return a local filesystem path for a URL or already-local path.

    - Local paths are returned as-is.
    - HTTP(S) URLs are downloaded to `cache_dir` and reused on subsequent calls.
    - YouTube URLs require optional `yt_dlp` for downloading.

    Parameters
    ----------
    kind: one of {"image", "video", "audio"}.
    """

    if isinstance(path_or_url, Path):
        return FetchResult(source=str(path_or_url), local_path=path_or_url, from_cache=False)

    value = str(path_or_url)
    if not is_http_url(value):
        return FetchResult(source=value, local_path=Path(value), from_cache=False)

    cache_dir = cache_dir or _default_cache_dir()
    cache_dir = Path(cache_dir)
    _ensure_dir(cache_dir)

    if kind not in {"image", "video", "audio"}:
        raise ValueError(f"Unsupported kind: {kind}")

    # Route YouTube video downloads through yt_dlp.
    if kind == "video" and is_youtube_url(value):
        return _ensure_local_youtube_video(value, cache_dir=cache_dir, timeout_sec=timeout_sec)

    return _ensure_local_http(value, kind=kind, cache_dir=cache_dir, timeout_sec=timeout_sec)


def _ensure_local_http(url: str, *, kind: str, cache_dir: Path, timeout_sec: int) -> FetchResult:
    try:
        import requests
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(
            "Downloading media URLs requires 'requests'. Install it via: pip install requests"
        ) from exc

    key = _url_to_cache_key(url)
    subdir = cache_dir / kind
    _ensure_dir(subdir)

    # Use a two-step approach: first HEAD for content-type, then GET streaming.
    content_type = None
    try:
        head = requests.head(url, allow_redirects=True, timeout=timeout_sec)
        if head.ok:
            content_type = head.headers.get("Content-Type")
    except Exception:  # noqa: BLE001
        content_type = None

    suffix = _safe_suffix_from_content_type(content_type)
    if not suffix:
        # fallback: best-effort from URL path
        suffix = Path(url.split("?", 1)[0]).suffix

    if not suffix:
        suffix = ".bin"

    dest = subdir / f"{key}{suffix}"
    if dest.exists() and dest.stat().st_size > 0:
        return FetchResult(source=url, local_path=dest, from_cache=True)

    tmp = dest.with_suffix(dest.suffix + ".tmp")
    logger.info("Downloading %s → %s", url, dest)

    with requests.get(url, stream=True, timeout=timeout_sec) as r:
        r.raise_for_status()
        with open(tmp, "wb") as f:
            for chunk in r.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    f.write(chunk)

    os.replace(tmp, dest)
    return FetchResult(source=url, local_path=dest, from_cache=False)


def _ensure_local_youtube_video(url: str, *, cache_dir: Path, timeout_sec: int) -> FetchResult:
    key = _url_to_cache_key(url)
    subdir = cache_dir / "youtube"
    _ensure_dir(subdir)

    dest = subdir / f"{key}.mp4"
    if dest.exists() and dest.stat().st_size > 0:
        return FetchResult(source=url, local_path=dest, from_cache=True)

    try:
        from yt_dlp import YoutubeDL
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(
            "YouTube downloading requires 'yt-dlp'. Install it via: pip install yt-dlp\n"
            "Note: some YouTube formats require ffmpeg installed on your machine."
        ) from exc

    logger.info("Downloading YouTube %s → %s", url, dest)

    # yt_dlp writes its own temp files; we just point it at our desired path.
    ydl_opts = {
        "outtmpl": str(dest.with_suffix("")) + ".%(ext)s",
        "format": "bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4]/best",
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "retries": 3,
        "socket_timeout": timeout_sec,
    }

    with YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

    # yt_dlp may pick a different extension; try to find the final output.
    if dest.exists() and dest.stat().st_size > 0:
        return FetchResult(source=url, local_path=dest, from_cache=False)

    candidates = sorted(subdir.glob(f"{key}.*"), key=lambda p: p.stat().st_mtime, reverse=True)
    for c in candidates:
        if c.stat().st_size > 0 and c.suffix.lower() in {".mp4", ".mkv", ".webm"}:
            # Normalize to mp4 name if possible.
            if c != dest:
                try:
                    os.replace(c, dest)
                    return FetchResult(source=url, local_path=dest, from_cache=False)
                except Exception:
                    return FetchResult(source=url, local_path=c, from_cache=False)

    raise RuntimeError("yt-dlp reported success but output file was not found")
