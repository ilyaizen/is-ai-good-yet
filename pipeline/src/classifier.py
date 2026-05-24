import sys
import os
import json
import logging
import asyncio
import argparse
import sqlite3
from pathlib import Path
from typing import List, Tuple, Optional, Dict, Any

"""
Local Sentiment Classifier (Phase 4 Alternative)

This script provides a local-first alternative to sentiment_analyzer.py.
While sentiment_analyzer.py uses the Groq API (online), this script uses
a local Ollama instance (offline) to perform the same Phase 4 analysis.

Key differences:
- Engine: Local Ollama (default qwen2.5:3b) vs Groq (openai/gpt-oss-20b).
- Connectivity: Requires Ollama running on localhost:11434.
- Purpose: Ideal for private, offline, or low-cost analysis.
"""

import aiohttp
from rich.console import Console
from rich.logging import RichHandler
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TaskProgressColumn,
    TimeRemainingColumn,
)
import polars as pl

# Add parent directory to path
current_dir = Path(__file__).resolve().parent
if str(current_dir) not in sys.path:
    sys.path.append(str(current_dir))

from store.db import get_db_connection, init_db
from store.parquet import read_articles
from interactive import InteractiveSession


def prepare_content_for_prompt(text: str) -> str:
    """
    Prepare text content for embedding in a JSON-like prompt format.
    - Strips/normalizes newlines (replaces with spaces)
    - Escapes double quotes
    """
    # Replace various newline types with single space
    cleaned = text.replace("\r\n", " ").replace("\r", " ").replace("\n", " ")
    # Collapse multiple spaces
    while "  " in cleaned:
        cleaned = cleaned.replace("  ", " ")
    # Escape double quotes for JSON compatibility
    cleaned = cleaned.replace('"', '\\"')
    return cleaned.strip()


# Setup Logging and Rich console for pretty output
console = Console()
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(console=console, rich_tracebacks=True, markup=True)],
)
logger = logging.getLogger("classifier")

# Local LLM Configuration (Ollama)
# This script uses the Ollama API to run LLMs locally on your own hardware.
OLLAMA_API_URL = "http://localhost:11434/api/chat"
MODEL_NAME = "qwen2.5:3b"  # Lightweight model suitable for local inference
DEFAULT_MODEL = "qwen2.5:3b"

# Classifier System Prompt (v3.0 Condensed)
SYSTEM_PROMPT = """Act as a Cynical Principal Engineer and Industry Analyst analyzing an "AI-tagged" article fragment from Hacker News (scraped and unsanitized), tasked with separating genuine engineering insights from industry hype or noise by determining whether it connects to marketing claims, practical utility or architectural impact, determine the author's stance on AI coding workflows and finally, decide if the fragment reflects a positive/neutral/negative sentiment, or mark it as `noise` if it's unrelated to opinions about AI coding workflows and tools.

## Avoid Neutral Defaulting
Do not default to neutral categories when sentiment is detectable:
- `noise` is for genuinely ambiguous content only.
- `uncertain` trajectory is for genuine uncertainty, not indecision.
- Look for signal words indicating clear sentiment.
- Signal words in author analysis require non-neutral classification.
- Signal words in factual descriptions do not require non-neutral classification.

## Signal Words (require non-neutral classification when author expresses them):
NEGATIVE: rejected, failed, broken, concern, backlash, criticism, problem, issue, flaw, frustrat, disappoint, skeptic, worry, warning
POSITIVE: love, excellent, breakthrough, revolutionary, solved, productive, efficient, game-changer, impressive, amazing

Context matters: Factual specs can be neutral; author opinions require non-neutral classification.

## Utility Categories:
- `magic`: Significantly improves productivity or solves a major problem.
- `tool`: Useful but may have minor bugs.
- `noise`: Genuinely ambiguous content.
- `toil`: Creates more work than it saves.
- `hazard`: Harmful or introduces significant risks.

### For news/essays:
- `informational`: Product launches/releases without author critique.
- `speculative`: Exploratory philosophy or opinion with no clear stance.

## Trajectory Categories:
- `optimistic`: Positive developments or beliefs.
- `pessimistic`: Negative developments or beliefs.
- `uncertain`: Only for genuine uncertainty or equal positive/negative evidence.

## Decision Examples:

| Title/Summary                           | Utility       | Trajectory  |
| --------------------------------------- | ------------- | ----------- |
| "Cursor ruined my coding workflow"      | toil          | pessimistic |
| "GPT-4o struggles with complex code"    | toil          | pessimistic |
| "AI assistants save 40% dev time"       | tool          | optimistic  |
| "Claude 3.5 Sonnet benchmarks released" | informational | uncertain   |

## Summary Guidelines:
- Good: "Anthropic's Claude Opus 4.5 excels at coding but is too expensive for heavy use."
- Bad: "Article discusses Anthropic's new model." (Vague - gives no verdict)
- The summary must express a clear verdict, not just describe the topic.

Return valid JSON only:
```json
{
  "utility": "magic" | "tool" | "informational" | "speculative" | "noise" | "toil" | "hazard",
  "trajectory": "optimistic" | "uncertain" | "pessimistic",
  "subtopic": "coding" | "model" | "society" | "tooling",
  "primary_theme": "<theme from table>",
  "secondary_theme": "<theme from table>" | null,
  "summary": "<max 25 words: blunt verdict>",
  "quotes": ["<quote 1>", "<quote 2>"]
}
```"""


