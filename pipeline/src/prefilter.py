import sys
import io
import asyncio
import logging
import argparse
import os
import signal
import json
import re
from pathlib import Path
from typing import List, Tuple, Optional, Dict, Set

import aiohttp
from aiolimiter import AsyncLimiter
from dotenv import load_dotenv
from rich.console import Console
from rich.logging import RichHandler
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, TimeRemainingColumn


# Load environment variables from .env file
env_path = Path(__file__).resolve().parent.parent.parent / '.env'
load_dotenv(env_path)

# Ensure proper path for imports (adds pipeline/src to sys.path)
current_dir = Path(__file__).resolve().parent
if str(current_dir) not in sys.path:
    sys.path.append(str(current_dir))

from store.db import (init_db, get_resolved_urls_for_prefiltering, update_prefilter_status,
                     get_prefiltered_stats, init_prefilter_state_table, get_prefilter_state,
                     save_prefilter_state, clear_prefilter_state, get_processed_urls, migrate_database)

# Force UTF-8 encoding for standard output (handles piping issues on Windows)
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Setup Rich Console
console = Console()

# Mistral API Rate Limit (safe estimate)
rate_limiter = AsyncLimiter(10, 1)  # 10 requests per second

from interactive import InteractiveSession  # noqa: F401

class CostMonitor:
    """Monitors API usage and cost efficiency."""
    def __init__(self):
        self.total_tokens = 0
        self.successful_calls = 0
        self.failed_calls = 0
        self.start_time = None

    def add_call(self, prompt_tokens: int, completion_tokens: int, success: bool):
        """Record API call metrics."""
        self.total_tokens += prompt_tokens + completion_tokens
        if success:
            self.successful_calls += 1
        else:
            self.failed_calls += 1

    def get_cost_estimate(self, cost_per_token: float = 0.000002) -> float:
        """Estimate cost based on token usage."""
        return self.total_tokens * cost_per_token

    def get_efficiency(self) -> float:
        """Calculate success rate."""
        total_calls = self.successful_calls + self.failed_calls
        return self.successful_calls / total_calls if total_calls > 0 else 0.0

    def get_processing_rate(self, current_count: int) -> float:
        """Calculate URLs per second."""
        if self.start_time is None:
            return 0.0
        try:
            elapsed = asyncio.get_event_loop().time() - self.start_time
            return current_count / elapsed if elapsed > 0 else 0.0
        except RuntimeError:
            # Event loop not available
            return 0.0

# Mistral API Configuration
MISTRAL_API_URL = "https://api.mistral.ai/v1/chat/completions"
MISTRAL_MODEL = "mistral-small-2506"  # Using the mistral-small-2506 model for cost efficiency

# Opinion Detection Prompt (Single Title - Legacy)
OPTION_DETECTION_PROMPT = """
You are an AI assistant that analyzes Hacker News article titles to determine if
they contain opinions about AI technology.

Analyze the following title and determine if it expresses an opinion about AI
(positive, negative, or neutral opinion):

Title: "{title}"

Respond with ONLY a single integer:
- 1 if the title clearly expresses an opinion about AI
- 0 if the title is factual/neutral or doesn't mention AI
- -1 if the title is unclear or ambiguous

Do not provide any explanation or additional text. Just the integer.
"""

# Opinion Detection Prompt (Batch Processing)
BATCH_OPTION_DETECTION_PROMPT = """
You are an AI assistant that analyzes Hacker News article titles to determine if
they contain opinions about AI technology.

Analyze the following list of titles (each with an ID) and determine if each
expresses an opinion about AI.

Classify each title as:
- 1 if the title clearly expresses an opinion about AI
- 0 if the title is factual/neutral or doesn't mention AI
- -1 if the title is unclear or ambiguous

Return a valid JSON object where the keys are the IDs (as strings) and the
values are the classification scores (integers).

Example Input:
1. "AI is destroying the world"
2. "New Python release 3.12"
3. "Why I think LLMs are overhyped"

Example Output:
{{
    "1": 1,
    "2": 0,
    "3": 1
}}

Titles to analyze:
{items}

Respond with ONLY the JSON object. Do not wrap it in markdown code blocks.
"""


