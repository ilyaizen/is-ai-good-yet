"""Base class for scraper strategies."""

from abc import ABC, abstractmethod
from typing import Optional


class ScraperStrategy(ABC):
    """Abstract base class for content extraction strategies."""

    @abstractmethod
    async def extract(self, html: str, url: str) -> Optional[dict]:
        """Extract article data from HTML.

        Args:
            html: Raw HTML content
            url: Article URL (for context)

        Returns:
            dict with keys: title, author, publish_date, text, word_count
            or None if extraction failed
        """
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Strategy name for logging."""
        pass
