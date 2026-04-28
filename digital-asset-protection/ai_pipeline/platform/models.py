from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class Platform(str, Enum):
    YOUTUBE = "youtube"
    X = "x"
    INSTAGRAM = "instagram"
    REDDIT = "reddit"


class MediaType(str, Enum):
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"


@dataclass
class SocialPost:
    platform: Platform
    post_id: str
    account_id: str
    timestamp: float
    media_type: MediaType
    media_url: str
    source_url: str = ""
    caption: str = ""
    hashtags: list[str] = field(default_factory=list)


@dataclass
class IngestionJob:
    job_id: str
    post: SocialPost
    received_at: float


@dataclass
class DetectionCase:
    case_id: str
    job_id: str
    platform: str
    post_id: str
    account_id: str
    media_type: str
    media_url: str
    status: str
    confidence_tier: str
    matched_asset_id: str
    score: float
    action: str
    explanation: str
    evidence: dict[str, Any]
    created_at: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
