import sys
import argparse
import logging
from pathlib import Path
from rich.console import Console
from rich.progress import track

# Add src to path
current_dir = Path(__file__).resolve().parent
if str(current_dir) not in sys.path:
    sys.path.append(str(current_dir))

from store.db import init_db, get_db_connection
from store.parquet import ParquetArticleStore
from store.text_store import TextArticleStore

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("rebuild_parquet")
console = Console()

def rebuild_parquet(batch_size: int = 1000):
    """Rebuild Parquet shards from Text Files + SQLite Metadata."""

    # 1. Initialize Stores
    text_store = TextArticleStore()
    parquet_store = ParquetArticleStore() # Will append new shards

    # Check if we should delete existing parquet?
    # Usually 'rebuild' implies clearing old data.
    # For safety, let's ask user or just overwrite if we were smarter, but ParquetArticleStore appends.
    # We should probably clear the 'data/articles/*.parquet' files first.

    parquet_dir = parquet_store.shard_dir
    existing_shards = list(parquet_dir.glob("*.parquet"))

    if existing_shards:
        console.print(f"[yellow]Found {len(existing_shards)} existing parquet shards.[/yellow]")
        console.print("[red]Deleting existing shards to rebuild from ground truth text files...[/red]")
        for shard in existing_shards:
            try:
                shard.unlink()
            except (OSError, PermissionError) as e:
                console.print(f"[bold red]Failed to delete {shard}: {e}[/bold red]")
                return

    # 2. Get all Article IDs from Text Store
    hn_ids = text_store.list_article_ids()
    console.print(f"[green]Found {len(hn_ids)} text articles in {text_store.storage_dir}[/green]")

    if not hn_ids:
        console.print("No text articles found. Nothing to rebuild.")
        return

    # 3. Connect to DB to get metadata
    conn = get_db_connection()
    cursor = conn.cursor()

    # Prepare map of valid HN_ID -> DB Metadata
    # We need: id (url_id), hn_score, hn_comments, hn_timestamp
    console.print("[blue]Loading metadata from SQLite...[/blue]")
    cursor.execute("SELECT id, hn_id, hn_score, hn_comments, hn_timestamp, url FROM urls WHERE hn_id IS NOT NULL")

    metadata_map = {}
    for row in cursor.fetchall():
        # row is (id, hn_id, hn_score, hn_comments, hn_timestamp, url)
        metadata_map[row[1]] = {
            "url_id": row[0],
            "hn_score": row[2] or 0,
            "hn_comments": row[3] or 0,
            "hn_timestamp": row[4] or 0,
            "db_url": row[5] # fallback if not in file
        }

    conn.close()

    # 4. Iterate and Rebuild
    count = 0
    skipped = 0

    for hn_id in track(hn_ids, description="Rebuilding Parquet..."):
        meta = metadata_map.get(hn_id)
        if not meta:
            # Maybe the DB was reset but files remain?
            # We can't put it in parquet without text schema compliance (url_id etc)
            # Log warning
            # logger.warning(f"Metadata missing for HN ID {hn_id}, skipping parquet.")
            skipped += 1
            continue

        raw_article = text_store.load_article(hn_id)
        if not raw_article:
            skipped += 1
            continue

        # Merge
        # text_store returns: title, author, date, url, text

        parquet_store.add_article(
            url_id=meta["url_id"],
            url=raw_article.get("url") or meta["db_url"],
            title=raw_article.get("title"),
            author=raw_article.get("author"),
            publish_date=raw_article.get("publish_date"),
            text=raw_article.get("text") or "",
            word_count=len((raw_article.get("text") or "").split()),
            hn_id=hn_id,
            hn_score=meta["hn_score"],
            hn_comments=meta["hn_comments"],
            hn_timestamp=meta["hn_timestamp"]
        )
        count += 1

    # 5. Flush remainder
    parquet_store.flush()
    console.print(f"[bold green]Rebuild Complete![/bold green]")
    console.print(f"Processed: {count} | Skipped: {skipped}")

if __name__ == "__main__":
    rebuild_parquet()
