"""
Summary Summarization for AI_DISCOURSE articles (Phase 5).

This module synthesizes themes from grouped sentiment summaries using
Groq API. It reads exported JSON files containing summaries
grouped by sentiment (positive/neutral/negative) and extracts recurring themes.
"""

import sys
import io
import asyncio
import logging
import argparse
import os
import json
import re
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

from groq import AsyncGroq
from aiolimiter import AsyncLimiter
from dotenv import load_dotenv
from rich.console import Console
from rich.logging import RichHandler
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TaskProgressColumn,
)

# Load environment variables from .env file
env_path = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(env_path)

# Ensure proper path for imports
current_dir = Path(__file__).resolve().parent
if str(current_dir) not in sys.path:
    sys.path.append(str(current_dir))

from store.db import (
    get_db_connection,
    init_db,
    migrate_database,
    upsert_theme,
    clear_themes,
    get_themes_stats,
)

# Force UTF-8 encoding for standard output (handles piping issues on Windows)
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

# Setup Rich Console
console = Console()

# Groq API Configuration
GROQ_MODEL = "openai/gpt-oss-20b"

# Rate limiting: 2 requests per 1 second (conservative to avoid API throttling)
rate_limiter = AsyncLimiter(2, 1)

# Default input directory for exported summaries
DEFAULT_INPUT_DIR = Path(__file__).resolve().parent.parent / "data" / "exports"

# Sentiment groups to process
SENTIMENT_GROUPS = ["positive", "neutral", "negative"]

# Summary Summarization Prompt Template
SUMMARIZATION_PROMPT = """You are analyzing {n} developer opinions about AI coding tools.
These summaries have been classified as {sentiment_group} sentiment.

Your task is to identify 3-5 RECURRING THEMES that appear across these summaries.

## GUIDELINES

1. **Theme Titles**: Should be clear and descriptive (3-6 words)
   - Good: "Code Quality Concerns", "Productivity Speed Gains"
   - Bad: "Issues", "Positive Feedback"

2. **Descriptions**: Synthesize what developers are collectively saying (2-3 sentences)
   - Focus on specific, actionable insights
   - Capture nuance and common experiences

3. **Verdicts**: Short phrase summarizing the theme's conclusion (3-5 words)
   - For positive: "Productivity Gains Confirmed", "Worth the Learning Curve"
   - For neutral: "Mixed Results Depend on Context", "Benefits Require Expertise"
   - For negative: "High Frustration Risk", "Not Ready for Production"

4. **Related Count**: Estimate how many summaries relate to each theme

## INPUT SUMMARIES

{summaries}

## OUTPUT (JSON ONLY)

{{
  "themes": [
    {{
      "title": "Theme Title Here",
      "description": "2-3 sentence synthesis of what developers are saying about this topic across the summaries.",
      "related_count": <number>,
      "sentiment_verdict": "Short Verdict Phrase"
    }}
  ],
  "meta": {{
    "total_summaries": {n},
    "sentiment_group": "{sentiment_group}"
  }}
}}"""


class CostMonitor:
    """Monitors API usage and cost efficiency."""

    def __init__(self):
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.successful_calls = 0
        self.failed_calls = 0

    def add_call(self, input_tokens: int, output_tokens: int, success: bool):
        """Record API call metrics."""
        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens
        if success:
            self.successful_calls += 1
        else:
            self.failed_calls += 1

    def get_cost_estimate(self) -> float:
        """Estimate cost based on Groq pricing for openai/gpt-oss-20b."""
        # Groq pricing for openai/gpt-oss-20b
        # $0.075/1M input, $0.30/1M output
        input_cost = (self.total_input_tokens / 1_000_000) * 0.075
        output_cost = (self.total_output_tokens / 1_000_000) * 0.30
        return input_cost + output_cost

    def get_stats(self) -> Dict[str, Any]:
        """Return current stats."""
        total_calls = self.successful_calls + self.failed_calls
        return {
            "total_calls": total_calls,
            "successful": self.successful_calls,
            "failed": self.failed_calls,
            "success_rate": (
                self.successful_calls / total_calls if total_calls > 0 else 0
            ),
            "total_tokens": self.total_input_tokens + self.total_output_tokens,
            "input_tokens": self.total_input_tokens,
            "output_tokens": self.total_output_tokens,
            "estimated_cost_usd": self.get_cost_estimate(),
        }