def get_unclassified_urls(batch_size: int = 50) -> List[Tuple[str, str]]:
    """
    Retrieves a batch of URLs that have been successfully scraped but not yet classified.
    Returns list of tuples: (url, hn_title)
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT url, hn_title
            FROM urls
            WHERE scraped_status = 'success'
            AND sentiment_score IS NULL
            LIMIT ?
        """,
            (batch_size,),
        )
        return cursor.fetchall()
    except sqlite3.OperationalError:
        return []
    finally:
        if conn:
            conn.close()


def update_classification_result(
    url: str, sentiment_score: float, is_opinion: bool, classification_json: str
):
    """
    Updates the classification results for a given URL.
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
        UPDATE urls
        SET sentiment_score = ?, is_opinion = ?, classification_json = ?
        WHERE url = ?
        """,
            (sentiment_score, is_opinion, classification_json, url),
        )
        conn.commit()
    except sqlite3.Error as e:
        logger.error(f"Database error updating classification for {url}: {e}")
    except Exception as e:
        logger.error(f"Unexpected error updating classification for {url}: {e}")
    finally:
        if conn:
            conn.close()


async def analyze_with_ollama(
    session: aiohttp.ClientSession, text: str, title: str, model: str
) -> Optional[Dict[str, Any]]:
    """
    Sends text to Ollama for analysis.
    """
    # Truncate text if too long to avoid context window issues
    truncated_text = text[:8000]

    # Prepare title (escape quotes)
    prepared_title = (title or "Untitled").replace('"', '\\"')
    # Prepare content (strip newlines, escape quotes)
    prepared_content = prepare_content_for_prompt(truncated_text)

    user_content = f'''Article:
{{
  "title": "{prepared_title}",
  "content": "{prepared_content}"
}}'''

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
        "stream": False,
        "format": "json",
    }

    try:
        async with session.post(OLLAMA_API_URL, json=payload) as response:
            if response.status != 200:
                logger.error(f"Ollama API error: {response.status}")
                return None

            data = await response.json()
            content = data.get("message", {}).get("content", "")

            try:
                result = json.loads(content)
                return result
            except json.JSONDecodeError:
                logger.error(f"Failed to parse JSON from Ollama: {content}")
                return None
    except aiohttp.ClientError as e:
        logger.error(f"HTTP client error calling Ollama: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error calling Ollama: {e}")
        return None


