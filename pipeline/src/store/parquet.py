"""Parquet storage for extracted articles."""

import polars as pl
from pathlib import Path
from typing import Optional
import logging

from .paths import get_articles_dir

logger = logging.getLogger(__name__)

ARTICLE_SCHEMA = {
    "url_id": pl.Int64,
    "url": pl.String,
    "title": pl.String,
    "author": pl.String,
    "publish_date": pl.String,
    "text": pl.String,
    "word_count": pl.Int64,
    "hn_id": pl.Int64,
    "hn_score": pl.Int64,
    "hn_comments": pl.Int64,
    "hn_timestamp": pl.Int64,
}

class ParquetArticleStore:
    """Manager for storing extracted articles in Parquet shards."""

    def __init__(self, shard_dir: str | Path | None = None, shard_size: int = 200):
        """Initialize the Parquet store.

        Args:
            shard_dir: Directory to store Parquet shards
            shard_size: Number of articles per shard
        """
        self.shard_dir = get_articles_dir() if shard_dir is None else Path(shard_dir)
        self.shard_dir.mkdir(parents=True, exist_ok=True)
        self.shard_size = shard_size
        self.buffer = []

    def add_article(
        self,
        url_id: int,
        url: str,
        title: Optional[str],
        author: Optional[str],
        publish_date: Optional[str],
        text: str,
        word_count: int,
        hn_id: int,
        hn_score: int,
        hn_comments: int,
        hn_timestamp: int
    ) -> None:
        """Add an article to the buffer.

        When buffer reaches shard_size, automatically writes to a shard.
        """
        self.buffer.append({
            "url_id": url_id,
            "url": url,
            "title": title,
            "author": author,
            "publish_date": publish_date,
            "text": text,
            "word_count": word_count,
            "hn_id": hn_id,
            "hn_score": hn_score,
            "hn_comments": hn_comments,
            "hn_timestamp": hn_timestamp,
        })

        if len(self.buffer) >= self.shard_size:
            self.flush()

    def flush(self) -> Optional[str]:
        """Write buffered articles to a new Parquet shard.

        Returns:
            Path to written shard, or None if buffer is empty
        """
        if not self.buffer:
            return None

        # Create DataFrame from buffer
        try:
            # Explicitly cast to schema to avoid Null type columns if a shard has only nulls in some fields
            df = pl.DataFrame(self.buffer, schema=ARTICLE_SCHEMA)

            # Generate shard filename based on timestamp and existing files
            shard_num = len(list(self.shard_dir.glob("articles_*.parquet")))
            shard_name = f"articles_{shard_num:04d}.parquet"
            shard_path = self.shard_dir / shard_name

            # Write with compression
            df.write_parquet(
                str(shard_path),
                compression="zstd",
                compression_level=22
            )

            logger.info(f"Flushed {len(self.buffer)} articles to {shard_name}")
            self.buffer = []
            return str(shard_path)

        except Exception as e:
            logger.error(f"Failed to flush parquet buffer: {e}")
            return None

    def close(self) -> Optional[str]:
        """Flush any remaining buffered articles and close the store."""
        return self.flush()

def read_articles(shard_dir: str | Path | None = None) -> pl.LazyFrame:
    """Read all article shards as a lazy frame for efficient processing.

    Args:
        shard_dir: Directory containing Parquet shards

    Returns:
        Polars LazyFrame for lazy evaluation of all articles
    """
    shard_dir = get_articles_dir() if shard_dir is None else Path(shard_dir)
    files = list(shard_dir.glob("articles_*.parquet"))

    if not files:
        # Return empty LazyFrame with correct schema
        return pl.DataFrame([], schema=ARTICLE_SCHEMA).lazy()

    # To handle existing shards with inconsistent schemas (e.g., 'author' as Null type vs String),
    # we scan them individually and cast to the consistent schema before concatenating.
    try:
        lfs = []
        for f in files:
            lf = pl.scan_parquet(f)
            # Apply casts to ensure consistency
            lf = lf.with_columns([
                pl.col(col).cast(dtype)
                for col, dtype in ARTICLE_SCHEMA.items()
            ])
            lfs.append(lf)

        return pl.concat(lfs)
    except Exception as e:
        logger.error(f"Error reading article shards: {e}")
        # Fallback to standard scan if individual scan fails (shouldn't happen)
        shard_pattern = str(shard_dir / "articles_*.parquet")
        return pl.scan_parquet(shard_pattern)