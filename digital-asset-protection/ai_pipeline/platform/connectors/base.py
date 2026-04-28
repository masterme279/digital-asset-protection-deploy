from __future__ import annotations

from abc import ABC, abstractmethod

from ai_pipeline.platform.models import SocialPost


class PlatformConnector(ABC):
    @abstractmethod
    def fetch_latest(self, limit: int = 20) -> list[SocialPost]:
        """Fetch latest posts from a platform API and return normalized schema."""
