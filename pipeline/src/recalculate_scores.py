"""
Recalculate sentiment scores from stored utility/trajectory values.

This script updates sentiment_score for all articles that have classification_json,
using the current UTILITY_SCORES and TRAJECTORY_SCORES weights. This allows
adjusting the scoring formula without re-running the LLM.

Usage:
    python -m src.recalculate_scores [--dry-run]
"""

import argparse
import json
import sqlite3
from pathlib import Path

# Import score weights from sentiment_analyzer
from src.sentiment_analyzer import (
    UTILITY_SCORES,
    TRAJECTORY_SCORES,
    UTILITY_WEIGHT,
    TRAJECTORY_WEIGHT,
    derive_sentiment_score,
)

# Legacy utility mappings (from old schema)
LEGACY_UTILITY_MAP = {
    "positive": "tool",    # Old "positive" → new "tool"
    "negative": "toil",    # Old "negative" → new "toil"
    "mixed": "noise",      # Old "mixed" → new "noise"
}

# Legacy trajectory mappings (from old schema)
LEGACY_TRAJECTORY_MAP = {
    # Map any old values if needed
}

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DB_PATH = DATA_DIR / "pipeline.db"


def recalculate_scores(dry_run: bool = False) -> dict:
    """
    Recalculate sentiment_score for all articles with classification_json.

    Returns stats dict with counts.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Get all articles with classification_json
    cursor.execute("""
        SELECT url, sentiment_score, classification_json
        FROM urls
        WHERE classification_json IS NOT NULL
    """)

    rows = cursor.fetchall()

    stats = {
        "total": len(rows),
        "updated": 0,
        "unchanged": 0,
        "errors": 0,
        "score_changes": [],
    }

    print(f"Processing {stats['total']} articles with classification_json...")
    print(f"Utility weights: {UTILITY_SCORES}")
    print(f"Trajectory weights: {TRAJECTORY_SCORES}")
    print(f"Formula: utility × {UTILITY_WEIGHT} + trajectory × {TRAJECTORY_WEIGHT}")
    print()

    for url, old_score, classification_json in rows:
        try:
            data = json.loads(classification_json)
            utility = data.get("utility")
            trajectory = data.get("trajectory")

            if not utility or not trajectory:
                stats["errors"] += 1
                continue

            # Map legacy values to new schema
            if utility in LEGACY_UTILITY_MAP:
                utility = LEGACY_UTILITY_MAP[utility]
            if trajectory in LEGACY_TRAJECTORY_MAP:
                trajectory = LEGACY_TRAJECTORY_MAP[trajectory]

            # Skip if still not valid
            if utility not in UTILITY_SCORES or trajectory not in TRAJECTORY_SCORES:
                stats["errors"] += 1
                continue

            # Calculate new score using current weights
            new_score = derive_sentiment_score(utility, trajectory)

            # Check if score changed
            if old_score is not None and abs(new_score - old_score) < 0.001:
                stats["unchanged"] += 1
                continue

            # Record the change
            stats["score_changes"].append({
                "url": url[:50],
                "utility": utility,
                "trajectory": trajectory,
                "old": old_score,
                "new": new_score,
                "diff": new_score - (old_score or 0),
            })

            if not dry_run:
                cursor.execute(
                    "UPDATE urls SET sentiment_score = ? WHERE url = ?",
                    (new_score, url)
                )

            stats["updated"] += 1

        except (json.JSONDecodeError, KeyError) as e:
            stats["errors"] += 1
            continue

    if not dry_run:
        conn.commit()

    conn.close()

    return stats


def print_summary(stats: dict, dry_run: bool):
    """Print summary of changes."""
    print("=" * 60)
    if dry_run:
        print("DRY RUN - No changes made")
    else:
        print("SCORES UPDATED")
    print("=" * 60)
    print(f"Total articles:  {stats['total']}")
    print(f"Updated:         {stats['updated']}")
    print(f"Unchanged:       {stats['unchanged']}")
    print(f"Errors:          {stats['errors']}")
    print()

    if stats["score_changes"]:
        # Show sample of changes
        print("Sample changes (first 10):")
        print("-" * 60)
        for change in stats["score_changes"][:10]:
            old_str = f"{change['old']:.2f}" if change['old'] is not None else "None"
            print(f"  {change['utility']:7} + {change['trajectory']:11} : {old_str} → {change['new']:.2f} ({change['diff']:+.2f})")

        if len(stats["score_changes"]) > 10:
            print(f"  ... and {len(stats['score_changes']) - 10} more")

        # Calculate average change
        diffs = [c["diff"] for c in stats["score_changes"]]
        avg_diff = sum(diffs) / len(diffs) if diffs else 0
        print()
        print(f"Average score change: {avg_diff:+.3f}")


def main():
    parser = argparse.ArgumentParser(
        description="Recalculate sentiment scores from stored utility/trajectory"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without updating database"
    )

    args = parser.parse_args()

    stats = recalculate_scores(dry_run=args.dry_run)
    print_summary(stats, args.dry_run)


if __name__ == "__main__":
    main()
