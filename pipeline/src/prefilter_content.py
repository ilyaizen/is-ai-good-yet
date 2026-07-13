"""
Content-based prefilter for scraped articles.

This module classifies scraped article content (not just titles) into categories:
- AI_DISCOURSE: Subjective developer experiences with AI coding tools
- AI_NEWS: Announcements/releases about AI coding tools specifically
- AI_OTHER: General AI/ML content NOT about coding workflows (tutorials, LLM research, AGI philosophy)
- NOISE: Not about artificial intelligence at all

Uses Groq API (llama-3.1-8b-instant) for classification with streaming output.
"""

import sys
import io
import asyncio
import logging
import argparse
import os
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Tuple, Optional, Dict, Any

from groq import AsyncGroq
from dotenv import load_dotenv
from rich.console import Console
from rich.logging import RichHandler
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TaskProgressColumn,
    TimeRemainingColumn,
    TaskID,
)
from rich.live import Live
from rich.panel import Panel
from rich.text import Text
import polars as pl

# Load environment variables from .env file
env_path = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(env_path)

# Ensure proper path for imports
current_dir = Path(__file__).resolve().parent
if str(current_dir) not in sys.path:
    sys.path.append(str(current_dir))

from store.db import get_db_connection, init_db, migrate_database
from store.parquet import read_articles
from store.paths import get_articles_dir
from interactive import InteractiveSession

# Force UTF-8 encoding for standard output (handles piping issues on Windows)
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

# Setup Rich Console
console = Console()

# Groq API Configuration
GROQ_MODEL = "llama-3.1-8b-instant"

# Maximum characters to send to the LLM (truncation limit)
MAX_CONTENT_LENGTH = 4000

# Separator for head/tail truncation
SNIP_SEPARATOR = "\n\n[… middle section omitted …]\n\n"

# Valid categories
VALID_CATEGORIES = {"AI_DISCOURSE", "AI_NEWS", "AI_OTHER", "NOISE"}

# Domains that typically don't contain relevant articles for AI sentiment analysis
IRRELEVANT_DOMAINS = [
    "github.com",
    "arxiv.org",
    "twitter.com",
    "x.com",
    "reddit.com",
    "youtube.com",
    "docs.google.com",
    "drive.google.com",
    "gist.github.com",
    "gitlab.com",
    "bitbucket.org",
    "stackoverflow.com",
    "stackexchange.com",
    "linkedin.com",
    "facebook.com",
    "instagram.com",
    "tiktok.com",
    "discord.com",
    "slack.com",
    "notion.so",
    "figma.com",
    "miro.com",
    "trello.com",
    "jira.atlassian.com",
    "huggingface.co",
    "kaggle.com",
    "colab.research.google.com",
    "pypi.org",
    "npmjs.com",
    "crates.io",
    "cursor.com",
]


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


def is_relevant_url(url: str) -> bool:
    """Check if a URL is from a relevant domain (not in IRRELEVANT_DOMAINS)."""
    try:
        from urllib.parse import urlparse

        hostname = urlparse(url).hostname or ""
        hostname = hostname.replace("www.", "", 1)
        for domain in IRRELEVANT_DOMAINS:
            if hostname == domain or hostname.endswith("." + domain):
                return False
        return True
    except Exception:
        return True  # If parsing fails, consider it relevant


