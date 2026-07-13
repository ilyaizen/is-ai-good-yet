import sys
import io
import os
import asyncio
import json
import logging
import argparse
from pathlib import Path
from typing import List, Optional, Tuple

# Add parent and current directory to path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)

if current_dir not in sys.path:
    sys.path.append(current_dir)
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

import aiohttp
from aiolimiter import AsyncLimiter
from tenacity import retry, stop_after_attempt, wait_exponential
from rich.console import Console
from rich.logging import RichHandler
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, TimeRemainingColumn

from store.db import init_db, migrate_database, get_existing_urls, upsert_hn_metadata, get_failed_urls, get_urls_missing_author, get_recent_resolved_urls
from store.paths import get_data_path
from interactive import InteractiveSession

# Force UTF-8 encoding for standard output (handles piping issues on Windows)
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Setup Rich Console
console = Console()

# Algolia HN API Rate Limit (safe estimate)
# Default is 5 requests per second
rate_limiter = AsyncLimiter(5, 1)

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
async def search_hn(session: aiohttp.ClientSession, url: str) -> Tuple[Optional[int], int, int, str, int, str]:
    """
    Queries Algolia for the given URL and returns the best matching story metadata.
    Returns: (hn_id, score, comments, title, timestamp, author)
    """
    api_url = "http://hn.algolia.com/api/v1/search"
    params = {
        "query": url,
        "restrictSearchableAttributes": "url",
        "tags": "story"
    }

    async with rate_limiter:
        async with session.get(api_url, params=params) as response:
            if response.status != 200:
                logging.warning(f"Algolia API error {response.status} for {url}")
                return None, 0, 0, "", 0, ""

            data = await response.json()
            hits = data.get("hits", [])

            if not hits:
                return None, 0, 0, "", 0, ""

            # Find the "best" hit (highest score + comments)
            best_hit = max(hits, key=lambda x: (x.get("points", 0) or 0) + (x.get("num_comments", 0) or 0))

            hn_id = int(best_hit.get("objectID"))
            score = best_hit.get("points", 0) or 0
            comments = best_hit.get("num_comments", 0) or 0
            title = best_hit.get("title", "") or ""
            timestamp = best_hit.get("created_at_i", 0)
            author = best_hit.get("author", "") or ""

            return hn_id, score, comments, title, timestamp, author

async def process_url(session: aiohttp.ClientSession, url: str, progress: Progress, task_id: int) -> str:
    """
    Resolves a single URL and saves it to the DB. Updates progress bar.
    Returns: 'resolved', 'no_match', or 'error'
    """
    try:
        hn_id, score, comments, title, timestamp, author = await search_hn(session, url)

        upsert_hn_metadata(url, hn_id, score, comments, title, timestamp, author)

        if hn_id:
            logging.info(f"[green]Resolved[/green] {url} -> HN:{hn_id} (Score: {score}) | Title: {title}")
            result = 'resolved'
        else:
            logging.debug(f"No HN match for {url}")
            result = 'no_match'

    except Exception as e:
        logging.error(f"[red]Failed[/red] {url}: {e}")
        result = 'error'
    finally:
        progress.advance(task_id)  # type: ignore

    return result

