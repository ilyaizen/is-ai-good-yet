"""
Sentiment analysis for AI_DISCOURSE articles.

This module analyzes scraped articles that have been classified as AI_DISCOURSE
using a 2-dimension approach (utility + trajectory) to derive a sentiment score.

Uses Groq API (openai/gpt-oss-20b) for analysis with JSON response format.
"""

import sys
import io
import asyncio
import logging
import argparse
import os
import json
import re
import time
from pathlib import Path
from datetime import datetime, timezone
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
GROQ_MODEL = "openai/gpt-oss-20b"

# Maximum characters to send to the LLM (truncation limit)
MAX_CONTENT_LENGTH = 8000

# Minimum characters for valid content (skip too-short articles)
MIN_CONTENT_LENGTH = 500

# Valid values for each field (v4.0 - Simplified)
VALID_UTILITY = {
    "magic",    # Game-changer, major productivity gain
    "tool",     # Net positive with caveats
    "mixed",    # Genuinely balanced or unclear
    "toil",     # Net negative, more work than value
    "hazard",   # Actively harmful, significant risks
}
VALID_TRAJECTORY = {"optimistic", "uncertain", "pessimistic"}
VALID_TOPICS = {"productivity", "quality", "workflow", "evaluation"}

# Score derivation weights (v4.0 - Equal weighting)
# Both dimensions matter equally for "Is AI Good Yet?"
# Max possible: magic(2.0) × 0.5 + optimistic(2.0) × 0.5 = +2.0
# Min possible: hazard(-2.0) × 0.5 + pessimistic(-2.0) × 0.5 = -2.0
UTILITY_SCORES = {
    "magic": 2.0,   # Game-changer - strongly positive
    "tool": 1.0,    # Net positive with caveats
    "mixed": 0.0,   # Genuinely balanced or unclear
    "toil": -1.0,   # Net negative - more work than value
    "hazard": -2.0, # Actively harmful
}
TRAJECTORY_SCORES = {
    "optimistic": 2.0,   # Improving rapidly
    "uncertain": 0.0,    # Genuine wait-and-see
    "pessimistic": -2.0, # Stalled or hitting limits
}
UTILITY_WEIGHT = 0.5
TRAJECTORY_WEIGHT = 0.5

# Scale bounds for frontend display mapping
# Max: magic(2.0) × 0.5 + optimistic(2.0) × 0.5 = +2.0
# Min: hazard(-2.0) × 0.5 + pessimistic(-2.0) × 0.5 = -2.0
SENTIMENT_MIN = -2.0
SENTIMENT_MAX = 2.0

# Sentiment Analysis Prompt (v4.1 - Research Findings Support)
SENTIMENT_SYSTEM_PROMPT = """Act as a Cynical Principal Engineer analyzing developer discourse about AI coding tools and workflows.

Your task: Extract the author's sentiment about AI coding tools from this article. If the article lacks developer opinion/experience/findings, REJECT it.

## REJECTION CHECK (Do First)

REJECT the article if ANY of these apply:
- Product announcement without author experience/opinion/findings
- Tutorial, course, book, or educational content
- Pure methodology research (no clear findings about AI coding effectiveness)
- AI news without developer perspective or empirical data
- Not about coding/development workflows

DO NOT REJECT if:
- Research presents CLEAR FINDINGS about AI coding tool effectiveness (e.g., "17% lower scores", "2x productivity")
- Article has explicit conclusions about whether AI helps or hinders coding

If rejecting, return: {"reject": true, "reason": "<why this isn't developer discourse>"}

## If NOT Rejecting, Analyze Sentiment

### Utility (Is it useful NOW?) - 5-tier scale:
- `magic`: Game-changer. "Can't imagine going back", "10x productivity"
- `tool`: Net positive with caveats. "Saves time but needs oversight"
- `mixed`: Genuinely balanced. "Great for X, terrible for Y"
- `toil`: Net negative. "Spent more time fixing than it saved"
- `hazard`: Actively harmful. "Broke production", "Created tech debt"

### Trajectory (Where is it heading?) - 3-tier scale:
- `optimistic`: "Each version better", "Limitations are temporary"
- `uncertain`: "Too early to tell", "Jury's still out"
- `pessimistic`: "Fundamental limits", "Same bugs for months"

### Topic (What aspect of AI coding?):
- `productivity`: Speed, efficiency, shipping faster, time saved
- `quality`: Correctness, bugs, hallucinations, reliability, trust
- `workflow`: Integration, context, ergonomics, learning curve
- `evaluation`: Tool comparisons, recommendations, adoption decisions

## Signal Words (require non-neutral classification):
NEGATIVE: rejected, failed, broken, frustrat, disappoint, skeptic, waste, useless
POSITIVE: love, excellent, breakthrough, productive, game-changer, amazing, 10x

## Decision Examples:

| Article                                                 | Utility | Trajectory  | Topic        |
| ------------------------------------------------------- | ------- | ----------- | ------------ |
| "Cursor ruined my workflow"                             | toil    | pessimistic | workflow     |
| "Shipped 2x faster with Claude"                         | tool    | optimistic  | productivity |
| "AI code review catches real bugs"                      | tool    | optimistic  | quality      |
| "Copilot vs Cursor: my verdict"                         | tool    | uncertain   | evaluation   |
| "AI hallucinations are a dealbreaker"                   | hazard  | pessimistic | quality      |
| "Study: AI assistance reduces skill mastery by 17%"     | mixed   | uncertain   | quality      |

## Summary Guidelines:
- Express a VERDICT, not a description
- Good: "Claude excels at refactoring but hallucinates API details"
- Bad: "Article discusses AI coding tools" (too vague)

Return valid JSON only:
```json
{
  "utility": "magic" | "tool" | "mixed" | "toil" | "hazard",
  "trajectory": "optimistic" | "uncertain" | "pessimistic",
  "topic": "productivity" | "quality" | "workflow" | "evaluation",
  "summary": "<max 25 words: blunt verdict>",
  "quotes": ["<relevant quote 1>", "<relevant quote 2>"]
}
```"""