# Content Classification Prompt (v4.1 - Developer Experience + Research Findings)
CONTENT_CLASSIFICATION_PROMPT = """Act as a strict Content Filter for a project tracking developer sentiment about AI coding tools.

CRITICAL: We ONLY want articles where developers share their PERSONAL EXPERIENCE or SUBSTANTIVE OPINION about using AI for coding, OR research with CLEAR FINDINGS about AI coding effectiveness. Product announcements, tutorials, and general AI news should be EXCLUDED.

## Categories

### AI_DISCOURSE (Include in Verdict)
First-person developer experience, substantive analysis with clear opinion, OR research with clear findings about AI coding tools.

MUST contain at least ONE of:
- First-person experience: "I used...", "We built...", "After 3 months with...", "My team switched to..."
- Critical evaluation with verdict: "X is better than Y because...", "Why X fails at..."
- Success/failure stories with lessons learned
- Productivity claims backed by personal anecdotes
- Workflow comparisons with personal recommendation
- **Research with clear findings**: Studies presenting empirical data about AI coding tool effectiveness, skill development, or productivity with explicit conclusions

Examples that QUALIFY:
- "I Replaced My Junior Dev With Cursor - Here's What Happened" (first-person experience)
- "Copilot vs Cursor: After Testing Both, Here's My Verdict" (comparative opinion)
- "Why I Stopped Using AI Coding Assistants" (personal decision with reasoning)
- "How Claude Helped Us Ship 2x Faster" (team experience with outcome)
- "AI Code Review Is Overrated - A Senior Dev's Perspective" (opinion piece)
- "How AI assistance impacts the formation of coding skills" (research with clear findings: 17% skill reduction)

### AI_NEWS (Exclude - No Developer Opinion)
Announcements, launches, or factual reporting WITHOUT author experience/opinion.

Characteristics:
- Press releases, company blog posts announcing features
- "Introducing X", "Announcing Y", "Now available: Z"
- Benchmark results presented without interpretation
- Funding/acquisition/hiring news
- Feature changelogs without usage commentary

Examples:
- "Windsurf Codemaps: Understand Code Before You Vibe It" (product marketing)
- "Cursor 2.0 Released with New Agent Features" (feature announcement)
- "GitHub Copilot Now Supports Multi-File Editing" (changelog)
- "Anthropic Raises $10B Series D" (funding news)

### AI_OTHER (Exclude - Wrong Topic)
AI/ML content NOT specifically about coding workflows with AI tools, OR methodology-focused academic content without clear findings.

Includes:
- Courses, tutorials, books, educational guides (even about LLMs/coding)
- Pure academic research (methodology-focused without clear findings about AI coding utility)
- Non-coding AI: audio, image, video generation, robotics
- AGI philosophy, AI ethics, job displacement debates
- General model capabilities without coding focus
- AI in healthcare/finance/legal/other industries

**NOTE**: Research WITH clear findings about AI coding effectiveness DOES qualify as AI_DISCOURSE.

Examples:
- "Neural Networks: Zero to Hero" (educational course)
- "Our New SAM Audio Model Transforms Audio Editing" (audio AI, not coding)
- "Will AI Replace Programmers?" (speculation, not experience)
- "Attention Is All You Need" (pure methodology paper, no coding tool findings)
- "Introduction to Prompt Engineering" (tutorial)
- "A Survey of LLM Architectures" (survey paper, no actionable findings)

### NOISE (Exclude - Not AI)
Content unrelated to AI/ML entirely.

Examples:
- "Postgres 17 Released" (database, no AI)
- "The State of JavaScript 2025" (web dev, no AI)

## Decision Rules (Apply in Order)

1. If it's a PRODUCT ANNOUNCEMENT or COMPANY BLOG POST (without findings) → AI_NEWS (not AI_DISCOURSE)
2. If it's EDUCATIONAL (course, tutorial, book, guide) → AI_OTHER (not AI_DISCOURSE)
3. If AI is mentioned but NOT about coding/development → AI_OTHER
4. If it's RESEARCH WITH CLEAR FINDINGS about AI coding utility → AI_DISCOURSE (even if company blog)
5. AI_DISCOURSE requires AUTHOR OPINION, PERSONAL EXPERIENCE, or EMPIRICAL FINDINGS - topic relevance alone is NOT enough
6. When uncertain between AI_DISCOURSE and AI_NEWS → choose AI_NEWS (be conservative)

Article:
{{
  "title": "{title}",
  "content": "{content}"
}}

Return valid JSON only:
{{
  "category": "AI_DISCOURSE" | "AI_NEWS" | "AI_OTHER" | "NOISE",
  "confidence": 0.0-1.0,
  "reasoning": "<20 words max. Why this category?>"
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
        """Estimate cost based on Groq pricing for llama-3.1-8b-instant."""
        # Groq pricing: https://console.groq.com/docs/models
        # llama-3.1-8b-instant: $0.05/1M input, $0.08/1M output
        input_cost = (self.total_input_tokens / 1_000_000) * 0.05
        output_cost = (self.total_output_tokens / 1_000_000) * 0.08
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


def migrate_content_filter_columns():
    """Add content filtering columns to the database if they don't exist."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Check existing columns
        cursor.execute("PRAGMA table_info(urls)")
        columns = [column[1] for column in cursor.fetchall()]

        if "content_category" not in columns:
            logging.info("Adding 'content_category' column to urls table")
            cursor.execute("ALTER TABLE urls ADD COLUMN content_category TEXT")

        if "content_confidence" not in columns:
            logging.info("Adding 'content_confidence' column to urls table")
            cursor.execute("ALTER TABLE urls ADD COLUMN content_confidence REAL")

        if "content_filter_json" not in columns:
            logging.info("Adding 'content_filter_json' column to urls table")
            cursor.execute("ALTER TABLE urls ADD COLUMN content_filter_json TEXT")

        conn.commit()
        logging.info("Content filter columns migration completed")

    except Exception as e:
        logging.error(f"Error during content filter migration: {e}")
    finally:
        if conn:
            conn.close()


