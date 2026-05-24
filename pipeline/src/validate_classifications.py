"""
Validation script for sentiment classifications.

Flags suspicious classifications that may indicate prompt calibration issues:
1. Summary/utility mismatch - Negative words in summary but neutral utility
2. Zero-score high-engagement - Top articles with 0.0 score
3. Trajectory/content mismatch - Negative content with uncertain trajectory

Usage:
    python -m src.validate_classifications
    python -m src.validate_classifications --export suspicious.csv
"""

import argparse
import csv
import json
import re
import sqlite3
import sys
from pathlib import Path
from typing import Dict, List, Tuple

from rich.console import Console
from rich.table import Table

# Add src to path
current_dir = Path(__file__).resolve().parent
if str(current_dir) not in sys.path:
    sys.path.append(str(current_dir))

from store.db import get_db_connection

console = Console()

# Signal words that should trigger non-neutral classification
NEGATIVE_SIGNALS = {
    "reject", "rejected", "rejection", "fail", "failed", "failure", "failing",
    "broken", "concern", "concerns", "backlash", "criticism", "criticize",
    "problem", "problems", "issue", "issues", "limit", "limits", "limitation",
    "flaw", "flaws", "risk", "risks", "frustrat", "disappoint", "disappointed",
    "skeptic", "skeptical", "worry", "worried", "warning", "nightmare",
    "ruined", "struggle", "struggles", "struggling", "stopped", "quit",
    "abandoned", "hate", "hated", "waste", "wasted", "useless", "terrible",
    "awful", "disaster", "dangerous", "bad"
}

POSITIVE_SIGNALS = {
    "love", "loved", "loving", "excellent", "breakthrough", "revolutionary",
    "solved", "productive", "efficient", "game-changer", "impressive",
    "amazing", "incredible", "fantastic", "wonderful", "brilliant",
    "saves", "saved", "faster", "better", "improved", "innovation"
}

# Neutral utilities that contribute 0 to score
NEUTRAL_UTILITIES = {"noise", "informational", "speculative"}


def contains_signal_words(text: str, signals: set) -> List[str]:
    """Check if text contains any signal words and return matched words."""
    if not text:
        return []

    text_lower = text.lower()
    found = []
    for signal in signals:
        if signal in text_lower:
            found.append(signal)
    return found


def get_classified_articles(min_score: int = 20, limit: int = 500) -> List[Dict]:
    """Get recently classified articles for validation."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT id, url, hn_title, hn_score, hn_comments,
                   sentiment_score, classification_json
            FROM urls
            WHERE classification_json IS NOT NULL
            AND hn_score >= ?
            ORDER BY hn_score DESC
            LIMIT ?
            """,
            (min_score, limit),
        )

        articles = []
        for row in cursor.fetchall():
            try:
                classification = json.loads(row[6])
            except json.JSONDecodeError:
                continue

            articles.append({
                "id": row[0],
                "url": row[1],
                "hn_title": row[2],
                "hn_score": row[3],
                "hn_comments": row[4],
                "sentiment_score": row[5],
                "utility": classification.get("utility"),
                "trajectory": classification.get("trajectory"),
                "summary": classification.get("summary", ""),
                "subtopic": classification.get("subtopic"),
            })

        return articles

    except sqlite3.Error as e:
        console.print(f"[red]Database error: {e}[/red]")
        return []
    finally:
        if conn:
            conn.close()