SENTIMENT_USER_PROMPT_TEMPLATE = """Title: "{title}"
Content: "{text}"
"""


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


def format_article_for_prompt(title: str, text: str) -> str:
    """Format article for the prompt - title + single-line content."""
    # Strip multiple newlines to single spaces
    clean_text = " ".join(text.split())
    return title, clean_text  # pyright: ignore[reportReturnType]


def derive_sentiment_score(utility: str, trajectory: str) -> float:
    """
    Derive a -2 to 2 sentiment score from utility and trajectory.

    Formula: score = (utility_score * 0.4) + (trajectory_score * 0.6)

    Examples:
    - magic + optimistic = +2.00
    - tool + optimistic = +1.76
    - tool + uncertain = +0.56
    - noise + uncertain = 0.00
    - toil + uncertain = -0.56
    - toil + pessimistic = -1.76
    - hazard + pessimistic = -2.00
    """
    utility_score = UTILITY_SCORES.get(utility, 0.0)
    trajectory_score = TRAJECTORY_SCORES.get(trajectory, 0.0)
    return (utility_score * UTILITY_WEIGHT) + (trajectory_score * TRAJECTORY_WEIGHT)


def normalize_topic(topic: Optional[str]) -> Optional[str]:
    """
    Map invalid topics to valid ones using fuzzy matching.

    Valid topics: productivity, quality, workflow, evaluation

    This handles common LLM mistakes and synonyms.
    """
    if topic is None:
        return None

    topic_lower = topic.lower().strip()

    # Already valid - return as-is
    if topic_lower in VALID_TOPICS:
        return topic_lower

    # Comprehensive mappings for common LLM errors
    TOPIC_MAPPINGS = {
        # Productivity-related
        "speed": "productivity",
        "efficiency": "productivity",
        "time": "productivity",
        "fast": "productivity",
        "shipping": "productivity",
        "velocity": "productivity",
        "automation": "productivity",
        "coding": "productivity",  # Legacy subtopic
        # Quality-related
        "correctness": "quality",
        "accuracy": "quality",
        "reliability": "quality",
        "bugs": "quality",
        "hallucination": "quality",
        "hallucinations": "quality",
        "errors": "quality",
        "trust": "quality",
        "security": "quality",
        "model": "quality",  # Legacy subtopic - model capabilities → quality
        # Workflow-related
        "integration": "workflow",
        "ergonomics": "workflow",
        "context": "workflow",
        "tooling": "workflow",  # Legacy subtopic
        "ide": "workflow",
        "editor": "workflow",
        "ux": "workflow",
        "experience": "workflow",
        "adoption": "workflow",
        "learning": "workflow",
        # Evaluation-related
        "comparison": "evaluation",
        "recommendation": "evaluation",
        "review": "evaluation",
        "benchmark": "evaluation",
        "choice": "evaluation",
        "decision": "evaluation",
        "society": "evaluation",  # Legacy subtopic - adoption decisions
    }

    mapped = TOPIC_MAPPINGS.get(topic_lower)
    if mapped:
        logging.debug(f"Mapped topic '{topic}' -> '{mapped}'")
        return mapped

    # Fallback: "workflow" as the most generic topic
    logging.debug(f"Unknown topic '{topic}' mapped to 'workflow'")
    return "workflow"