def get_scraped_urls_for_content_filter(
    batch_size: int = 50,
    min_score: int = 20,
    min_comments: int = 5,
    relevant_only: bool = True,
) -> List[Tuple[str, str, int]]:
    """
    Get scraped articles that haven't been content-filtered yet.
    Automatically marks irrelevant URLs as 'SKIPPED' to prevent clogged queues.

    Args:
        batch_size: Maximum number of URLs to return
        min_score: Minimum HN score filter
        min_comments: Minimum HN comments filter
        relevant_only: If True, exclude URLs from non-article domains

    Returns list of tuples: (url, hn_title, hn_id)
    """
    conn = None
    collected_results = []

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        while len(collected_results) < batch_size:
            # Fetch a chunk of candidates
            fetch_limit = batch_size * 2

            cursor.execute(
                """
                SELECT url, hn_title, hn_id
                FROM urls
                WHERE scraped_status = 'success'
                AND content_category IS NULL
                AND hn_score >= ?
                AND hn_comments >= ?
                ORDER BY hn_score DESC
                LIMIT ?
            """,
                (min_score, min_comments, fetch_limit),
            )
            candidates = cursor.fetchall()

            if not candidates:
                break

            relevant_candidates = []
            irrelevant_urls = []

            for row in candidates:
                url = row[0]
                if relevant_only and not is_relevant_url(url):
                    irrelevant_urls.append(url)
                else:
                    relevant_candidates.append(row)

            # Batch update irrelevant URLs to SKIPPED
            if irrelevant_urls:
                logging.info(
                    f"Skipping {len(irrelevant_urls)} irrelevant URLs (e.g. {irrelevant_urls[0]})"
                )
                placeholders = ",".join(["?"] * len(irrelevant_urls))
                cursor.execute(
                    f"""
                    UPDATE urls
                    SET content_category = 'SKIPPED',
                        content_confidence = 0.0,
                        content_filter_json = '{{}}'
                    WHERE url IN ({placeholders})
                    """,
                    irrelevant_urls,
                )
                conn.commit()

            # Add relevant ones to our collection
            for item in relevant_candidates:
                collected_results.append(item)
                if len(collected_results) >= batch_size:
                    break

        return collected_results

    except Exception as e:
        logging.error(f"Error fetching URLs for content filter: {e}")
        return []
    finally:
        if conn:
            conn.close()


def get_pending_content_filter_count(
    min_score: int = 20,
    min_comments: int = 5,
    relevant_only: bool = True,
) -> int:
    """Get count of scraped articles pending content filtering."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT url
            FROM urls
            WHERE scraped_status = 'success'
            AND content_category IS NULL
            AND hn_score >= ?
            AND hn_comments >= ?
        """,
            (min_score, min_comments),
        )
        urls = [row[0] for row in cursor.fetchall()]

        # Filter by relevant domains if requested
        if relevant_only:
            urls = [u for u in urls if is_relevant_url(u)]

        return len(urls)
    except Exception:
        return 0
    finally:
        if conn:
            conn.close()