async def analyze_title_with_mistral(session: aiohttp.ClientSession, title: str, api_key: str) -> Optional[int]:
    """
    Analyzes a title using Mistral API to determine if it contains an opinion about AI.
    Returns: 1 (opinion), 0 (neutral), -1 (unclear), or None (error)
    """
    try:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": MISTRAL_MODEL,
            "messages": [
                {
                    "role": "user",
                    "content": OPTION_DETECTION_PROMPT.format(title=title)
                }
            ],
            "temperature": 0.0,
            "max_tokens": 10
        }

        async with rate_limiter:
            async with session.post(MISTRAL_API_URL, json=payload, headers=headers) as response:
                if response.status != 200:
                    logging.error(f"Mistral API error {response.status} for title: {title}")
                    return None

                data = await response.json()
                content = data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()

                # Parse the integer response
                try:
                    return int(content)
                except ValueError:
                    logging.warning(f"Invalid response format from Mistral API: {content}")
                    return None

    except (aiohttp.ClientError, ValueError, OSError) as e:
        logging.error(f"Error analyzing title '{title}': {e}")
        return None


async def analyze_batch_with_mistral(session: aiohttp.ClientSession, items: List[Tuple[str, str]], api_key: str) -> Dict[str, int]:
    """
    Analyzes a batch of titles using Mistral API.
    Args:
        items: List of (url, title) tuples
    Returns: Dictionary mapping URL to score (1, 0, -1). Missing URLs indicate failure/skip.
    """
    # Create ID mapping for the prompt (using strings "1", "2", etc.)
    # We map "1" -> (url, title)
    id_map = {str(i+1): item for i, item in enumerate(items)}

    # Format the list for the prompt
    formatted_items = "\n".join([f'{k}. "{v[1]}"' for k, v in id_map.items()])

    try:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": MISTRAL_MODEL,
            "messages": [
                {
                    "role": "user",
                    "content": BATCH_OPTION_DETECTION_PROMPT.format(items=formatted_items)
                }
            ],
            # Allow enough tokens for the JSON response
            "max_tokens": 500,
            "temperature": 0.0,
            "response_format": {"type": "json_object"}
        }

        async with rate_limiter:
            async with session.post(MISTRAL_API_URL, json=payload, headers=headers) as response:
                if response.status != 200:
                    logging.error(f"Mistral API error {response.status} for batch")
                    # Return empty dict so individual retries or next batch can happen
                    # Alternatively, raise exception to trigger retry?
                    # For now, logging error is safer.
                    error_text = await response.text()
                    logging.debug(f"API Error Details: {error_text}")
                    return {}

                data = await response.json()
                content = data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()

                try:
                    # Clean up content if it contains markdown code blocks
                    if content.startswith("```"):
                        content = content.strip("`").replace("json\n", "", 1).strip()

                    results = json.loads(content)

                    # Map back to URL -> Score
                    url_scores = {}
                    for id_str, score in results.items():
                        if id_str in id_map:
                            url = id_map[id_str][0]
                            # Validate score is within expected range
                            if str(score) in ["1", "0", "-1"]:
                                url_scores[url] = int(score)
                            else:
                                # Default to unclear if weird score
                                logging.warning(f"Invalid score {score} for item {id_str}")
                                url_scores[url] = -1

                    return url_scores

                except json.JSONDecodeError:
                    logging.error(f"Failed to parse JSON response from Mistral: {content}")
                    return {}

    except (aiohttp.ClientError, ValueError, OSError) as e:
        logging.error(f"Error analyzing batch: {e}")
        return {}



