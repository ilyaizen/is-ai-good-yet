"""Trafilatura-based content extraction strategy."""

from typing import Optional, Dict, Any
import trafilatura
from .base import ScraperStrategy

# Type annotation for trafilatura's return type
TrafilaturaResult = Dict[str, Any]


class TrafilaturaScraper(ScraperStrategy):
    """Extract articles using trafilatura (fast, precision-focused)."""

    @property
    def name(self) -> str:
        return "trafilatura"

    async def extract(self, html: str, url: str) -> Optional[dict]:
        """Extract using trafilatura with precision settings.

        Args:
            html: Raw HTML content
            url: Article URL (unused for trafilatura)

        Returns:
            Extracted article data or None
        """
        import asyncio

        def _run_trafilatura():
            try:
                # Use favor_recall for more complete content extraction
                # no_fallback=False enables readability.js as backup
                doc = trafilatura.bare_extraction(
                    html,
                    include_comments=False,
                    include_tables=True,
                    favor_recall=True,
                    no_fallback=False,
                    with_metadata=True
                )

                # Type annotation to help Pylance understand the structure
                doc_dict: Dict[str, Any] = doc  # type: ignore

                if not doc_dict or not doc_dict.get("text"):
                    return None

                # Minimum content length requirement
                if len(doc_dict["text"]) < 100:  # type: ignore
                    return None

                return {
                    "title": doc_dict.get("title", ""),  # type: ignore
                    "author": doc_dict.get("author", ""),  # type: ignore
                    "publish_date": doc_dict.get("date", ""),  # type: ignore
                    "text": doc_dict["text"].strip(),  # type: ignore
                    "word_count": len(doc_dict["text"].split()),  # type: ignore
                }
            except Exception:
                return None

        # Run the synchronous extraction in a separate thread
        return await asyncio.get_event_loop().run_in_executor(None, _run_trafilatura)
