"""
Algolia Discovery - Supplementary Story Discovery for the Catch-Up Pipeline.

Queries the Algolia HN API directly to find AI-related stories that Histre may have missed.
This supplements the Histre-based discovery with direct Algolia searches using relevant keywords.

Usage:
    python -m src.algolia_discover -v                    # Default: last 7 days, 50+ points
    python -m src.algolia_discover -v --days 14          # Extended recency window
    python -m src.algolia_discover -v --min-score 100    # Higher score threshold
    python -m src.algolia_discover -v --dry-run          # Show what would be added
"""

import sys
import io
import asyncio
import argparse
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

import aiohttp
from aiolimiter import AsyncLimiter
from tenacity import retry, stop_after_attempt, wait_exponential
from rich.console import Console
from rich.logging import RichHandler
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.table import Table

from src.store.db import init_db, migrate_database, get_db_connection

# Force UTF-8 encoding for standard output (handles piping issues on Windows)
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

# Setup Rich Console
console = Console()

# Algolia HN API Rate Limit (conservative: 5 requests per second)
rate_limiter = AsyncLimiter(5, 1)

# Keywords to search for AI-related stories
# These are searched against story titles and URLs
DISCOVERY_KEYWORDS = [
    # Core AI coding terms
    "ai coding",
    "ai programming",
    "llm code",
    "gpt code",
    "claude code",
    "copilot",
    "cursor ai",
    # Agentic / workflow terms
    "vibecoding",
    "vibe coding",
    "agentic",
    "ai agent",
    "ai workflow",
    "ai development",
    # Specific tools/models
    "chatgpt coding",
    "anthropic",
    "openai coding",
    "codex",
    "codeium",
    "tabnine",
    "sourcegraph cody",
    # Meta discussions
    "ai replacing programmers",
    "ai developers",
    "ai software engineer",
]


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
async def search_algolia(
    session: aiohttp.ClientSession,
    query: str,
    min_score: int,
    days: int,
    hits_per_page: int = 100,
) -> list[dict]:
    """
    Query Algolia's search_by_date API for stories matching the query.
    Returns list of story dictionaries with HN metadata.
    """
    api_url = "https://hn.algolia.com/api/v1/search_by_date"

    # Calculate Unix timestamp for recency filter
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
    cutoff_timestamp = int(cutoff_date.timestamp())

    params = {
        "query": query,
        "tags": "story",
        "numericFilters": f"points>{min_score},created_at_i>{cutoff_timestamp}",
        "hitsPerPage": hits_per_page,
    }

    async with rate_limiter:
        async with session.get(api_url, params=params) as response:
            if response.status != 200:
                logging.warning(f"Algolia API error {response.status} for query '{query}'")
                return []

            data = await response.json()
            hits = data.get("hits", [])

            # Filter to only stories with external URLs (not HN self-posts)
            stories = [
                hit for hit in hits
                if hit.get("url") and not hit.get("url", "").startswith("item?id=")
            ]

            return stories