def load_summaries(input_dir: Path) -> Dict[str, List[str]]:
    """
    Load exported summary JSON files from the input directory.
    Returns dict mapping sentiment_group -> list of summary strings.
    """
    summaries = {}

    for group in SENTIMENT_GROUPS:
        file_path = input_dir / f"{group}.json"
        if file_path.exists():
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        summaries[group] = data
                        logging.info(
                            f"Loaded {len(data)} summaries from {file_path.name}"
                        )
                    else:
                        logging.warning(
                            f"Invalid format in {file_path.name}: expected list"
                        )
                        summaries[group] = []
            except json.JSONDecodeError as e:
                logging.error(f"Failed to parse {file_path.name}: {e}")
                summaries[group] = []
        else:
            logging.warning(f"File not found: {file_path}")
            summaries[group] = []

    return summaries


def validate_themes_response(result: Dict[str, Any]) -> tuple[bool, str]:
    """Validate the LLM response structure."""
    errors = []

    if "themes" not in result:
        errors.append("Missing 'themes' field")
    elif not isinstance(result["themes"], list):
        errors.append("'themes' must be a list")
    else:
        for i, theme in enumerate(result["themes"]):
            if not isinstance(theme, dict):
                errors.append(f"Theme {i} must be an object")
                continue
            if "title" not in theme:
                errors.append(f"Theme {i} missing 'title'")
            if "description" not in theme:
                errors.append(f"Theme {i} missing 'description'")
            if "related_count" not in theme:
                errors.append(f"Theme {i} missing 'related_count'")
            if "sentiment_verdict" not in theme:
                errors.append(f"Theme {i} missing 'sentiment_verdict'")

    if errors:
        return False, "; ".join(errors)
    return True, ""


