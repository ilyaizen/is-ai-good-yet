#!/usr/bin/env python
"""
Utility: Fix HN ID Mismatch

When the resolver picks the wrong HN post for a URL (due to Algolia matching
multiple posts), this script allows manual correction by specifying the correct HN ID.

Usage:
    python src/fix_hn_id.py <hn_id> [--url <url>]
    python src/fix_hn_id.py 46574276  # Fetches metadata from Algolia and updates DB
    python src/fix_hn_id.py 46574276 --url https://antirez.com/news/158  # Specify URL explicitly
"""

import argparse
import requests
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "pipeline.db"


def get_hn_item(hn_id: int) -> dict:
    """Fetch HN item metadata from Algolia."""
    url = f"http://hn.algolia.com/api/v1/items/{hn_id}"
    response = requests.get(url)
    if response.status_code != 200:
        raise ValueError(f"Failed to fetch HN item {hn_id}: {response.status_code}")
    return response.json()


def fix_hn_id(hn_id: int, target_url: str = None): # type: ignore
    """Fix the HN ID for a URL in the database."""
    # Fetch metadata from Algolia
    print(f"Fetching HN item {hn_id} from Algolia...")
    item = get_hn_item(hn_id)

    article_url = item.get("url")
    title = item.get("title", "")
    score = item.get("points", 0) or 0
    comments = item.get("children", [])
    num_comments = len(comments) if isinstance(comments, list) else 0
    # Algolia items API doesn't return num_comments directly, use search API
    search_url = "http://hn.algolia.com/api/v1/search"
    search_resp = requests.get(search_url, params={"query": str(hn_id), "tags": "story"})
    if search_resp.status_code == 200:
        hits = search_resp.json().get("hits", [])
        for hit in hits:
            if str(hit.get("objectID")) == str(hn_id):
                num_comments = hit.get("num_comments", 0) or 0
                score = hit.get("points", 0) or 0
                break

    timestamp = item.get("created_at_i", 0)
    author = item.get("author", "")

    print(f"  Title: {title}")
    print(f"  URL: {article_url}")
    print(f"  Score: {score}, Comments: {num_comments}")

    # Determine which URL to update
    url_to_update = target_url or article_url
    if not url_to_update:
        raise ValueError("No URL found in HN item and none specified with --url")

    # Update database
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Check if URL exists
    cursor.execute("SELECT hn_id, hn_title FROM urls WHERE url = ?", (url_to_update,))
    existing = cursor.fetchone()

    if existing:
        old_hn_id, old_title = existing
        print(f"\nUpdating existing entry:")
        print(f"  Old HN ID: {old_hn_id} -> New HN ID: {hn_id}")
        print(f"  Old Title: {old_title}")
        print(f"  New Title: {title}")

        cursor.execute("""
            UPDATE urls SET
                hn_id = ?,
                hn_score = ?,
                hn_comments = ?,
                hn_title = ?,
                hn_timestamp = ?,
                hn_author = ?
            WHERE url = ?
        """, (hn_id, score, num_comments, title, timestamp, author, url_to_update))
    else:
        print(f"\nInserting new entry for URL: {url_to_update}")
        cursor.execute("""
            INSERT INTO urls (url, hn_id, hn_score, hn_comments, hn_title, hn_timestamp, hn_author, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'resolved')
        """, (url_to_update, hn_id, score, num_comments, title, timestamp, author))

    conn.commit()
    print(f"\n✓ Successfully updated database for HN ID {hn_id}")
    conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Fix HN ID mismatch by fetching correct metadata from Algolia",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python src/fix_hn_id.py 46574276
  python src/fix_hn_id.py 46574276 --url https://antirez.com/news/158
        """
    )
    parser.add_argument("hn_id", type=int, help="The correct HN ID to use")
    parser.add_argument("--url", type=str, help="Target URL to update (optional, uses HN item URL if not specified)")

    args = parser.parse_args()
    fix_hn_id(args.hn_id, args.url)