def validate_response(result: Dict[str, Any]) -> Tuple[bool, str]:
    """Validate the LLM response structure and values (v4.0 - simplified schema)."""
    errors = []

    # Normalize topic before validation
    if "topic" in result:
        result["topic"] = normalize_topic(result["topic"])

    # Required fields (v4.0 - simplified, no themes)
    required = [
        "utility",
        "trajectory",
        "topic",
        "summary",
        "quotes",
    ]
    for field in required:
        if field not in result:
            errors.append(f"Missing required field: {field}")

    # Validate enum values
    if result.get("utility") not in VALID_UTILITY:
        errors.append(f"Invalid utility: {result.get('utility')}")

    if result.get("trajectory") not in VALID_TRAJECTORY:
        errors.append(f"Invalid trajectory: {result.get('trajectory')}")

    if result.get("topic") not in VALID_TOPICS:
        errors.append(f"Invalid topic: {result.get('topic')}")

    # Validate summary is a string
    summary = result.get("summary")
    if summary is not None and not isinstance(summary, str):
        errors.append("summary must be a string")

    # Validate quotes is a list of strings
    quotes = result.get("quotes")
    if quotes is not None:
        if not isinstance(quotes, list):
            errors.append("quotes must be a list")
        elif not all(isinstance(q, str) for q in quotes):
            errors.append("quotes must contain only strings")

    if errors:
        return False, "; ".join(errors)
    return True, ""


def truncate_text(text: str, max_length: int = MAX_CONTENT_LENGTH) -> str:
    """
    Truncate text using head+tail strategy to preserve intro and conclusion.

    - First ~40% from beginning (thesis, introduction)
    - Last ~60% from end (conclusion, summary, verdict)
    - Middle section omitted (supporting details)

    Emphasizes conclusions since authors often summarize their verdict at the end.
    """
    if len(text) <= max_length:
        return text

    # Calculate head and tail sizes (40% head, 60% tail)
    head_size = int(max_length * 0.4)
    tail_size = max_length - head_size - 50  # Reserve space for separator

    # Extract head - try to break at word boundary
    head = text[:head_size]
    last_space = head.rfind(" ")
    if last_space > head_size * 0.9:
        head = head[:last_space]

    # Extract tail - try to break at word boundary
    tail = text[-tail_size:]
    first_space = tail.find(" ")
    if first_space > 0 and first_space < tail_size * 0.1:
        tail = tail[first_space + 1 :]

    return f"{head}\n\n[… middle section omitted …]\n\n{tail}"


def get_articles_for_analysis(
    batch_size: int = 50,
    min_score: int = 20,
    min_comments: int = 5,
    reanalyze: bool = False,
) -> List[Tuple[str, str, int]]:
    """
    Get AI_DISCOURSE articles for sentiment analysis.

    NOTE: Only AI_DISCOURSE articles are analyzed. AI_NEWS articles are
    classified in Phase 3 but excluded from sentiment analysis since they
    don't contribute to the verdict score.

    Args:
        batch_size: Maximum number of articles to return
        min_score: Minimum HN score filter
        min_comments: Minimum HN comments filter
        reanalyze: If True, include already-analyzed articles

    Returns list of tuples: (url, hn_title, hn_id)
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Base query for AI_DISCOURSE articles only (AI_NEWS excluded from sentiment analysis)
        if reanalyze:
            where_clause = """
                WHERE content_category = 'AI_DISCOURSE'
                AND scraped_status = 'success'
                AND hn_score >= ?
                AND hn_comments >= ?
            """
        else:
            where_clause = """
                WHERE content_category = 'AI_DISCOURSE'
                AND scraped_status = 'success'
                AND sentiment_score IS NULL
                AND hn_score >= ?
                AND hn_comments >= ?
            """

        cursor.execute(
            f"""
            SELECT url, hn_title, hn_id
            FROM urls
            {where_clause}
            ORDER BY hn_score DESC
            LIMIT ?
            """,
            (min_score, min_comments, batch_size),
        )
        return cursor.fetchall()

    except Exception as e:
        logging.error(f"Error fetching articles for analysis: {e}")
        return []
    finally:
        if conn:
            conn.close()


def get_pending_analysis_count(
    min_score: int = 20,
    min_comments: int = 5,
) -> int:
    """Get count of AI_DISCOURSE articles pending sentiment analysis."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT COUNT(*)
            FROM urls
            WHERE content_category = 'AI_DISCOURSE'
            AND scraped_status = 'success'
            AND sentiment_score IS NULL
            AND hn_score >= ?
            AND hn_comments >= ?
            """,
            (min_score, min_comments),
        )
        return cursor.fetchone()[0]
    except Exception:
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


def update_sentiment_result(
    url: str,
    sentiment_score: float,
    result_json: str,
    metrics_json: Optional[str] = None,
):
    """Update sentiment analysis results for a URL, including optional speed metrics."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        if metrics_json:
            # Merge with existing metrics (preserve prefilter metrics if present)
            cursor.execute("SELECT groq_metrics_json FROM urls WHERE url = ?", (url,))
            existing = cursor.fetchone()
            existing_metrics = {}
            if existing and existing[0]:
                try:
                    existing_metrics = json.loads(existing[0])
                except json.JSONDecodeError:
                    pass

            existing_metrics["classifier"] = json.loads(metrics_json)
            merged_metrics = json.dumps(existing_metrics)

            cursor.execute(
                """
                UPDATE urls
                SET sentiment_score = ?,
                    classification_json = ?,
                    status = 'analyzed',
                    groq_metrics_json = ?
                WHERE url = ?
                """,
                (sentiment_score, result_json, merged_metrics, url),
            )
        else:
            cursor.execute(
                """
                UPDATE urls
                SET sentiment_score = ?,
                    classification_json = ?,
                    status = 'analyzed'
                WHERE url = ?
                """,
                (sentiment_score, result_json, url),
            )
        conn.commit()
    except Exception as e:
        logging.error(f"Error updating sentiment for {url}: {e}")
    finally:
        if conn:
            conn.close()