async def resolve_hn_links(input_file: str, verbose: bool = False, force: bool = False, retry_failed: bool = False, fix_missing: bool = False, update_recent: bool = False, recent_days: int = 30, limit: int = 0, batch_size: int = 50, rate_limit: float = 5.0):
    """
    Reads URLs from the input JSON and resolves their Hacker News metadata via Algolia.

    When update_recent is True, refreshes hn_score and hn_comments for articles
    posted within the last recent_days days, since HN metadata continues to change.
    """
    # Setup logging
    level = logging.INFO if verbose else logging.WARNING
    logging.basicConfig(
        level=level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(console=console, rich_tracebacks=True, markup=True)]
    )

    init_db()
    migrate_database()

    # Update rate limiter if custom limit is provided
    if rate_limit != 5.0:
        global rate_limiter
        rate_limiter = AsyncLimiter(rate_limit, 1)

    input_path = Path(input_file)
    if not input_path.exists():
        console.print(f"[bold red]Input file not found:[/bold red] {input_path}")
        return

    console.print("[bold blue]Loading URLs...[/bold blue]")
    with open(input_path, "r", encoding="utf-8") as f:
        all_urls = json.load(f)

    # Simple normalization
    all_urls = [u.strip() for u in all_urls if u.strip()]

    if force:
        to_process = all_urls
        console.print(f"[bold red]Force Mode Enabled:[/bold red] Reprocessing all {len(all_urls)} URLs.")
    elif retry_failed:
        # Get URLs that are already in DB but have no HN ID (failed/no match)
        failed_urls = get_failed_urls()
        # Intersect with all_urls to ensure we only process what's in the input file
        to_process = [u for u in all_urls if u in failed_urls]

        # Also include URLs that are in input but NOT in DB at all (new ones)
        existing_urls_all = get_existing_urls()
        new_urls = [u for u in all_urls if u not in existing_urls_all]

        # Combine them (using set to avoid dupes)
        to_process = list(set(to_process + new_urls))

        console.print(f"[bold orange]Retry Mode Enabled:[/bold orange] Retrying {len(failed_urls)} failed URLs + {len(new_urls)} new URLs.")
    elif fix_missing:
        missing_urls = get_urls_missing_author()
        to_process = [u for u in all_urls if u in missing_urls]
        console.print(f"[bold magenta]Fix Missing Mode:[/bold magenta] Reprocessing {len(to_process)} URLs with missing metadata (authors).")
    elif update_recent:
        # Refresh metadata for articles within the recency window
        recent_urls = get_recent_resolved_urls(days=recent_days)
        to_process = [u for u in all_urls if u in recent_urls]
        console.print(f"[bold cyan]Update Recent Mode:[/bold cyan] Refreshing {len(to_process)} URLs from the last {recent_days} days.")
    else:
        existing_urls = get_existing_urls()
        to_process = [u for u in all_urls if u not in existing_urls]

        console.print(f"Total URLs: {len(all_urls)}. Existing: {len(existing_urls)}. [bold yellow]To process: {len(to_process)}[/bold yellow]")

    if limit > 0:
        to_process = to_process[:limit]
        console.print(f"[bold yellow]Limit applied:[/bold yellow] Processing first {limit} URLs.")

    if not to_process:
        console.print("[bold green]Nothing to process.[/bold green]")

    interactive_session = InteractiveSession(console)
    interactive_session.start()


    stats = {
        "resolved": 0,
        "no_match": 0,
        "error": 0
    }

    async with aiohttp.ClientSession() as http_session:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeRemainingColumn(),
            console=console
        ) as progress:

            task_id = progress.add_task("[cyan]Resolving HN Links...", total=len(to_process))

            # Chunking to manage concurrent tasks
            for i in range(0, len(to_process), batch_size):
                if interactive_session.check_shutdown():
                    break
                await interactive_session.wait_if_paused()

                chunk = to_process[i:i + batch_size]
                tasks = [process_url(http_session, url, progress, task_id) for url in chunk]
                results = await asyncio.gather(*tasks)

                for res in results:
                    stats[res] += 1

    console.print("\n[bold]Resolution Complete![/bold]")
    console.print(f"[green]Resolved:[/green] {stats['resolved']}")
    console.print(f"[yellow]No Match:[/yellow] {stats['no_match']}")
    if stats['error'] > 0:
        console.print(f"[red]Errors:[/red]   {stats['error']}")
    console.print(f"Total Processed: {sum(stats.values())}")

    console.print("\n[bold blue]Next Steps:[/bold blue]")
    console.print("Metadata has been saved to the SQLite database.")
    console.print("You can now run the prefilter to identify opinion pieces:")
    console.print("[white]  python pipeline/src/prefilter.py[/white]")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Resolve HN links from a JSON file.")
    default_input = str(get_data_path("histre_feed.json"))

    parser.add_argument("input_file", nargs="?", default=default_input, help="Path to the JSON file containing URLs")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose logging")
    parser.add_argument("-f", "--force", action="store_true", help="Force re-processing of all URLs")

    parser.add_argument("-r", "--retry", action="store_true", help="Retry URLs that previously failed or had no match")
    parser.add_argument("-m", "--missing", action="store_true", help="Reprocess URLs that have missing metadata (e.g. author)")
    parser.add_argument("-u", "--update-recent", action="store_true", help="Refresh score/comments for recent articles")
    parser.add_argument("--recent-days", type=int, default=30, help="Recency window in days for --update-recent (default: 30)")

    parser.add_argument("-l", "--limit", type=int, default=0, help="Limit the number of URLs to process")
    parser.add_argument("-b", "--batch-size", type=int, default=50, help="Batch size for parallel processing (default: 50)")
    parser.add_argument("--rate-limit", type=float, default=5.0, help="API rate limit in requests per second (default: 5.0)")


    args = parser.parse_args()

    asyncio.run(resolve_hn_links(args.input_file, args.verbose, args.force, args.retry, args.missing, args.update_recent, args.recent_days, args.limit, args.batch_size, args.rate_limit))