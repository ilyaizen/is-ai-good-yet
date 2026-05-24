"""Simple fallback scraper using lxml."""

from typing import Optional
from lxml import html as lhtml
from .base import ScraperStrategy

class SimpleScraper(ScraperStrategy):
    """Extract text using simple lxml parsing (fallback)."""

    @property
    def name(self) -> str:
        return "simple_lxml"

    async def extract(self, html_content: str, url: str) -> Optional[dict]:
        """Extract text content directly from HTML body.

        This strategy is a "dumb" fallback that just grabs all text from the body,
        removing only the most obvious non-content elements (scripts, styles, nav).
        It is useful when sophisticated extractors (Trafilatura) fail to identify
        the "main" content and return nothing.
        """
        import asyncio

        def _run_simple():
            try:
                if not html_content or len(html_content) < 100:
                    return None

                try:
                    # Parse HTML
                    tree = lhtml.fromstring(html_content)
                except Exception:
                    # Fallback for broken HTML
                    return None

                # Remove script, style, and navigation elements
                # We be conservative here - only remove things that are definitely noise
                for element in tree.xpath('//script | //style | //noscript | //header | //footer | //nav'):
                    element.drop_tree()

                # Extract text from body (or root if no body)
                body = tree.xpath('//body')
                if body:
                    text_elems = body[0].xpath('.//text()')
                else:
                    text_elems = tree.xpath('//text()')

                text = " ".join(text_elems)
                text = " ".join(text.split()) # Normalize whitespace

                if len(text) < 200:
                    return None

                # Try to find title
                title = ""
                title_elem = tree.xpath('//title/text()')
                if title_elem:
                    title = title_elem[0].strip()

                return {
                    "title": title,
                    "author": "",
                    "publish_date": "",
                    "text": text,
                    "word_count": len(text.split()),
                }
            except Exception:
                return None

        return await asyncio.get_event_loop().run_in_executor(None, _run_simple)
