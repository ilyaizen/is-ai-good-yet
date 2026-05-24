import sys
from pathlib import Path
from rich.console import Console
from rich.progress import track

current_dir = Path(__file__).resolve().parent
if str(current_dir) not in sys.path:
    sys.path.append(str(current_dir))

from store.db import get_db_connection
from store.text_store import TextArticleStore
from store.parquet import ParquetArticleStore

console = Console()

def get_scraped_hn_ids():
    """Get all hn_ids from DB where scraped_status = 'success'."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT hn_id FROM urls WHERE scraped_status = 'success' AND hn_id IS NOT NULL")
    ids = {row[0] for row in cursor.fetchall()}
    conn.close()
    return ids

def reset_scraped_status(hn_ids):
    """Reset scraped_status to NULL for the given hn_ids."""
    if not hn_ids:
        return 0
    conn = get_db_connection()
    cursor = conn.cursor()
    placeholders = ','.join('?' * len(hn_ids))
    cursor.execute(f"UPDATE urls SET scraped_status = NULL WHERE hn_id IN ({placeholders})", list(hn_ids))
    count = cursor.rowcount
    conn.commit()
    conn.close()
    return count

def delete_parquet_files():
    """Delete all parquet shard files."""
    parquet_dir = current_dir.parent / 'data' / 'articles'
    if not parquet_dir.exists():
        return 0
    parquet_files = list(parquet_dir.glob('*.parquet'))
    count = len(parquet_files)
    for f in parquet_files:
        f.unlink()
    return count

def rebuild_parquet_from_ground_truth():
    """Rebuild parquet from text files using existing rebuild logic."""
    text_store = TextArticleStore()
    parquet_store = ParquetArticleStore()
    
    hn_ids = text_store.list_article_ids()
    
    if not hn_ids:
        return 0
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, hn_id, hn_score, hn_comments, hn_timestamp, url FROM urls WHERE hn_id IS NOT NULL")
    
    metadata_map = {}
    for row in cursor.fetchall():
        metadata_map[row[1]] = {
            "url_id": row[0],
            "hn_score": row[2] or 0,
            "hn_comments": row[3] or 0,
            "hn_timestamp": row[4] or 0,
            "db_url": row[5]
        }
    conn.close()
    
    count = 0
    for hn_id in track(hn_ids, description="Rebuilding parquet..."):
        meta = metadata_map.get(hn_id)
        if not meta:
            continue
        
        raw_article = text_store.load_article(hn_id)
        if not raw_article:
            continue
        
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
    
    parquet_store.flush()
    return count

def main():
    console.print("[blue]Starting ground-truth uptake process...[/blue]")
    
    text_store = TextArticleStore()
    text_file_hn_ids = set(text_store.list_article_ids())
    console.print(f"[green]Found {len(text_file_hn_ids)} article text files (ground truth)[/green]")
    
    scraped_hn_ids = get_scraped_hn_ids()
    console.print(f"[blue]Found {len(scraped_hn_ids)} articles marked as scraped in DB[/blue]")
    
    missing_hn_ids = scraped_hn_ids - text_file_hn_ids
    
    if missing_hn_ids:
        console.print(f"[yellow]Found {len(missing_hn_ids)} articles deleted from ground truth[/yellow]")
        reset_count = reset_scraped_status(missing_hn_ids)
        console.print(f"[green]Reset scraped_status for {reset_count} articles[/green]")
    else:
        console.print("[green]No deleted articles found - DB is in sync[/green]")
    
    deleted_count = delete_parquet_files()
    console.print(f"[green]Deleted {deleted_count} old parquet files[/green]")
    
    rebuilt_count = rebuild_parquet_from_ground_truth()
    console.print(f"[green]Rebuilt {rebuilt_count} articles into parquet[/green]")
    
    console.print("[bold green]Ground-truth uptake complete![/bold green]")

if __name__ == '__main__':
    main()