async def synthesize_themes(
    client: AsyncGroq,
    summaries: List[str],
    sentiment_group: str,
    cost_monitor: CostMonitor,
) -> Optional[Dict[str, Any]]:
    """
    Send grouped summaries to Groq for theme extraction.
    """
    if not summaries:
        logging.warning(f"No summaries for {sentiment_group} group")
        return None

    # Format summaries as bullet list
    summaries_text = "\n".join(f"- {s}" for s in summaries)

    prompt = SUMMARIZATION_PROMPT.format(
        n=len(summaries),
        sentiment_group=sentiment_group,
        summaries=summaries_text,
    )

    try:
        async with rate_limiter:
            response = await client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_completion_tokens=2048,
                response_format={"type": "json_object"},
            )

        # Extract token usage
        usage = response.usage
        input_tokens = usage.prompt_tokens if usage else 0
        output_tokens = usage.completion_tokens if usage else 0

        # Extract content from response
        content = response.choices[0].message.content
        if not content:
            logging.error("Empty content in Groq response")
            cost_monitor.add_call(input_tokens, output_tokens, False)
            return None

        content = content.strip()

        try:
            # Extract JSON from response
            json_content = content

            # Clean up if wrapped in markdown
            if "```" in json_content:
                match = re.search(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", json_content)
                if match:
                    json_content = match.group(1)
                else:
                    lines = json_content.split("\n")
                    lines = [l for l in lines if not l.strip().startswith("```")]
                    json_content = "\n".join(lines).strip()

            # If response has text before JSON, extract just the JSON object
            if not json_content.strip().startswith("{"):
                match = re.search(r"\{[\s\S]*\}", json_content)
                if match:
                    json_content = match.group(0)
                else:
                    logging.error(
                        f"No JSON object found in response: {content[:200]}..."
                    )
                    cost_monitor.add_call(input_tokens, output_tokens, False)
                    return None

            result = json.loads(json_content)

            # Validate response
            is_valid, error_msg = validate_themes_response(result)
            if not is_valid:
                logging.warning(f"Invalid response: {error_msg}")
                cost_monitor.add_call(input_tokens, output_tokens, False)
                return None

            cost_monitor.add_call(input_tokens, output_tokens, True)

            return {
                "themes": result["themes"],
                "meta": result.get("meta", {}),
            }

        except json.JSONDecodeError as e:
            logging.error(f"Failed to parse JSON: {content[:300]}...")
            cost_monitor.add_call(input_tokens, output_tokens, False)
            return None

    except Exception as e:
        logging.error(f"Groq API error: {e}")
        cost_monitor.add_call(0, 0, False)
        return None


def save_themes_to_db(
    sentiment_group: str,
    themes: List[Dict[str, Any]],
    model: str = GROQ_MODEL,
):
    """Save extracted themes to the database."""
    for theme in themes:
        upsert_theme(
            sentiment_group=sentiment_group,
            theme_title=theme["title"],
            theme_description=theme["description"],
            sentiment_verdict=theme.get("sentiment_verdict", ""),
            article_count=theme.get("related_count", 0),
            model=model,
        )


def show_stats():
    """Display theme statistics."""
    stats = get_themes_stats()

    console.print("\n[bold blue]Theme Statistics[/bold blue]")
    console.print(f"  Total Themes: {stats['total']}")
    console.print(f"  [green]Positive:[/green] {stats['positive']}")
    console.print(f"  [yellow]Neutral:[/yellow] {stats['neutral']}")
    console.print(f"  [red]Negative:[/red] {stats['negative']}")


async def summarize_themes(
    api_key: str,
    verbose: bool = False,
    input_dir: Optional[Path] = None,
    reset: bool = False,
):
    """
    Main function to synthesize themes from exported summaries.

    Args:
        api_key: Groq API key
        verbose: Enable verbose logging
        input_dir: Directory containing exported JSON files
        reset: Clear existing themes before starting
    """
    # Setup logging
    level = logging.INFO if verbose else logging.WARNING
    logging.basicConfig(
        level=level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(console=console, rich_tracebacks=True, markup=True)],
        force=True,
    )

    # Initialize database
    init_db()
    migrate_database()

    # Handle reset
    if reset:
        console.print("[bold yellow]Clearing existing themes...[/bold yellow]")
        clear_themes()
        console.print("[green]Themes cleared[/green]")

    # Set input directory
    if input_dir is None:
        input_dir = DEFAULT_INPUT_DIR

    if not input_dir.exists():
        console.print(f"[bold red]Input directory not found: {input_dir}[/bold red]")
        console.print("Please run the export from the /summaries page first.")
        console.print(f"Then place the JSON files in: {input_dir}")
        return

    # Load summaries from exported files
    console.print(f"[bold blue]Loading summaries from: {input_dir}[/bold blue]")
    summaries = load_summaries(input_dir)

    total_summaries = sum(len(s) for s in summaries.values())
    if total_summaries == 0:
        console.print("[bold yellow]No summaries found to process.[/bold yellow]")
        console.print("Export summaries from /summaries page first.")
        return

    console.print(f"[bold blue]Found {total_summaries} total summaries[/bold blue]")
    for group, sums in summaries.items():
        if sums:
            console.print(f"  {group}: {len(sums)}")

    # Cost monitoring
    cost_monitor = CostMonitor()

    # Create Groq async client
    client = AsyncGroq(api_key=api_key)

    # Process each sentiment group
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        task_id = progress.add_task(
            "[cyan]Synthesizing themes...",
            total=len([g for g in summaries if summaries[g]]),
        )

        for sentiment_group, group_summaries in summaries.items():
            if not group_summaries:
                continue

            progress.update(
                task_id,
                description=f"[cyan]Processing {sentiment_group}...",
            )

            result = await synthesize_themes(
                client,
                group_summaries,
                sentiment_group,
                cost_monitor,
            )

            if result and result.get("themes"):
                themes = result["themes"]
                save_themes_to_db(sentiment_group, themes)

                # Color-code output
                color = {
                    "positive": "green",
                    "neutral": "orange",
                    "negative": "red",
                }.get(sentiment_group, "white")

                console.print(
                    f"[{color}]{sentiment_group.capitalize()}:[/{color}] "
                    f"Extracted {len(themes)} themes from {len(group_summaries)} summaries"
                )

                for theme in themes:
                    console.print(
                        f"  - {theme['title']} ({theme.get('related_count', '?')} related)"
                    )
            else:
                console.print(
                    f"[red]Failed to extract themes for {sentiment_group}[/red]"
                )

            progress.advance(task_id)

    # Final report
    console.print("\n[bold]Summary Summarization Complete![/bold]")
    show_stats()

    # Cost report
    cost_stats = cost_monitor.get_stats()
    console.print(f"\n[bold blue]API Usage:[/bold blue]")
    console.print(f"Total Calls: {cost_stats['total_calls']}")
    console.print(f"Input Tokens: {cost_stats['input_tokens']:,}")
    console.print(f"Output Tokens: {cost_stats['output_tokens']:,}")
    console.print(f"Estimated Cost: ${cost_stats['estimated_cost_usd']:.4f}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Synthesize themes from grouped sentiment summaries using Groq API."
    )
    parser.add_argument(
        "--api-key",
        help="Groq API key (or set GROQ_API_KEY in .env)",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        help=f"Directory containing exported JSON files (default: {DEFAULT_INPUT_DIR})",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Clear existing themes before starting",
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Show theme statistics and exit",
    )

    args = parser.parse_args()

    # Stats-only mode
    if args.stats:
        init_db()
        migrate_database()
        show_stats()
        exit(0)

    # Get API key
    api_key = args.api_key or os.environ.get("GROQ_API_KEY")
    if not api_key:
        console.print("[bold red]Error: Groq API key is required.[/bold red]")
        console.print("Set GROQ_API_KEY in .env or provide --api-key argument.")
        exit(1)

    # Run the summarizer
    asyncio.run(
        summarize_themes(
            api_key,
            args.verbose,
            args.input_dir,
            args.reset,
        )
    )
