"""
Analyze a single story by HN ID using Groq API.

Run sentiment analysis on a specific Hacker News story by its ID.
Useful for testing prompts and debugging classification on individual articles.

Usage (from project root):
    python pipeline/src/analyze_single.py 46515696
    python pipeline/src/analyze_single.py 46515696 -v --show-prompt
"""

import asyncio
import argparse
import json
import os
import sys
from pathlib import Path

# Ensure proper path for imports (works from any directory)
current_dir = Path(__file__).resolve().parent
pipeline_src = current_dir
if str(pipeline_src) not in sys.path:
    sys.path.insert(0, str(pipeline_src))

from dotenv import load_dotenv
from groq import AsyncGroq
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
import polars as pl

# Load environment variables from .env file
env_path = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(env_path)

from store.db import get_db_connection, init_db
from store.parquet import read_articles
from sentiment_analyzer import (
    GROQ_MODEL,
    SENTIMENT_SYSTEM_PROMPT,
    SENTIMENT_USER_PROMPT_TEMPLATE,
    truncate_text,
    validate_response,
    derive_sentiment_score,
    update_sentiment_result,
)

console = Console()


def get_article_by_hn_id(hn_id: int) -> dict | None:
    """
    Get article metadata from database by HN ID.

    Returns dict with url, hn_title, hn_score, hn_comments, content_category, sentiment_score
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT url, hn_title, hn_score, hn_comments, content_category,
                   sentiment_score, classification_json, scraped_status
            FROM urls
            WHERE hn_id = ?
            """,
            (hn_id,),
        )
        row = cursor.fetchone()

        if not row:
            return None

        return {
            "url": row[0],
            "hn_title": row[1],
            "hn_score": row[2],
            "hn_comments": row[3],
            "content_category": row[4],
            "sentiment_score": row[5],
            "classification_json": row[6],
            "scraped_status": row[7],
        }

    except Exception as e:
        console.print(f"[red]Error fetching article: {e}[/red]")
        return None
    finally:
        if conn:
            conn.close()


def get_article_content(url: str) -> str | None:
    """Get article content from parquet store."""
    try:
        data_dir = current_dir.parent / "data" / "articles"
        if not data_dir.exists():
            console.print(f"[yellow]Parquet directory not found: {data_dir}[/yellow]")
            return None

        lf = read_articles(shard_dir=data_dir)
        filtered = lf.filter(pl.col("url") == url).select(["text"])
        df = filtered.collect()

        if df.is_empty():
            return None

        return df.row(0)[0]

    except Exception as e:
        console.print(f"[red]Error reading content: {e}[/red]")
        return None