def update_content_category(url: str, category: str):
    """Update content_category for a URL (used when analyzer rejects as non-AI-coding)."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE urls
            SET content_category = ?
            WHERE url = ?
            """,
            (category, url),
        )
        conn.commit()
    except Exception as e:
        logging.error(f"Error updating content_category for {url}: {e}")
    finally:
        if conn:
            conn.close()


def reset_sentiment_data(
    min_score: int = 20,
    min_comments: int = 5,
) -> int:
    """Reset sentiment analysis data for all AI_DISCOURSE articles."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE urls
            SET sentiment_score = NULL,
                classification_json = NULL,
                status = 'prefiltered'
            WHERE content_category = 'AI_DISCOURSE'
            AND hn_score >= ?
            AND hn_comments >= ?
            """,
            (min_score, min_comments),
        )
        affected = cursor.rowcount
        conn.commit()
        logging.info(f"Reset sentiment data for {affected} articles")
        return affected
    except Exception as e:
        logging.error(f"Error resetting sentiment data: {e}")
        return 0
    finally:
        if conn:
            conn.close()


async def analyze_sentiment_with_groq(
    client: AsyncGroq,
    title: str,
    text: str,
    cost_monitor: CostMonitor,
    verbose: bool = False,
    retry_count: int = 0,
    max_tokens: int = 8192,
) -> Optional[Dict[str, Any]]:
    """
    Analyze article sentiment using Groq API with JSON response format.

    Returns dict with sentiment analysis fields including derived score.
    Implements retry with exponential backoff for transient JSON validation failures.
    """
    MAX_RETRIES = 2

    # Format and truncate content
    _, clean_text = format_article_for_prompt(title, text)
    truncated_text = truncate_text(clean_text)

    user_prompt = SENTIMENT_USER_PROMPT_TEMPLATE.format(
        title=title or "Untitled",
        text=truncated_text,
    )

    # Track prompt character count for metrics
    prompt_chars = len(truncated_text)

    try:
        # START TIMING
        start_time = time.perf_counter()

        # Get non-streaming response with JSON format
        response = await client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": SENTIMENT_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=1,
            max_completion_tokens=max_tokens,
            top_p=0.95,            reasoning_effort="low",
            response_format={"type": "json_object"},
        )

        # END TIMING
        end_time = time.perf_counter()
        inference_time_ms = (end_time - start_time) * 1000

        # Extract content and usage
        content = (response.choices[0].message.content or "").strip()
        input_tokens = response.usage.prompt_tokens if response.usage else 0
        output_tokens = response.usage.completion_tokens if response.usage else 0
        tokens_per_second = (
            output_tokens / (inference_time_ms / 1000) if inference_time_ms > 0 else 0
        )

        try:
            # Check for refusals (model says it can't analyze)
            refusal_phrases = [
                "cannot analyze",
                "can't analyze",
                "unable to analyze",
                "not enough content",
                "insufficient content",
            ]
            if any(phrase in content.lower() for phrase in refusal_phrases):
                logging.warning(f"Analysis refused: insufficient content")
                cost_monitor.add_call(input_tokens, output_tokens, False)
                return None

            # Clean up if wrapped in markdown
            if "```" in content:
                match = re.search(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", content)
                if match:
                    content = match.group(1)
                else:
                    lines = content.split("\n")
                    lines = [l for l in lines if not l.strip().startswith("```")]
                    content = "\n".join(lines).strip()

            # Handle thinking tags from LLM models
            if "<think>" in content:
                think_end = content.find("</think>")
                if think_end != -1:
                    content = content[think_end + 8 :].strip()

            # Find JSON object in response
            if not content.strip().startswith("{"):
                match = re.search(r"\{[\s\S]*\}", content)
                if match:
                    content = match.group(0)
                else:
                    logging.error(
                        f"No JSON object found in response: {content[:200]}..."
                    )
                    cost_monitor.add_call(input_tokens, output_tokens, False)
                    return None

            result = json.loads(content)

            # Check for rejection response (v4.0 - explicit reject field)
            if result.get("reject") is True:
                reason = result.get("reason", "Content rejected by analyzer")
                logging.warning(f"Rejected: {reason[:100]}")
                cost_monitor.add_call(input_tokens, output_tokens, True)  # Still a successful API call
                return {"is_rejected": True, "reason": reason}

            # Check for N/A values in required fields (legacy fallback)
            na_values = {"n/a", "na", "N/A", "NA", None}
            if (
                result.get("utility") in na_values
                or result.get("trajectory") in na_values
            ):
                note = result.get("note", result.get("reason", "Article doesn't match criteria"))
                logging.warning(f"N/A response: {note[:100]}")
                cost_monitor.add_call(input_tokens, output_tokens, True)
                return {"is_rejected": True, "reason": note}

            # Validate response
            is_valid, error_msg = validate_response(result)
            if not is_valid:
                logging.warning(f"Invalid response: {error_msg}")
                cost_monitor.add_call(input_tokens, output_tokens, False)
                return None

            # Derive sentiment score
            score = derive_sentiment_score(result["utility"], result["trajectory"])

            # Add metadata
            result["model"] = GROQ_MODEL
            result["analyzed_at"] = datetime.now(timezone.utc).isoformat()

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
                "score": score,
                "result": result,
                "metrics": metrics,
            }

        except json.JSONDecodeError as e:
            logging.error(f"Failed to parse JSON: {content[:300]}...")
            cost_monitor.add_call(input_tokens, output_tokens, False)
            return None

    except Exception as e:
        error_str = str(e)
        # Handle Groq JSON validation failures with retry
        if "400" in error_str and "json_validate_failed" in error_str:
            if retry_count < MAX_RETRIES:
                # Check if it's a max tokens issue
                if "max completion tokens" in error_str.lower():
                    new_max_tokens = (
                        3072  # Increase significantly for token limit issues
                    )
                    logging.warning(
                        f"Max tokens hit, retrying with {new_max_tokens} tokens (attempt {retry_count + 2}/{MAX_RETRIES + 1})"
                    )
                else:
                    new_max_tokens = max_tokens
                    logging.warning(
                        f"JSON validation failed, retrying (attempt {retry_count + 2}/{MAX_RETRIES + 1})"
                    )

                # Exponential backoff: 1s, 2s, 4s...
                await asyncio.sleep(1 * (2**retry_count))

                return await analyze_sentiment_with_groq(
                    client,
                    title,
                    text,
                    cost_monitor,
                    verbose,
                    retry_count=retry_count + 1,
                    max_tokens=new_max_tokens,
                )
            else:
                logging.error(
                    f"JSON validation failed after {MAX_RETRIES + 1} attempts: {error_str[:200]}"
                )

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
    stats = {
        "success": 0,
        "failed": 0,
        "no_content": 0,
        "too_short": 0,
        "reclassified": 0,
    }

    # Get article content
    urls = [item[0] for item in batch]
    content_map = get_article_content_batch(urls)

    for url, title, hn_id in batch:
        if interactive.check_shutdown():
            break

        await interactive.wait_if_paused()

        text = content_map.get(url)
        if not text:
            logging.warning(f"[yellow]No content[/yellow] for #{hn_id} - skipping")
            stats["no_content"] += 1
            progress.advance(task_id)
            continue

        # Skip too-short articles
        if len(text.strip()) < MIN_CONTENT_LENGTH:
            logging.warning(
                f"[yellow]Too short[/yellow] ({len(text)} chars) #{hn_id} - skipping"
            )
            stats["too_short"] += 1
            progress.advance(task_id)
            continue

        # Show article being processed
        if verbose:
            console.print(f"\n[bold cyan]#{hn_id}[/bold cyan] {title[:60]}...")

        result = await analyze_sentiment_with_groq(
            client, title, text, cost_monitor, verbose
        )

        if result and result.get("is_rejected"):
            # Rejected - article lacks developer opinion/experience, reclassify to AI_OTHER
            update_content_category(url, "AI_OTHER")
            reason = result.get("reason", "Not developer discourse")[:50]
            console.print(
                f"  [magenta][~] Rejected[/magenta] → AI_OTHER - {reason}..."
            )
            stats["reclassified"] += 1
        elif result and "score" in result:
            # Extract metrics if present
            metrics_json = (
                json.dumps(result.get("metrics")) if result.get("metrics") else None
            )

            update_sentiment_result(
                url,
                result["score"],
                json.dumps(result["result"]),
                metrics_json,
            )

            # Color-code by sentiment score
            score = result["score"]
            if score > 0.2:
                color = "green"
                sentiment = "positive"
                icon = "[+]"
            elif score < -0.2:
                color = "red"
                sentiment = "negative"
                icon = "[-]"
            else:
                color = "yellow"
                sentiment = "mixed"
                icon = "[~]"

            utility = result["result"]["utility"]
            trajectory = result["result"]["trajectory"]
            summary = result["result"].get("summary", "")[:50]

            console.print(
                f"  [{color}]{icon} {sentiment:8}[/{color}] ({score:+.2f}) "
                f"[dim]{utility}/{trajectory}[/dim] - {summary}"
            )
            stats["success"] += 1
        else:
            console.print(f"  [red][!] Failed to analyze[/red]")
            stats["failed"] += 1

        progress.advance(task_id)

    return stats