def validate_articles(articles: List[Dict]) -> List[Dict]:
    """Validate articles and flag suspicious classifications."""
    flagged = []

    for article in articles:
        issues = []

        utility = article.get("utility", "")
        trajectory = article.get("trajectory", "")
        summary = article.get("summary", "")
        title = article.get("hn_title", "")
        score = article.get("sentiment_score", 0)

        combined_text = f"{title} {summary}".lower()

        # Check 1: Negative signals in title/summary but neutral utility
        neg_signals = contains_signal_words(combined_text, NEGATIVE_SIGNALS)
        if neg_signals and utility in NEUTRAL_UTILITIES:
            issues.append(f"NEG_SIGNALS_NEUTRAL: {', '.join(neg_signals[:3])}")

        # Check 2: Negative signals but uncertain trajectory
        if neg_signals and trajectory == "uncertain":
            issues.append(f"NEG_SIGNALS_UNCERTAIN: {', '.join(neg_signals[:3])}")

        # Check 3: Zero score for high-engagement articles
        if score == 0.0 and article.get("hn_score", 0) >= 100:
            issues.append("ZERO_SCORE_HIGH_ENGAGEMENT")

        # Check 4: Positive signals but negative/toil utility
        pos_signals = contains_signal_words(combined_text, POSITIVE_SIGNALS)
        if pos_signals and utility in ("toil", "hazard"):
            issues.append(f"POS_SIGNALS_NEG_UTILITY: {', '.join(pos_signals[:3])}")

        # Check 5: Summary mentions rejection/concern but score is neutral
        rejection_words = ["rejection", "rejected", "backlash", "concern", "concerns"]
        if any(w in summary.lower() for w in rejection_words) and score == 0.0:
            issues.append("REJECTION_IN_SUMMARY_ZERO_SCORE")

        if issues:
            flagged.append({
                **article,
                "issues": issues,
            })

    return flagged


def print_report(flagged: List[Dict]):
    """Print a Rich table report of flagged articles."""
    if not flagged:
        console.print("[green]✓ No suspicious classifications found![/green]")
        return

    console.print(f"\n[bold red]Found {len(flagged)} suspicious classifications:[/bold red]\n")

    # Group by issue type
    issue_counts: Dict[str, int] = {}
    for article in flagged:
        for issue in article["issues"]:
            issue_type = issue.split(":")[0]
            issue_counts[issue_type] = issue_counts.get(issue_type, 0) + 1

    console.print("[bold]Issue Summary:[/bold]")
    for issue_type, count in sorted(issue_counts.items(), key=lambda x: -x[1]):
        console.print(f"  • {issue_type}: {count}")
    console.print()

    # Print table of flagged articles
    table = Table(title="Flagged Articles (Top 30)", show_lines=True)
    table.add_column("ID", style="dim", width=6)
    table.add_column("Title", width=45, overflow="fold")
    table.add_column("U/T", width=15)
    table.add_column("Score", width=6)
    table.add_column("Issues", width=35, overflow="fold")

    for article in flagged[:30]:
        util_traj = f"{article['utility']}/{article['trajectory']}"
        score_str = f"{article['sentiment_score']:.2f}"
        issues_str = "\n".join(article["issues"])

        table.add_row(
            str(article["id"]),
            article["hn_title"][:45] if article["hn_title"] else "N/A",
            util_traj,
            score_str,
            issues_str,
        )

    console.print(table)


def export_to_csv(flagged: List[Dict], output_path: str):
    """Export flagged articles to CSV."""
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "id", "hn_title", "url", "hn_score", "hn_comments",
            "utility", "trajectory", "sentiment_score", "summary", "issues"
        ])
        writer.writeheader()

        for article in flagged:
            row = {
                "id": article["id"],
                "hn_title": article["hn_title"],
                "url": article["url"],
                "hn_score": article["hn_score"],
                "hn_comments": article["hn_comments"],
                "utility": article["utility"],
                "trajectory": article["trajectory"],
                "sentiment_score": article["sentiment_score"],
                "summary": article["summary"],
                "issues": "; ".join(article["issues"]),
            }
            writer.writerow(row)

    console.print(f"[green]Exported {len(flagged)} flagged articles to {output_path}[/green]")


def main():
    parser = argparse.ArgumentParser(
        description="Validate sentiment classifications and flag suspicious results."
    )
    parser.add_argument(
        "--min-score", type=int, default=20,
        help="Minimum HN score filter (default: 20)"
    )
    parser.add_argument(
        "--limit", type=int, default=1000,
        help="Maximum articles to check (default: 1000)"
    )
    parser.add_argument(
        "--export", type=str, default=None,
        help="Export flagged articles to CSV file"
    )

    args = parser.parse_args()

    console.print("[bold]Validating sentiment classifications...[/bold]\n")

    # Get articles
    articles = get_classified_articles(min_score=args.min_score, limit=args.limit)
    console.print(f"Checking {len(articles)} classified articles...")

    # Validate
    flagged = validate_articles(articles)

    # Report
    print_report(flagged)

    # Export if requested
    if args.export and flagged:
        export_to_csv(flagged, args.export)

    # Return exit code based on findings
    return 1 if len(flagged) > 50 else 0


if __name__ == "__main__":
    sys.exit(main())