def url_exists_in_db(url: str) -> bool:
    """Check if a URL already exists in the database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM urls WHERE url = ?", (url,))
    exists = cursor.fetchone() is not None
    conn.close()
    return exists


def insert_discovered_story(
    url: str,
    hn_id: int,
    hn_score: int,
    hn_comments: int,
    hn_title: str,
    hn_timestamp: int,
    hn_author: str,
) -> bool:
    """
    Insert a newly discovered story into the database.
    Returns True if inserted, False if already exists.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            INSERT INTO urls (url, hn_id, hn_score, hn_comments, hn_title, hn_timestamp, hn_author, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'resolved')
            """,
            (url, hn_id, hn_score, hn_comments, hn_title, hn_timestamp, hn_author),
        )
        conn.commit()
        return True
    except Exception:
        # URL already exists (UNIQUE constraint)
        return False
    finally:
        conn.close()


async def discover_stories(
    verbose: bool = False,
    min_score: int = 50,
    days: int = 7,
    dry_run: bool = False,
    keywords: Optional[list[str]] = None,
) -> dict:
    """
    Discover AI-related stories from Algolia that may have been missed by Histre.

    Args:
        verbose: Enable detailed logging
        min_score: Minimum HN score threshold
        days: Number of days to look back
        dry_run: If True, don't insert, just report what would be added
        keywords: Optional custom list of keywords (defaults to DISCOVERY_KEYWORDS)

    Returns:
        Statistics dictionary with counts of discovered/inserted stories
    """
    # Setup logging
    level = logging.INFO if verbose else logging.WARNING
    logging.basicConfig(
        level=level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(console=console, rich_tracebacks=True, markup=True)],
    )

    init_db()
    migrate_database()

    search_keywords = keywords or DISCOVERY_KEYWORDS

    console.print(f"[bold blue]Algolia Discovery[/bold blue]")
    console.print(f"  Keywords: {len(search_keywords)}")
    console.print(f"  Min Score: {min_score}+")
    console.print(f"  Recency: Last {days} days")
    console.print(f"  Dry Run: {dry_run}")
    console.print()

    # Track all discovered stories (deduplicated by HN ID)
    all_stories: dict[int, dict] = {}  # hn_id -> story

    stats = {
        "keywords_searched": 0,
        "stories_found": 0,
        "already_in_db": 0,
        "newly_inserted": 0,
    }

    async with aiohttp.ClientSession() as session:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console,
        ) as progress:
            task_id = progress.add_task(
                "[cyan]Searching Algolia...", total=len(search_keywords)
            )

            for keyword in search_keywords:
                stories = await search_algolia(session, keyword, min_score, days)
                stats["keywords_searched"] += 1

                for story in stories:
                    hn_id = int(story.get("objectID", 0))
                    if hn_id and hn_id not in all_stories:
                        all_stories[hn_id] = story

                progress.advance(task_id)

    stats["stories_found"] = len(all_stories)
    console.print(f"\n[bold]Found {len(all_stories)} unique stories[/bold]\n")

    # Process discovered stories
    new_stories = []

    for hn_id, story in all_stories.items():
        url = story.get("url", "")
        if not url:
            continue

        if url_exists_in_db(url):
            stats["already_in_db"] += 1
            logging.debug(f"Already in DB: {url}")
            continue

        # This is a new story!
        hn_score = story.get("points", 0) or 0
        hn_comments = story.get("num_comments", 0) or 0
        hn_title = story.get("title", "") or ""
        hn_timestamp = story.get("created_at_i", 0) or 0
        hn_author = story.get("author", "") or ""

        new_stories.append({
            "hn_id": hn_id,
            "url": url,
            "title": hn_title,
            "score": hn_score,
            "comments": hn_comments,
            "timestamp": hn_timestamp,
            "author": hn_author,
        })

    # Display new stories in a table
    if new_stories:
        table = Table(title=f"[bold green]New Stories to Add ({len(new_stories)})[/bold green]")
        table.add_column("HN ID", style="cyan")
        table.add_column("Score", justify="right", style="yellow")
        table.add_column("Title", style="white", max_width=60)
        table.add_column("Author", style="dim")

        for story in sorted(new_stories, key=lambda x: x["score"], reverse=True):
            table.add_row(
                str(story["hn_id"]),
                str(story["score"]),
                story["title"][:60] + ("..." if len(story["title"]) > 60 else ""),
                story["author"],
            )

        console.print(table)
        console.print()

    # Insert new stories (unless dry run)
    if not dry_run:
        for story in new_stories:
            inserted = insert_discovered_story(
                url=story["url"],
                hn_id=story["hn_id"],
                hn_score=story["score"],
                hn_comments=story["comments"],
                hn_title=story["title"],
                hn_timestamp=story["timestamp"],
                hn_author=story["author"],
            )
            if inserted:
                stats["newly_inserted"] += 1
                logging.info(f"[green]Inserted[/green] HN:{story['hn_id']} - {story['title'][:50]}...")
    else:
        console.print("[yellow]DRY RUN - No stories inserted[/yellow]")

    # Final summary
    console.print("\n[bold]Discovery Complete![/bold]")
    console.print(f"  Keywords searched: {stats['keywords_searched']}")
    console.print(f"  Unique stories found: {stats['stories_found']}")
    console.print(f"  Already in database: {stats['already_in_db']}")
    console.print(f"  [green]Newly inserted:[/green] {stats['newly_inserted']}")

    return stats


def main():
    """Main entry point for Algolia Discovery."""
    parser = argparse.ArgumentParser(
        description="Discover AI-related HN stories directly from Algolia.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m src.algolia_discover -v                    # Default settings
  python -m src.algolia_discover -v --days 14          # Last 14 days
  python -m src.algolia_discover -v --min-score 100    # Higher threshold
  python -m src.algolia_discover --dry-run             # Preview only
""",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable verbose logging"
    )
    parser.add_argument(
        "--min-score",
        type=int,
        default=50,
        help="Minimum HN score threshold (default: 50)",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=7,
        help="Number of days to look back (default: 7)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be added without inserting",
    )

    args = parser.parse_args()

    asyncio.run(
        discover_stories(
            verbose=args.verbose,
            min_score=args.min_score,
            days=args.days,
            dry_run=args.dry_run,
        )
    )


if __name__ == "__main__":
    main()