def _show_sentiment_diagnostics(min_score: int, min_comments: int):
    """Show detailed diagnostics about sentiment analysis state when no articles to process."""
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

        # Count by content_category
        cursor.execute(
            """
            SELECT content_category, COUNT(*) as count FROM urls
            WHERE scraped_status = 'success'
            AND hn_score >= ? AND hn_comments >= ?
            GROUP BY content_category
            ORDER BY count DESC
            """,
            (min_score, min_comments),
        )
        by_category = cursor.fetchall()

        # Count AI_DISCOURSE that are already analyzed
        cursor.execute(
            """
            SELECT COUNT(*) FROM urls
            WHERE content_category = 'AI_DISCOURSE'
            AND scraped_status = 'success'
            AND sentiment_score IS NOT NULL
            AND hn_score >= ? AND hn_comments >= ?
            """,
            (min_score, min_comments),
        )
        analyzed = cursor.fetchone()[0]

        # Count AI_DISCOURSE pending analysis
        cursor.execute(
            """
            SELECT COUNT(*) FROM urls
            WHERE content_category = 'AI_DISCOURSE'
            AND scraped_status = 'success'
            AND sentiment_score IS NULL
            AND hn_score >= ? AND hn_comments >= ?
            """,
            (min_score, min_comments),
        )
        pending = cursor.fetchone()[0]

        # Count articles without content_category (need prefilter first)
        cursor.execute(
            """
            SELECT COUNT(*) FROM urls
            WHERE scraped_status = 'success'
            AND content_category IS NULL
            AND hn_score >= ? AND hn_comments >= ?
            """,
            (min_score, min_comments),
        )
        need_prefilter = cursor.fetchone()[0]

        console.print("\n[bold blue]── Sentiment Diagnostics ──[/bold blue]")
        console.print(f"[dim]Filters: score >= {min_score}, comments >= {min_comments}[/dim]")
        console.print(f"")
        console.print(f"[bold]Scraped Articles (matching filters):[/bold] {total_scraped:,}")
        console.print(f"")
        console.print(f"[bold]By Content Category:[/bold]")
        for category, count in by_category:
            if category == "AI_DISCOURSE":
                console.print(f"  [green]{category}[/green]: {count:,} (analyzed: {analyzed:,}, pending: {pending:,})")
            elif category is None:
                console.print(f"  [yellow]NULL (needs prefilter)[/yellow]: {count:,}")
            else:
                color = "blue" if category == "AI_NEWS" else "dim"
                console.print(f"  [{color}]{category}[/{color}]: {count:,}")
        console.print(f"")

        # Explain state
        if pending == 0 and analyzed > 0:
            console.print("[dim]All AI_DISCOURSE articles have been sentiment-analyzed.[/dim]")
        elif need_prefilter > 0:
            console.print(f"[yellow]{need_prefilter:,} articles still need content prefiltering (Phase 4) first.[/yellow]")
            console.print("[dim]Run prefilter to classify articles into AI_DISCOURSE/AI_NEWS/etc.[/dim]")
        elif total_scraped == 0:
            console.print("[yellow]No scraped articles match the score/comment filters.[/yellow]")
            console.print("[dim]Try running the scraper (Phase 3) first, or lower --min-score/--min-comments.[/dim]")
        else:
            ai_discourse_count = next((c[1] for c in by_category if c[0] == "AI_DISCOURSE"), 0)
            if ai_discourse_count == 0:
                console.print("[yellow]No AI_DISCOURSE articles found after prefiltering.[/yellow]")
                console.print("[dim]All articles were classified as AI_NEWS, AI_OTHER, NOISE, or SKIPPED.[/dim]")

    except Exception as e:
        console.print(f"[red]Error getting diagnostics: {e}[/red]")
    finally:
        if conn:
            conn.close()


