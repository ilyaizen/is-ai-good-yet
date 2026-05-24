#!/usr/bin/env python3
"""
Reclassify sterile articles from AI_DISCOURSE to AI_OTHER.

These are articles that passed the content prefilter but the sentiment analyzer
determined they're not actually about AI coding tools/workflows.
"""

import argparse
import json
import sqlite3
import sys
from pathlib import Path

# Fix Windows console encoding for Unicode characters
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except (AttributeError, OSError):
        # reconfigure not available or failed, ignore
        pass

DB_PATH = Path(__file__).parent.parent / "data" / "pipeline.db"

# Patterns that indicate the article isn't about AI coding
STERILE_PATTERNS = [
    "not about ai coding",
    "not ai coding",
    "not about ai coding tools",
    "not ai coding tools",
    "not an ai coding",
    "not about ai",
    "not an opinion",
    "no opinion",
    "no sentiment expressed",
    "not relevant",
    "mismatched analysis",
    "no actual sentiment",
    "doesn't express",
    "does not express",
    "does not mention ai coding",
    "no ai coding discussion",
]


def find_sterile_articles(conn: sqlite3.Connection) -> list[dict]:
    """Find AI_DISCOURSE articles with sterile summaries."""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, hn_id, hn_title, sentiment_score, classification_json
        FROM urls
        WHERE content_category = 'AI_DISCOURSE'
          AND classification_json IS NOT NULL
    """)

    sterile = []
    for row in cursor.fetchall():
        id_, hn_id, title, score, cj = row
        try:
            analysis = json.loads(cj)
            summary = analysis.get("summary", "").lower()

            # Check if summary matches any sterile pattern
            for pattern in STERILE_PATTERNS:
                if pattern in summary:
                    sterile.append({
                        "id": id_,
                        "hn_id": hn_id,
                        "title": title,
                        "score": score,
                        "summary": analysis.get("summary", ""),
                        "matched_pattern": pattern,
                    })
                    break
        except json.JSONDecodeError:
            continue

    return sterile


def reclassify_articles(conn: sqlite3.Connection, article_ids: list[int], dry_run: bool = False) -> int:
    """Update articles to AI_OTHER category."""
    if dry_run or not article_ids:
        return 0

    cursor = conn.cursor()
    placeholders = ",".join("?" * len(article_ids))
    cursor.execute(f"""
        UPDATE urls
        SET content_category = 'AI_OTHER'
        WHERE id IN ({placeholders})
    """, article_ids)
    conn.commit()
    return cursor.rowcount


def main():
    parser = argparse.ArgumentParser(description="Reclassify sterile articles from AI_DISCOURSE to AI_OTHER")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be changed without making changes")
    parser.add_argument("-v", "--verbose", action="store_true", help="Show detailed output")
    args = parser.parse_args()

    conn = sqlite3.connect(DB_PATH)

    print("Scanning for sterile articles...")
    sterile = find_sterile_articles(conn)

    if not sterile:
        print("No sterile articles found.")
        conn.close()
        return

    print(f"\nFound {len(sterile)} sterile articles:\n")

    for article in sterile:
        print(f"  [{article['hn_id']}] {article['title'][:60]}...")
        if args.verbose:
            print(f"    Score: {article['score']}")
            print(f"    Summary: {article['summary']}")
            print(f"    Pattern: '{article['matched_pattern']}'")
        print()

    if args.dry_run:
        print(f"DRY RUN: Would reclassify {len(sterile)} articles to AI_OTHER")
    else:
        article_ids = [a["id"] for a in sterile]
        count = reclassify_articles(conn, article_ids)
        print(f"Reclassified {count} articles from AI_DISCOURSE to AI_OTHER")

    conn.close()


if __name__ == "__main__":
    main()