def update_content_filter_result(
    url: str,
    category: str,
    confidence: float,
    result_json: str,
    metrics_json: Optional[str] = None,
):
    """Update content filter results for a URL, including optional speed metrics."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        if metrics_json:
            # Merge with existing metrics (preserve classifier metrics if present)
            cursor.execute("SELECT groq_metrics_json FROM urls WHERE url = ?", (url,))
            existing = cursor.fetchone()
            existing_metrics = {}
            if existing and existing[0]:
                try:
                    existing_metrics = json.loads(existing[0])
                except json.JSONDecodeError:
                    pass

            existing_metrics["prefilter"] = json.loads(metrics_json)
            merged_metrics = json.dumps(existing_metrics)

            cursor.execute(
                """
                UPDATE urls
                SET content_category = ?,
                    content_confidence = ?,
                    content_filter_json = ?,
                    groq_metrics_json = ?
                WHERE url = ?
                """,
                (category, confidence, result_json, merged_metrics, url),
            )
        else:
            cursor.execute(
                """
                UPDATE urls
                SET content_category = ?,
                    content_confidence = ?,
                    content_filter_json = ?
                WHERE url = ?
                """,
                (category, confidence, result_json, url),
            )
        conn.commit()
    except Exception as e:
        logging.error(f"Error updating content filter for {url}: {e}")
    finally:
        if conn:
            conn.close()


def reset_content_filter_data(
    min_score: int = 20,
    min_comments: int = 5,
) -> int:
    """Reset content filter data for all articles matching criteria."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE urls
            SET content_category = NULL,
                content_confidence = NULL,
                content_filter_json = NULL
            WHERE scraped_status = 'success'
            AND hn_score >= ?
            AND hn_comments >= ?
            AND content_category IS NOT NULL
            """,
            (min_score, min_comments),
        )
        affected = cursor.rowcount
        conn.commit()
        logging.info(f"Reset content filter data for {affected} articles")
        return affected
    except Exception as e:
        logging.error(f"Error resetting content filter data: {e}")
        return 0
    finally:
        if conn:
            conn.close()


def get_article_content_batch(url_list: List[str]) -> Dict[str, str]:
    """
    Retrieve article text for the given URLs from Parquet store.
    Returns dict mapping URL -> text content.
    """
    try:
        data_dir = get_articles_dir()
        if not data_dir.exists():
            logging.warning(f"Parquet directory not found: {data_dir}")
            return {}

        lf = read_articles(shard_dir=data_dir)
        filtered = lf.filter(pl.col("url").is_in(url_list)).select(["url", "text"])
        df = filtered.collect()

        return {row["url"]: row["text"] for row in df.iter_rows(named=True)}

    except Exception as e:
        logging.error(f"Error reading article content: {e}")
        return {}


def truncate_text(text: str, max_length: int = MAX_CONTENT_LENGTH) -> str:
    """Truncate text to max_length, trying to break at word boundaries."""
    if len(text) <= max_length:
        return text

    # Try to break at a space near the limit
    truncated = text[:max_length]
    last_space = truncated.rfind(" ")
    if last_space > max_length * 0.8:  # Only break at space if reasonable
        truncated = truncated[:last_space]

    return truncated + "..."


def truncate_head_tail(text: str, max_length: int = MAX_CONTENT_LENGTH, head_ratio: float = 0.6) -> str:
    """
    Truncate text using head/tail strategy for prefilter.

    Keeps the opening (60%) and closing (40%) portions of the text,
    replacing the middle with a separator.
    """
    if len(text) <= max_length:
        return text

    separator = SNIP_SEPARATOR
    available = max_length - len(separator)
    head_len = int(available * head_ratio)
    tail_len = available - head_len

    # Extract head and tail
    head = text[:head_len]
    tail = text[-tail_len:]

    # Adjust head to word boundary
    head_space = head.rfind(" ")
    if head_space > head_len * 0.8:
        head = head[:head_space]

    # Adjust tail to word boundary
    tail_space = tail.find(" ")
    if 0 < tail_space < tail_len * 0.2:
        tail = tail[tail_space + 1:]

    return head + separator + tail


async def classify_content_with_groq_streaming(
    client: AsyncGroq,
    title: str,
    text: str,
    cost_monitor: CostMonitor,
    verbose: bool = False,
) -> Optional[Dict[str, Any]]:
    """
    Classify article content using Groq API with streaming output.

    Returns dict with:
    - category: OPINION_CODING, NEWS_CODING, AI_OTHER, or NOT_AI
    - confidence: 0.0-1.0
    - reasoning: brief explanation
    """
    truncated_text = truncate_head_tail(text)

    # Prepare title (escape quotes)
    prepared_title = (title or "Untitled").replace('"', '\\"')
    # Prepare content (strip newlines, escape quotes)
    prepared_content = prepare_content_for_prompt(truncated_text)

    prompt = CONTENT_CLASSIFICATION_PROMPT.format(
        title=prepared_title,
        content=prepared_content,
    )

    # Track prompt character count for metrics
    prompt_chars = len(prepared_content)

    try:
        # START TIMING
        start_time = time.perf_counter()

        # Stream the response
        stream = await client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.6,
            max_completion_tokens=256,
            top_p=0.95,
            stream=True,
        )

        # Collect streamed content
        full_content = ""
        input_tokens = 0
        output_tokens = 0

        async for chunk in stream:
            # Extract token from chunk
            delta = chunk.choices[0].delta if chunk.choices else None
            if delta and delta.content:
                full_content += delta.content

            # Track usage from final chunk
            if hasattr(chunk, 'x_groq') and chunk.x_groq:
                usage = getattr(chunk.x_groq, 'usage', None)
                if usage:
                    input_tokens = getattr(usage, 'prompt_tokens', 0)
                    output_tokens = getattr(usage, 'completion_tokens', 0)

        # END TIMING
        end_time = time.perf_counter()
        inference_time_ms = (end_time - start_time) * 1000
        tokens_per_second = output_tokens / (inference_time_ms / 1000) if inference_time_ms > 0 else 0

        # Parse the JSON response
        content = full_content.strip()

        try:
            # Clean up if wrapped in markdown
            if content.startswith("```"):
                content = content.strip("`").replace("json\n", "", 1).strip()

            # Handle thinking tags from LLM models
            if "<think>" in content:
                # Extract content after </think>
                think_end = content.find("</think>")
                if think_end != -1:
                    content = content[think_end + 8:].strip()

            # Find JSON object in response
            json_start = content.find("{")
            json_end = content.rfind("}") + 1
            if json_start != -1 and json_end > json_start:
                content = content[json_start:json_end]

            result = json.loads(content)

            # Validate category
            category = result.get("category", "").upper()
            if category not in VALID_CATEGORIES:
                logging.warning(
                    f"Invalid category '{category}', defaulting to NOT_AI"
                )
                category = "NOT_AI"

            confidence = float(result.get("confidence", 0.5))
            reasoning = result.get("reasoning", "")

            cost_monitor.add_call(input_tokens, output_tokens, True)

            # Build metrics object for speed insights
            metrics = {
                "model": GROQ_MODEL,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": input_tokens + output_tokens,
                "inference_time_ms": round(inference_time_ms, 1),
                "tokens_per_second": round(tokens_per_second, 1),
                "prompt_chars": prompt_chars,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

            return {
                "category": category,
                "confidence": confidence,
                "reasoning": reasoning,
                "metrics": metrics,
            }

        except json.JSONDecodeError:
            logging.error(f"Failed to parse JSON: {content[:200]}...")
            cost_monitor.add_call(input_tokens, output_tokens, False)
            return None

    except Exception as e:
        logging.error(f"Error calling Groq API: {e}")
        cost_monitor.add_call(0, 0, False)
        return None


async def process_batch(
    client: AsyncGroq,
    batch: List[Tuple[str, str, int]],
    cost_monitor: CostMonitor,
    progress: Progress,
    task_id: TaskID,
    interactive: InteractiveSession,
    verbose: bool = False,
) -> Dict[str, int]:
    """Process a batch of articles and return stats."""
    stats = {"success": 0, "failed": 0, "no_content": 0}

    # Get article content
    urls = [item[0] for item in batch]
    content_map = get_article_content_batch(urls)

    for url, title, hn_id in batch:
        if interactive.check_shutdown():
            break

        await interactive.wait_if_paused()

        text = content_map.get(url)
        if not text:
            logging.warning(
                f"[yellow]No content[/yellow] for {url} - marking as skipped"
            )
            update_content_filter_result(url, "SKIPPED", 0.0, "{}")
            stats["no_content"] += 1
            progress.advance(task_id)
            continue

        # Show article being processed
        if verbose:
            console.print(f"\n[bold cyan]#{hn_id}[/bold cyan] {title[:60]}...")

        result = await classify_content_with_groq_streaming(
            client, title, text, cost_monitor, verbose
        )

        if result:
            # Extract metrics if present
            metrics_json = json.dumps(result.get("metrics")) if result.get("metrics") else None

            update_content_filter_result(
                url,
                result["category"],
                result["confidence"],
                json.dumps(result),
                metrics_json,
            )

            # Color-code by category
            category = result["category"]
            if category == "AI_DISCOURSE":
                color = "green"
                icon = "[check]"
            elif category == "AI_NEWS":
                color = "blue"
                icon = "[info]"
            elif category == "AI_OTHER":
                color = "yellow"
                icon = "[~]"
            elif category == "NOISE":
                color = "dim"
                icon = "[x]"
            else:
                color = "dim"
                icon = "[?]"

            console.print(
                f"  [{color}]{icon} {category}[/{color}] ({result['confidence']:.0%}) - {result.get('reasoning', '')[:50]}"
            )
            stats["success"] += 1
        else:
            console.print(f"  [red][!] Failed to classify[/red]")
            stats["failed"] += 1

        progress.advance(task_id)

    return stats


async def prefilter_content(
    api_key: str,
    verbose: bool = False,
    batch_size: int = 20,
    min_score: int = 20,
    min_comments: int = 5,
    limit: int = 0,
    relevant_only: bool = True,
    reset: bool = False,
):
    """
    Main function to prefilter article content using Groq API.

    Args:
        api_key: Groq API key
        verbose: Enable verbose logging with streaming output
        batch_size: Number of articles per batch
        min_score: Minimum HN score filter (default: 20)
        min_comments: Minimum HN comments filter (default: 5)
        limit: Maximum articles to process (0 = unlimited)
        relevant_only: Exclude non-article domains like github.com (default: True)
        reset: Clear existing content filter data before starting
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

    # Initialize database and run migrations
    init_db()
    migrate_database()
    migrate_content_filter_columns()

    # Handle reset
    if reset:
        console.print("[bold yellow]Resetting content filter data...[/bold yellow]")
        affected = reset_content_filter_data(min_score, min_comments)
        console.print(f"[green]Reset {affected} articles[/green]")

    # Check pending count
    pending_count = get_pending_content_filter_count(
        min_score, min_comments, relevant_only
    )

    if pending_count == 0:
        console.print(
            "[bold green]No scraped articles need content filtering.[/bold green]"
        )
        # Show diagnostic info when verbose to help debug
        if verbose:
            _show_prefilter_diagnostics(min_score, min_comments)
        return

    if limit > 0:
        target_count = min(pending_count, limit)
    else:
        target_count = pending_count

    console.print(
        f"\n[bold blue]Found {pending_count} articles pending content filter[/bold blue]"
    )
    console.print(f"[bold blue]Processing up to {target_count} articles[/bold blue]")
    console.print(f"[dim]Model: {GROQ_MODEL} (streaming)[/dim]")

    # Display active filters
    filters = []
    if min_score > 0:
        filters.append(f"score >= {min_score}")
    if min_comments > 0:
        filters.append(f"comments >= {min_comments}")
    if relevant_only:
        filters.append("relevant domains only")
    if filters:
        console.print(f"[dim]Filters: {', '.join(filters)}[/dim]")

    # Setup graceful shutdown
    interactive = InteractiveSession(console)
    interactive.start()

    # Cost monitoring
    cost_monitor = CostMonitor()

    total_stats = {"success": 0, "failed": 0, "no_content": 0}
    processed = 0

    # Create Groq async client
    client = AsyncGroq(api_key=api_key)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeRemainingColumn(),
        console=console,
        transient=not verbose,  # Keep progress visible in verbose mode
    ) as progress:
        content_task_id = progress.add_task(
            "[cyan]Content Filtering...",
            total=target_count,
        )

        while processed < target_count:
            if interactive.check_shutdown():
                console.print(
                    "\n[bold yellow]Shutdown requested. Exiting...[/bold yellow]"
                )
                break

            # Fetch next batch
            remaining = target_count - processed
            fetch_size = min(batch_size, remaining)
            batch = get_scraped_urls_for_content_filter(
                fetch_size, min_score, min_comments, relevant_only
            )

            if not batch:
                console.print("[green]No more articles to process.[/green]")
                break

            batch_stats = await process_batch(
                client,
                batch,
                cost_monitor,
                progress,
                content_task_id,
                interactive,
                verbose,
            )

            for key in total_stats:
                total_stats[key] += batch_stats[key]

            processed += len(batch)

    # Final report
    console.print("\n[bold]Content Filtering Complete![/bold]")
    console.print(f"[green]Classified:[/green] {total_stats['success']}")
    if total_stats["failed"] > 0:
        console.print(f"[red]Failed:[/red] {total_stats['failed']}")
    if total_stats["no_content"] > 0:
        console.print(f"[yellow]No Content:[/yellow] {total_stats['no_content']}")

    # Cost report
    cost_stats = cost_monitor.get_stats()
    console.print(f"\n[bold blue]API Usage:[/bold blue]")
    console.print(f"Total Calls: {cost_stats['total_calls']}")
    console.print(f"Input Tokens: {cost_stats['input_tokens']:,}")
    console.print(f"Output Tokens: {cost_stats['output_tokens']:,}")
    console.print(f"Estimated Cost: ${cost_stats['estimated_cost_usd']:.2f}")