def show_stats():
    """Display sentiment analysis statistics."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Total OPINION_CODING articles
        cursor.execute("""
            SELECT COUNT(*) FROM urls
            WHERE content_category = 'AI_DISCOURSE'
            AND scraped_status = 'success'
        """)
        total_opinion = cursor.fetchone()[0]

        # Analyzed articles
        cursor.execute("""
            SELECT COUNT(*) FROM urls
            WHERE content_category = 'AI_DISCOURSE'
            AND scraped_status = 'success'
            AND sentiment_score IS NOT NULL
        """)
        analyzed = cursor.fetchone()[0]

        # Pending articles
        pending = total_opinion - analyzed

        # Score distribution
        cursor.execute("""
            SELECT
                SUM(CASE WHEN sentiment_score > 0.2 THEN 1 ELSE 0 END) as positive,
                SUM(CASE WHEN sentiment_score BETWEEN -0.2 AND 0.2 THEN 1 ELSE 0 END) as mixed,
                SUM(CASE WHEN sentiment_score < -0.2 THEN 1 ELSE 0 END) as negative,
                AVG(sentiment_score) as avg_score
            FROM urls
            WHERE sentiment_score IS NOT NULL
        """)
        row = cursor.fetchone()
        positive = row[0] or 0
        mixed = row[1] or 0
        negative = row[2] or 0
        avg_score = row[3] or 0

        # Utility distribution
        cursor.execute("""
            SELECT
                json_extract(classification_json, '$.utility') as utility,
                COUNT(*) as count
            FROM urls
            WHERE classification_json IS NOT NULL
            GROUP BY utility
            ORDER BY count DESC
        """)
        utilities = cursor.fetchall()

        # Trajectory distribution
        cursor.execute("""
            SELECT
                json_extract(classification_json, '$.trajectory') as trajectory,
                COUNT(*) as count
            FROM urls
            WHERE classification_json IS NOT NULL
            GROUP BY trajectory
            ORDER BY count DESC
        """)
        trajectories = cursor.fetchall()

        console.print("\n[bold blue]Sentiment Analysis Statistics[/bold blue]")
        console.print(f"  Total AI_DISCOURSE: {total_opinion}")
        console.print(f"  [green]Analyzed:[/green] {analyzed}")
        console.print(f"  [dim]Pending:[/dim] {pending}")

        if analyzed > 0:
            console.print(f"\n[bold]Score Distribution:[/bold]")
            console.print(
                f"  [green]Positive (>0.2):[/green] {positive} ({positive / analyzed * 100:.1f}%)"
            )
            console.print(
                f"  [yellow]Mixed (-0.2 to 0.2):[/yellow] {mixed} ({mixed / analyzed * 100:.1f}%)"
            )
            console.print(
                f"  [red]Negative (<-0.2):[/red] {negative} ({negative / analyzed * 100:.1f}%)"
            )
            console.print(f"  [bold]Average Score:[/bold] {avg_score:+.3f}")

            if utilities:
                console.print(f"\n[bold]Utility Distribution:[/bold]")
                for utility, count in utilities:
                    console.print(f"  {utility or 'unknown'}: {count}")

            if trajectories:
                console.print(f"\n[bold]Trajectory Distribution:[/bold]")
                for trajectory, count in trajectories:
                    console.print(f"  {trajectory or 'unknown'}: {count}")

    except Exception as e:
        console.print(f"[red]Error getting stats: {e}[/red]")
    finally:
        if conn:
            conn.close()


async def analyze_sentiment(
    api_key: str,
    verbose: bool = False,
    batch_size: int = 20,
    min_score: int = 20,
    min_comments: int = 5,
    limit: int = 0,
    reanalyze: bool = False,
    reset: bool = False,
):
    """
    Main function to analyze sentiment using Groq API.

    Args:
        api_key: Groq API key
        verbose: Enable verbose logging with streaming output
        batch_size: Number of articles per batch
        min_score: Minimum HN score filter (default: 20)
        min_comments: Minimum HN comments filter (default: 5)
        limit: Maximum articles to process (0 = unlimited)
        reanalyze: Include already-analyzed articles
        reset: Clear existing scores before starting
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
        console.print("[bold yellow]Resetting sentiment data...[/bold yellow]")
        affected = reset_sentiment_data(min_score, min_comments)
        console.print(f"[green]Reset {affected} articles[/green]")

    # Check pending count
    pending_count = get_pending_analysis_count(min_score, min_comments)

    if pending_count == 0 and not reanalyze:
        console.print(
            "[bold green]No AI_DISCOURSE articles need sentiment analysis.[/bold green]"
        )
        # Show diagnostic info when verbose to help debug
        if verbose:
            _show_sentiment_diagnostics(min_score, min_comments)
        return

    if limit > 0:
        target_count = min(pending_count if not reanalyze else limit, limit)
    else:
        target_count = pending_count if not reanalyze else pending_count

    console.print(
        f"\n[bold blue]Found {pending_count} articles pending analysis[/bold blue]"
    )
    console.print(f"[bold blue]Processing up to {target_count} articles[/bold blue]")
    console.print(f"[dim]Model: {GROQ_MODEL} (JSON response format)[/dim]")

    # Display active filters
    filters = []
    if min_score > 0:
        filters.append(f"score >= {min_score}")
    if min_comments > 0:
        filters.append(f"comments >= {min_comments}")
    if reanalyze:
        filters.append("re-analyzing all")
    if filters:
        console.print(f"[dim]Filters: {', '.join(filters)}[/dim]")

    # Setup graceful shutdown
    interactive = InteractiveSession(console)
    interactive.start()

    # Cost monitoring
    cost_monitor = CostMonitor()

    total_stats = {
        "success": 0,
        "failed": 0,
        "no_content": 0,
        "too_short": 0,
        "reclassified": 0,
    }
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
        analysis_task_id = progress.add_task(
            "[cyan]Analyzing Sentiment...",
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
            batch = get_articles_for_analysis(
                fetch_size, min_score, min_comments, reanalyze
            )

            if not batch:
                console.print("[green]No more articles to process.[/green]")
                break

            batch_stats = await process_batch(
                client,
                batch,
                cost_monitor,
                progress,
                analysis_task_id,
                interactive,
                verbose,
            )

            for key in total_stats:
                total_stats[key] += batch_stats[key]

            processed += len(batch)

    # Final report
    console.print("\n[bold]Sentiment Analysis Complete![/bold]")
    console.print(f"[green]Analyzed:[/green] {total_stats['success']}")
    if total_stats["reclassified"] > 0:
        console.print(
            f"[magenta]Reclassified to AI_OTHER:[/magenta] {total_stats['reclassified']}"
        )
    if total_stats["failed"] > 0:
        console.print(f"[red]Failed:[/red] {total_stats['failed']}")
    if total_stats["no_content"] > 0:
        console.print(f"[yellow]No Content:[/yellow] {total_stats['no_content']}")
    if total_stats["too_short"] > 0:
        console.print(f"[yellow]Too Short:[/yellow] {total_stats['too_short']}")

    # Cost report
    cost_stats = cost_monitor.get_stats()
    console.print(f"\n[bold blue]API Usage:[/bold blue]")
    console.print(f"Total Calls: {cost_stats['total_calls']}")
    console.print(f"Input Tokens: {cost_stats['input_tokens']:,}")
    console.print(f"Output Tokens: {cost_stats['output_tokens']:,}")
    console.print(f"Estimated Cost: ${cost_stats['estimated_cost_usd']:.2f}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Sentiment analysis for AI_DISCOURSE articles using Groq API."
    )
    parser.add_argument(
        "--api-key",
        help="Groq API key (or set GROQ_API_KEY in .env)",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose logging with detailed output",
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
        "--reset",
        action="store_true",
        help="Clear existing sentiment scores before starting",
    )
    parser.add_argument(
        "--reset-only",
        action="store_true",
        help="Clear existing sentiment scores and exit (don't analyze)",
    )
    parser.add_argument(
        "--reanalyze",
        action="store_true",
        help="Include already-analyzed articles (don't skip)",
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Show sentiment analysis statistics and exit",
    )

    args = parser.parse_args()

    # Stats-only mode
    if args.stats:
        show_stats()
        exit(0)

    # Reset-only mode
    if args.reset_only:
        init_db()
        migrate_database()
        console.print("[bold yellow]Resetting sentiment data...[/bold yellow]")
        affected = reset_sentiment_data(args.min_score, args.min_comments)
        console.print(
            f"[green]Reset {affected} articles - ready for re-analysis[/green]"
        )
        exit(0)

    # Get API key
    api_key = args.api_key or os.environ.get("GROQ_API_KEY")
    if not api_key:
        console.print("[bold red]Error: Groq API key is required.[/bold red]")
        console.print("Set GROQ_API_KEY in .env or provide --api-key argument.")
        exit(1)

    # Run the analyzer
    asyncio.run(
        analyze_sentiment(
            api_key,
            args.verbose,
            args.batch_size,
            args.min_score,
            args.min_comments,
            args.limit,
            args.reanalyze,
            args.reset,
        )
    )