async def process_title(session: aiohttp.ClientSession, url: str, title: str, api_key: str, progress: Progress, task_id: int) -> str:
    """
    Processes a single title through Mistral API and updates the database.
    Returns: 'success', 'error', or 'skipped'
    """
    try:
        # Analyze the title
        filter_score = await analyze_title_with_mistral(session, title, api_key)

        if filter_score is None:
            logging.warning(f"[yellow]Skipped[/yellow] {url} - API error or invalid response")
            return 'skipped'

        # Update database
        update_prefilter_status(url, filter_score)

        if filter_score == 1:
            logging.info(f"[green]Opinion[/green] {url} -> Score: {filter_score} | Title: {title}")
        elif filter_score == 0:
            logging.info(f"[blue]Neutral[/blue] {url} -> Score: {filter_score} | Title: {title}")
        else:
            logging.info(f"[yellow]Unclear[/yellow] {url} -> Score: {filter_score} | Title: {title}")

        return 'success'

    except (ValueError, KeyError) as e:
        logging.error(f"[red]Failed[/red] {url}: {e}")
        return 'error'
    finally:
        progress.advance(task_id)  # type: ignore

async def prefilter_titles(
    api_key: str,
    verbose: bool = False,
    batch_size: int = 1,
    use_batch_processing: bool = False
):
    """
    Main function to prefilter HN article titles using Mistral API.

    Args:
        api_key: Mistral API key
        verbose: Enable verbose logging
        batch_size: Number of titles to process per batch
                   (default: 1 for single-title processing)
        use_batch_processing: Use multi-title batch processing
                             (default: False - using legacy single-title)
    """
    # Setup logging
    level = logging.INFO if verbose else logging.WARNING
    logging.basicConfig(
        level=level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(console=console, rich_tracebacks=True, markup=True)]
    )

    # Initialize database and state table
    init_db()
    init_prefilter_state_table()

    # Run database migration to ensure schema is up-to-date
    migrate_database()

    # Load existing state for resumable execution
    processed_urls = get_processed_urls()
    state = get_prefilter_state()
    last_batch_index = int(state.get('last_batch_index', '-1'))

    # Get URLs that need processing (excluding already processed ones)
    all_urls = get_resolved_urls_for_prefiltering()
    urls_to_process = [url for url in all_urls if url[0] not in processed_urls]

    if not urls_to_process:
        console.print("[bold green]No URLs need prefiltering.[/bold green]")
        # Clear state if we're done
        clear_prefilter_state()
        return

    console.print(f"[bold blue]Found {len(urls_to_process)} URLs to prefilter[/bold blue]")
    if last_batch_index >= 0:
        console.print(f"[bold yellow]Resuming from batch {last_batch_index + 1}[/bold yellow]")

    stats = {
        "success": 0,
        "error": 0,
        "skipped": 0
    }

    # Setup graceful shutdown
    interactive_session = InteractiveSession(console)
    interactive_session.start()

    # Setup cost monitoring
    cost_monitor = CostMonitor()

    async with aiohttp.ClientSession() as http_session:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeRemainingColumn(),
            console=console
        ) as progress:
            task_id = progress.add_task(
                "[cyan]Prefiltering Titles...",
                total=len(urls_to_process)
            )

            # Start from where we left off
            start_index = last_batch_index * batch_size if last_batch_index >= 0 else 0

            # Safety check: if start_index exceeds the number of URLs to process,
            # reset to 0 to avoid infinite loop/skipping all URLs
            if start_index >= len(urls_to_process):
                warning_msg = (
                    f"Batch index {last_batch_index} is too high for "
                    f"{len(urls_to_process)} URLs. Resetting to 0."
                )
                logging.warning(warning_msg)
                start_index = 0
                # Clear the corrupted state
                save_prefilter_state('last_batch_index', '-1')

            # Process in batches with interruption support
            for i in range(start_index, len(urls_to_process), batch_size):
                if interactive_session.check_shutdown():
                    console.print(
                        "[bold yellow]Shutdown requested. Saving state and exiting...[/bold yellow]"
                    )
                    save_prefilter_state('last_batch_index', str(i // batch_size))
                    return

                await interactive_session.wait_if_paused()

                chunk = urls_to_process[i:i + batch_size]
                urls = [url[0] for url in chunk]
                titles = [url[1] for url in chunk]

                if use_batch_processing:
                    # Batch processing logic
                    results_map = await analyze_batch_with_mistral(
                        http_session, chunk, api_key
                    )

                    for url, title in chunk:
                        if url in results_map:
                            score = results_map[url]
                            update_prefilter_status(url, score)
                            stats['success'] += 1

                            if score == 1:
                                logging.info(
                                    f"[green]Opinion[/green] {url} -> Score: {score} | Title: {title}"
                                )
                            elif score == 0:
                                logging.info(
                                    f"[blue]Neutral[/blue] {url} -> Score: {score} | Title: {title}"
                                )
                            else:
                                logging.info(
                                    f"[yellow]Unclear[/yellow] {url} -> Score: {score} | Title: {title}"
                                )
                        else:
                            # Failed to get result for this item in batch
                            logging.warning(
                                f"[yellow]Skipped[/yellow] {url} - Batch analysis failed"
                            )
                            stats['skipped'] += 1

                    # Advance progress by the number of items processed in this batch
                    progress.advance(task_id, advance=len(chunk))
                else:
                    # Use legacy single-title processing
                    tasks = [
                        process_title(http_session, url, title, api_key, progress, task_id)
                        for url, title in chunk
                    ]
                    results = await asyncio.gather(*tasks)

                    for res in results:
                        stats[res] += 1

                # Check for shutdown between batches
                if interactive_session.check_shutdown():
                    console.print(
                        "[bold yellow]Shutdown requested. Saving state and exiting...[/bold yellow]"
                    )
                    save_prefilter_state('last_batch_index', str(i // batch_size))
                    return

    # Show final statistics
    console.print("\n[bold]Prefiltering Complete![/bold]")
    console.print(f"[green]Success:[/green] {stats['success']}")
    if stats['skipped'] > 0:
        console.print(f"[yellow]Skipped:[/yellow] {stats['skipped']}")
    if stats['error'] > 0:
        console.print(f"[red]Errors:[/red]   {stats['error']}")
    console.print(f"Total Processed: {sum(stats.values())}")

    # Show updated stats
    prefiltered_stats = get_prefiltered_stats()
    console.print(f"\n[bold blue]Current Database Stats:[/bold blue]")
    console.print(f"Resolved URLs: {prefiltered_stats['resolved']}")
    console.print(f"Prefiltered URLs: {prefiltered_stats['prefiltered']}")
    console.print(f"Pending Prefilter: {prefiltered_stats['pending_prefilter']}")

    console.print("\n[bold blue]Next Steps:[/bold blue]")
    console.print("You can now run the scraper to fetch article content:")
    console.print("[white]  python pipeline/src/scraper.py[/white]")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Prefilter HN article titles using Mistral API."
    )
    parser.add_argument(
        "--api-key",
        help="Mistral API key (optional if MISTRAL_API_KEY is set in .env)"
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    parser.add_argument(
        "-b",
        "--batch-size",
        type=int,
        default=10,
        help="Batch size for processing (default: 10)"
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume from last checkpoint (automatic by default)"
    )

    args = parser.parse_args()

    # Get API key from environment variable or CLI argument
    api_key = args.api_key or os.environ.get("MISTRAL_API_KEY")

    if not api_key:
        console.print("[bold red]Error: Mistral API key is required.[/bold red]")
        console.print("Either set MISTRAL_API_KEY in your .env file or provide --api-key argument.")
        exit(1)

    # Validate batch size
    if args.batch_size < 1 or args.batch_size > 50:
        console.print("[bold red]Error: Batch size must be between 1 and 50.[/bold red]")
        exit(1)

    asyncio.run(prefilter_titles(
        api_key,
        args.verbose,
        args.batch_size,
        True  # Enable batch processing by default
    ))