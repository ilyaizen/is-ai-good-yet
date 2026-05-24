import logging
from pathlib import Path
from typing import Optional, List, Dict

logger = logging.getLogger(__name__)

class TextArticleStore:
    """Manager for storing scraped articles as plain text files (Ground Truth)."""

    def __init__(self, storage_dir: str | Path = "pipeline/data/articles-text"):
        """Initialize the text store.

        Args:
            storage_dir: Directory to store text files
        """
        # Resolve path relative to project root if possible
        if str(storage_dir) == "pipeline/data/articles-text":
             # ../../../.. from src/store/text_store.py to root
             self.storage_dir = Path(__file__).resolve().parent.parent.parent.parent / "pipeline" / "data" / "articles-text"
        else:
             self.storage_dir = Path(storage_dir)

        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def save_article(self, hn_id: int, title: Optional[str], author: Optional[str], date: Optional[str], url: str, text: str) -> Path:
        """Save article content to a text file.

        Format:
        Title: ...
        URL: ...

        <Body>

        Note: author and date params kept for backward compatibility but not written.
        """
        filename = self.storage_dir / f"{hn_id}.txt"

        title = title or ""
        url = url or ""
        text = text or ""

        content = f"Title: {title}\nURL: {url}\n\n{text}"

        with open(filename, "w", encoding="utf-8") as f:
            f.write(content)

        return filename

    def load_article(self, hn_id: int) -> Optional[Dict]:
        """Load article content from a text file."""
        filename = self.storage_dir / f"{hn_id}.txt"
        if not filename.exists():
            return None

        try:
            with open(filename, "r", encoding="utf-8") as f:
                content = f.read()

            # Split header and body
            parts = content.split("\n\n", 1)
            header_block = parts[0]
            body_text = parts[1] if len(parts) > 1 else ""

            metadata = {}
            for line in header_block.split("\n"):
                if ": " in line:
                    key, val = line.split(": ", 1)
                    metadata[key.lower()] = val.strip()

            return {
                "hn_id": hn_id,
                "title": metadata.get("title"),
                "author": metadata.get("author"),
                "publish_date": metadata.get("date"),
                "url": metadata.get("url"),
                "text": body_text
            }
        except Exception as e:
            logger.error(f"Error reading article {hn_id}: {e}")
            return None

    def list_article_ids(self) -> List[int]:
        """Return a list of HN IDs present in the store."""
        ids = []
        for f in self.storage_dir.glob("*.txt"):
            try:
                ids.append(int(f.stem))
            except ValueError:
                continue
        return ids