async def analyze_single_article(
    client: AsyncGroq,
    title: str,
    text: str,
    verbose: bool = False,
) -> dict | None:
    """
    Analyze a single article and return full results.

    Returns dict with score, result, metrics, raw_response
    """
    from datetime import datetime, timezone

    # Format and truncate content
    clean_text = " ".join(text.split())
    truncated_text = truncate_text(clean_text)

    user_prompt = SENTIMENT_USER_PROMPT_TEMPLATE.format(
        title=title or "Untitled",
        text=truncated_text,
    )
    prompt_chars = len(SENTIMENT_SYSTEM_PROMPT) + len(user_prompt)

    if verbose:
        console.print(f"\n[dim]Prompt length: {len(user_prompt)} chars[/dim]")
        console.print(f"[dim]Content truncated: {len(text)} -> {len(truncated_text)} chars[/dim]")

    try:
        import time
        start_time = time.perf_counter()

        response = await client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": SENTIMENT_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.6,
            max_completion_tokens=2048,
            top_p=0.95,
            response_format={"type": "json_object"},
        )

        end_time = time.perf_counter()
        inference_time_ms = (end_time - start_time) * 1000

        content = (response.choices[0].message.content or "").strip()
        input_tokens = response.usage.prompt_tokens if response.usage else 0
        output_tokens = response.usage.completion_tokens if response.usage else 0

        # Parse JSON response
        import re
        if "<think>" in content:
            think_end = content.find("</think>")
            if think_end != -1:
                content = content[think_end + 8:].strip()

        if "```" in content:
            match = re.search(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", content)
            if match:
                content = match.group(1)

        if not content.strip().startswith("{"):
            match = re.search(r"\{[\s\S]*\}", content)
            if match:
                content = match.group(0)

        result = json.loads(content)

        # Validate
        is_valid, error_msg = validate_response(result)
        if not is_valid:
            console.print(f"[red]Validation error: {error_msg}[/red]")
            return {"raw_response": content, "error": error_msg}

        # Derive score
        score = derive_sentiment_score(result["utility"], result["trajectory"])
        tokens_per_second = output_tokens / (inference_time_ms / 1000) if inference_time_ms > 0 else 0

        return {
            "score": score,
            "result": result,
            "metrics": {
                "model": GROQ_MODEL,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": input_tokens + output_tokens,
                "inference_time_ms": round(inference_time_ms, 1),
                "tokens_per_second": round(tokens_per_second, 1),
                "prompt_chars": prompt_chars,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
            "raw_response": content,
        }

    except Exception as e:
        console.print(f"[red]API Error: {e}[/red]")
        return None


def display_results(hn_id: int, article: dict, analysis: dict):
    """Display analysis results in a formatted panel."""
    result = analysis.get("result", {})
    score = analysis.get("score", 0)
    metrics = analysis.get("metrics", {})

    # Score color
    if score > 0.2:
        score_color = "green"
        sentiment = "POSITIVE"
    elif score < -0.2:
        score_color = "red"
        sentiment = "NEGATIVE"
    else:
        score_color = "yellow"
        sentiment = "MIXED"

    # Build output table
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Field", style="bold")
    table.add_column("Value")

    table.add_row("HN ID", str(hn_id))
    table.add_row("Title", article["hn_title"][:80])
    table.add_row("URL", article["url"][:80])
    table.add_row("HN Score", str(article["hn_score"]))
    table.add_row("Category", article["content_category"] or "N/A")
    table.add_row("", "")
    table.add_row(f"[{score_color}]Sentiment Score[/{score_color}]", f"[{score_color}]{score:+.2f} ({sentiment})[/{score_color}]")
    table.add_row("Utility", result.get("utility", "N/A"))
    table.add_row("Trajectory", result.get("trajectory", "N/A"))
    table.add_row("Subtopic", result.get("subtopic", "N/A"))
    table.add_row("Primary Theme", result.get("primary_theme", "N/A"))
    table.add_row("Secondary Theme", result.get("secondary_theme") or "None")
    table.add_row("", "")
    table.add_row("Summary", result.get("summary", "N/A"))

    quotes = result.get("quotes", [])
    if quotes:
        table.add_row("", "")
        table.add_row("Quotes", "")
        for i, quote in enumerate(quotes[:3], 1):
            table.add_row("", f"  {i}. \"{quote[:100]}...\"" if len(quote) > 100 else f"  {i}. \"{quote}\"")

    table.add_row("", "")
    table.add_row("[dim]Model[/dim]", f"[dim]{metrics.get('model', 'N/A')}[/dim]")
    table.add_row("[dim]Tokens[/dim]", f"[dim]{metrics.get('input_tokens', 0)} in / {metrics.get('output_tokens', 0)} out[/dim]")
    table.add_row("[dim]Latency[/dim]", f"[dim]{metrics.get('inference_time_ms', 0):.0f}ms[/dim]")

    console.print(Panel(table, title=f"[bold]Analysis for HN #{hn_id}[/bold]", border_style="blue"))


async def main(
    hn_id: int,
    verbose: bool = False,
    save: bool = False,
    show_prompt: bool = False,
    show_raw: bool = False,
):
    """Main function to analyze a single story."""
    init_db()

    # Get article metadata
    article = get_article_by_hn_id(hn_id)
    if not article:
        console.print(f"[red]Article with HN ID {hn_id} not found in database.[/red]")
        return

    console.print(f"\n[bold blue]Analyzing HN #{hn_id}[/bold blue]")
    console.print(f"[dim]Title: {article['hn_title']}[/dim]")

    # Check scrape status
    if article["scraped_status"] != "success":
        console.print(f"[yellow]Warning: Article scrape status is '{article['scraped_status']}'[/yellow]")

    # Get content
    content = get_article_content(article["url"])
    if not content:
        console.print(f"[red]No content found for this article.[/red]")
        return

    console.print(f"[dim]Content length: {len(content)} chars[/dim]")

    # Show prompt if requested
    if show_prompt:
        clean_text = " ".join(content.split())
        truncated = truncate_text(clean_text)
        user_prompt = SENTIMENT_USER_PROMPT_TEMPLATE.format(
            title=article["hn_title"],
            text=truncated,
        )
        console.print("\n[bold]System Prompt:[/bold]")
        console.print(Panel(SENTIMENT_SYSTEM_PROMPT, border_style="dim"))
        console.print("\n[bold]User Prompt:[/bold]")
        console.print(Panel(user_prompt[:2000] + "..." if len(user_prompt) > 2000 else user_prompt, border_style="dim"))

    # Get API key
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        console.print("[red]Error: GROQ_API_KEY not set in environment.[/red]")
        return

    # Analyze
    client = AsyncGroq(api_key=api_key)
    console.print("\n[cyan]Calling Groq API...[/cyan]")

    analysis = await analyze_single_article(
        client,
        article["hn_title"],
        content,
        verbose,
    )

    if not analysis:
        console.print("[red]Analysis failed.[/red]")
        return

    if "error" in analysis:
        console.print(f"[red]Analysis error: {analysis['error']}[/red]")
        if show_raw:
            console.print("\n[bold]Raw Response:[/bold]")
            console.print(analysis.get("raw_response", "N/A"))
        return

    # Display results
    display_results(hn_id, article, analysis)

    # Show raw response if requested
    if show_raw:
        console.print("\n[bold]Raw JSON Response:[/bold]")
        console.print(json.dumps(analysis["result"], indent=2))

    # Save to database if requested
    if save:
        metrics_json = json.dumps(analysis.get("metrics"))
        update_sentiment_result(
            article["url"],
            analysis["score"],
            json.dumps(analysis["result"]),
            metrics_json,
        )
        console.print(f"\n[green]Results saved to database.[/green]")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Analyze a single story by HN ID using Groq API."
    )
    parser.add_argument(
        "hn_id",
        type=int,
        help="Hacker News story ID (e.g., 46515696)",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose output",
    )
    parser.add_argument(
        "-s",
        "--save",
        action="store_true",
        help="Save results to database",
    )
    parser.add_argument(
        "--show-prompt",
        action="store_true",
        help="Show the full prompt sent to the LLM",
    )
    parser.add_argument(
        "--show-raw",
        action="store_true",
        help="Show raw JSON response from LLM",
    )

    args = parser.parse_args()

    asyncio.run(
        main(
            hn_id=args.hn_id,
            verbose=args.verbose,
            save=args.save,
            show_prompt=args.show_prompt,
            show_raw=args.show_raw,
        )
    )
