"""Newspaper3k-based content extraction strategy."""

from typing import Optional
try:
    from newspaper import Article, ArticleException
except ImportError:
    Article = None
    ArticleException = None

from .base import ScraperStrategy


class NewspaperScraper(ScraperStrategy):
    """Extract articles using newspaper3k (aggressive parsing)."""

    @property
    def name(self) -> str:
        return "newspaper3k"

    async def extract(self, html: str, url: str) -> Optional[dict]:
        """Extract using newspaper3k parser with pre-fetched HTML.

        Args:
            html: Raw HTML content (pre-fetched)
            url: Article URL (required for newspaper3k context)

        Returns:
            Extracted article data or None
        """
        import asyncio

        if Article is None:
            # newspaper3k not installed
            return None

        def _run_newspaper():
            try:
                article = Article(url) # type: ignore
                # Use pre-fetched HTML instead of fetching again
                article.download(input_html=html)
                article.parse()

                if not article.text or len(article.text) < 100:
                    return None

                return {
                    "title": article.title or "",
                    "author": ", ".join(article.authors) if article.authors else "",
                    "publish_date": article.publish_date.isoformat() if article.publish_date else "",  # type: ignore
                    "text": article.text.strip(),
                    "word_count": len(article.text.split()),
                }
            except Exception:  # Handle both ArticleException and general exceptions
                return None

        return await asyncio.get_event_loop().run_in_executor(None, _run_newspaper)