def get_article_content(url_list: List[str]) -> Dict[str, str]:
    """
    Retrieves article text for the given list of URLs from Parquet store.
    """
    try:
        data_dir = current_dir.parent / "data" / "articles"
        if not data_dir.exists():
            logger.warning(f"Parquet directory not found: {data_dir}")
            return {}

        # Scan all parquet files using helper that handles schema consistency
        lf = read_articles(shard_dir=data_dir)

        filtered = lf.filter(pl.col("url").is_in(url_list)).select(["url", "text"])
        df = filtered.collect()

        # Convert to dict
        return {row["url"]: row["text"] for row in df.iter_rows(named=True)}

    except (FileNotFoundError, OSError) as e:
        logger.error(f"File system error reading parquet content: {e}")
        return {}
    except Exception as e:
        logger.error(f"Unexpected error reading parquet content: {e}")
        return {}


async def process_batch(
    session: aiohttp.ClientSession,
    batch: List[Tuple[str, str]],
    model: str,
    progress: Progress,
    task_id: int,
) -> int:
    """
    Orchestrates the analysis of a batch of URLs:
    1. Fetches full text from Parquet storage for all URLs in the batch.
    2. Iterates through each URL and title.
    3. Calls the Ollama LLM for sentiment classification.
    4. Saves the structured JSON results back to the SQLite database.
    """
    urls = [b[0] for b in batch]
    contents_map = get_article_content(urls)

    success_count = 0

    for url, title in batch:
        text = contents_map.get(url)
        if not text:
            logger.warning(f"[yellow]No content found for[/yellow] {url}")
            progress.advance(task_id)  # type: ignore
            continue

        logger.info(f"Analyzing: {title[:50]}...")
        result = await analyze_with_ollama(session, text, title, model)

        if result:
            score = result.get("sentiment_score", 0.0)
            is_op = result.get("is_opinion", False)
            quotes = result.get("key_quotes", [])

            # Save to DB
            update_classification_result(url, score, is_op, json.dumps(result))

            color = "green" if score > 0.3 else "red" if score < -0.3 else "cyan"
            logger.info(f"[{color}]Result: Score={score}, Opinion={is_op}[/{color}]")
            success_count += 1
        else:
            logger.warning(f"[red]Classification failed for[/red] {url}")

        progress.advance(task_id)  # type: ignore

    return success_count


async def main(model: str, batch_size: int, limit: int):
    init_db()

    # Check if we can connect to Ollama
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get("http://localhost:11434/") as resp:
                if resp.status == 200:
                    console.print("[green]Connected to Ollama.[/green]")
                else:
                    console.print(
                        "[red]Ollama returned unexpected status. Is it running?[/red]"
                    )
                    return
        except aiohttp.ClientError:
            console.print(
                "[red]Could not connect to Ollama (localhost:11434). Please ensure it is running.[/red]"
            )
            return
        except Exception:
            console.print(
                "[red]Unexpected error connecting to Ollama. Please ensure it is running.[/red]"
            )
            return

        interactive = InteractiveSession(console)
        interactive.start()

        total_processed = 0

        while True:
            if interactive.check_shutdown():
                break

            urls_to_process = get_unclassified_urls(batch_size)
            if not urls_to_process:
                console.print("[green]No more unclassified URLs found.[/green]")
                break

            if limit > 0 and total_processed >= limit:
                console.print(f"[yellow]Limit of {limit} reached.[/yellow]")
                break

            console.print(
                f"[bold blue]Processing batch of {len(urls_to_process)} articles...[/bold blue]"
            )

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                TimeRemainingColumn(),
                console=console,
            ) as progress:
                task = progress.add_task(
                    "[cyan]Classifying...", total=len(urls_to_process)
                )

                processed_in_batch = await process_batch(
                    session, urls_to_process, model, progress, task
                )
                total_processed += processed_in_batch

            await interactive.wait_if_paused()

    console.print(
        f"[bold green]Classification complete. Processed {total_processed} articles.[/bold green]"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Classify article sentiment using Ollama."
    )
    parser.add_argument(
        "--model", type=str, default=DEFAULT_MODEL, help="Ollama model to use"
    )
    parser.add_argument("--batch-size", type=int, default=10, help="Batch size")
    parser.add_argument(
        "--limit", type=int, default=0, help="Max articles to process (0 for infinite)"
    )

    args = parser.parse_args()

    try:
        asyncio.run(main(args.model, args.batch_size, args.limit))
    except KeyboardInterrupt:
        pass