def _show_prefilter_diagnostics(min_score: int, min_comments: int):
    """Show detailed diagnostics about prefilter state when no articles to process."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Count total scraped articles meeting criteria
        cursor.execute(
            """
            SELECT COUNT(*) FROM urls
            WHERE scraped_status = 'success'
            AND hn_score >= ? AND hn_comments >= ?
            """,
            (min_score, min_comments),
        )
        total_scraped = cursor.fetchone()[0]

        # Count already filtered (have content_category)
        cursor.execute(
            """
            SELECT content_category, COUNT(*) as count FROM urls
            WHERE scraped_status = 'success'
            AND content_category IS NOT NULL
            AND hn_score >= ? AND hn_comments >= ?
            GROUP BY content_category
            ORDER BY count DESC
            """,
            (min_score, min_comments),
        )
        by_category = cursor.fetchall()

        # Count pending (no content_category)
        cursor.execute(
            """
            SELECT COUNT(*) FROM urls
            WHERE scraped_status = 'success'
            AND content_category IS NULL
            AND hn_score >= ? AND hn_comments >= ?
            """,
            (min_score, min_comments),
        )
        pending = cursor.fetchone()[0]

        # Count total URLs in database
        cursor.execute("SELECT COUNT(*) FROM urls")
        total_urls = cursor.fetchone()[0]

        # Count scraped articles (any status)
        cursor.execute(
            """
            SELECT scraped_status, COUNT(*) FROM urls
            WHERE hn_score >= ? AND hn_comments >= ?
            GROUP BY scraped_status
            ORDER BY COUNT(*) DESC
            """,
            (min_score, min_comments),
        )
        by_scrape_status = cursor.fetchall()

        console.print("\n[bold blue]── Prefilter Diagnostics ──[/bold blue]")
        console.print(f"[dim]Filters: score >= {min_score}, comments >= {min_comments}[/dim]")
        console.print(f"")
        console.print(f"[bold]Database:[/bold] {total_urls:,} total URLs")
        console.print(f"")
        console.print(f"[bold]Scrape Status (matching filters):[/bold]")
        for status, count in by_scrape_status:
            console.print(f"  {status or 'NULL'}: {count:,}")
        console.print(f"")
        console.print(f"[bold]Content Filter Status (scraped & matching filters):[/bold]")
        console.print(f"  Already filtered: {sum(c[1] for c in by_category):,}")
        for category, count in by_category:
            color = "green" if category == "AI_DISCOURSE" else "blue" if category == "AI_NEWS" else "dim"
            console.print(f"    [{color}]{category}[/{color}]: {count:,}")
        console.print(f"  [yellow]Pending (NULL category):[/yellow] {pending:,}")
        console.print(f"")

        # If pending is 0 but we have articles, explain why
        if pending == 0 and total_scraped > 0:
            console.print("[dim]All scraped articles have been content-filtered.[/dim]")
        elif total_scraped == 0:
            console.print("[yellow]No scraped articles match the score/comment filters.[/yellow]")
            console.print("[dim]Try running the scraper (Phase 3) first, or lower --min-score/--min-comments.[/dim]")

    except Exception as e:
        console.print(f"[red]Error getting diagnostics: {e}[/red]")
    finally:
        if conn:
            conn.close()


def get_content_filter_stats() -> Dict[str, int]:
    """Get statistics about content-filtered articles."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Count by category
        cursor.execute(
            """
            SELECT content_category, COUNT(*) as count
            FROM urls
            WHERE content_category IS NOT NULL
            GROUP BY content_category
        """
        )
        categories = {row[0]: row[1] for row in cursor.fetchall()}

        # Total scraped but not filtered
        cursor.execute(
            """
            SELECT COUNT(*)
            FROM urls
            WHERE scraped_status = 'success'
            AND content_category IS NULL
        """
        )
        pending = cursor.fetchone()[0]

        return {
            "OPINION_CODING": categories.get("OPINION_CODING", 0),
            "NEWS_CODING": categories.get("NEWS_CODING", 0),
            "AI_OTHER": categories.get("AI_OTHER", 0),
            "NOT_AI": categories.get("NOT_AI", 0),
            "SKIPPED": categories.get("SKIPPED", 0),
            "pending": pending,
            "total_filtered": sum(v for k, v in categories.items() if k != "SKIPPED"),
        }
    except Exception:
        return {}
    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Content-based prefilter for scraped articles using Groq API."
    )
    parser.add_argument(
        "--api-key",
        help="Groq API key (or set GROQ_API_KEY in .env)",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose logging with streaming output",
    )
    parser.add_argument(
        "-b",
        "--batch-size",
        type=int,
        default=20,
        help="Batch size for processing (default: 20)",
    )
    parser.add_argument(
        "--min-score",
        type=int,
        default=20,
        help="Minimum HN score to filter (default: 20)",
    )
    parser.add_argument(
        "--min-comments",
        type=int,
        default=5,
        help="Minimum HN comments to filter (default: 5)",
    )
    parser.add_argument(
        "-l",
        "--limit",
        type=int,
        default=0,
        help="Maximum articles to process (0 = unlimited)",
    )
    parser.add_argument(
        "--relevant-only",
        action="store_true",
        default=True,
        dest="relevant_only",
        help="Only process URLs from relevant domains (default: True)",
    )
    parser.add_argument(
        "--all-domains",
        action="store_false",
        dest="relevant_only",
        help="Process URLs from all domains (disables --relevant-only)",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Clear existing content filter data before starting",
    )
    parser.add_argument(
        "--reset-only",
        action="store_true",
        help="Clear existing content filter data and exit (don't process)",
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Show content filter statistics and exit",
    )

    args = parser.parse_args()

    # Stats-only mode
    if args.stats:
        stats = get_content_filter_stats()
        console.print("\n[bold blue]Content Filter Statistics:[/bold blue]")
        console.print(f"  OPINION_CODING: {stats.get('OPINION_CODING', 0)}")
        console.print(f"  NEWS_CODING:    {stats.get('NEWS_CODING', 0)}")
        console.print(f"  AI_OTHER:       {stats.get('AI_OTHER', 0)}")
        console.print(f"  NOT_AI:         {stats.get('NOT_AI', 0)}")
        console.print(f"  SKIPPED:        {stats.get('SKIPPED', 0)}")
        console.print(f"  [dim]Pending:       {stats.get('pending', 0)}[/dim]")
        console.print(f"  Total Filtered: {stats.get('total_filtered', 0)}")
        exit(0)

    # Reset-only mode
    if args.reset_only:
        init_db()
        migrate_database()
        migrate_content_filter_columns()
        console.print("[bold yellow]Resetting content filter data...[/bold yellow]")
        affected = reset_content_filter_data(args.min_score, args.min_comments)
        console.print(
            f"[green]Reset {affected} articles - ready for re-filtering[/green]"
        )
        exit(0)

    # Get API key
    api_key = args.api_key or os.environ.get("GROQ_API_KEY")
    if not api_key:
        console.print("[bold red]Error: Groq API key is required.[/bold red]")
        console.print("Set GROQ_API_KEY in .env or provide --api-key argument.")
        exit(1)

    # Run the prefilter
    asyncio.run(
        prefilter_content(
            api_key,
            args.verbose,
            args.batch_size,
            args.min_score,
            args.min_comments,
            args.limit,
            args.relevant_only,
            args.reset,
        )
    )
