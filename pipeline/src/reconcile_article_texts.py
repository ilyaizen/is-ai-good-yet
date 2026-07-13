from __future__ import annotations

import argparse
import json
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping
from urllib.request import urlopen

from .store.paths import get_pipeline_data_dir, get_pipeline_db_path


@dataclass(frozen=True)
class ReconciliationSummary:
    scanned: int = 0
    updated: int = 0
    inserted: int = 0
    skipped: int = 0
    failed: int = 0


def fetch_hn_item(hn_id: int) -> Mapping[str, Any] | None:
    url = f"https://hacker-news.firebaseio.com/v0/item/{hn_id}.json"
    for attempt in range(3):
        try:
            with urlopen(url, timeout=15) as response:
                item = json.load(response)
            return item if isinstance(item, dict) else None
        except Exception:
            if attempt == 2:
                return None
            time.sleep(attempt + 1)
    return None


def parse_article_headers(path: Path) -> tuple[str, str]:
    title = ""
    url = ""
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            stripped = line.rstrip("\r\n")
            if not stripped:
                break
            if stripped.startswith("Title: "):
                title = stripped.removeprefix("Title: ").strip()
            elif stripped.startswith("URL: "):
                url = stripped.removeprefix("URL: ").strip()
    return title, url


def reconcile_article_texts(
    db_path: Path,
    text_dir: Path,
    *,
    fetch_item: Callable[[int], Mapping[str, Any] | None] = fetch_hn_item,
) -> ReconciliationSummary:
    article_paths = {
        int(path.stem): path
        for path in text_dir.glob("*.txt")
        if path.stem.isdigit()
    }
    article_ids = sorted(article_paths)

    connection = sqlite3.connect(db_path)
    try:
        database_ids = {
            row[0]
            for row in connection.execute("SELECT DISTINCT hn_id FROM urls WHERE hn_id IS NOT NULL")
        }
        database_urls = {
            row[0]: row[1]
            for row in connection.execute("SELECT url, hn_id FROM urls")
        }
    finally:
        connection.close()

    orphan_items: list[tuple[int, str, str, Mapping[str, Any]]] = []
    skipped = 0
    failed = 0
    for hn_id in sorted(set(article_ids) - database_ids):
        file_title, file_url = parse_article_headers(article_paths[hn_id])
        canonical_hn_id = database_urls.get(file_url)
        if canonical_hn_id is not None and canonical_hn_id != hn_id:
            skipped += 1
            continue
        item = fetch_item(hn_id)
        if not item:
            failed += 1
            continue
        url = file_url or str(item.get("url") or f"https://news.ycombinator.com/item?id={hn_id}")
        title = str(item.get("title") or file_title or "Untitled")
        orphan_items.append((hn_id, title, url, item))

    updated = 0
    inserted = 0
    connection = sqlite3.connect(db_path)
    try:
        for offset in range(0, len(article_ids), 500):
            chunk = article_ids[offset : offset + 500]
            placeholders = ",".join("?" for _ in chunk)
            cursor = connection.execute(
                f"""
                UPDATE urls
                SET scraped_status = 'success',
                    extract_error = NULL,
                    retry_count = 0,
                    last_retry_at = NULL,
                    failure_category = NULL
                WHERE hn_id IN ({placeholders})
                  AND COALESCE(scraped_status, '') != 'success'
                """,
                chunk,
            )
            updated += cursor.rowcount

        for hn_id, title, url, item in orphan_items:
            existing = connection.execute("SELECT id FROM urls WHERE url = ?", (url,)).fetchone()
            connection.execute(
                """
                INSERT INTO urls (
                    url, hn_id, hn_score, hn_comments, hn_title, hn_timestamp,
                    hn_author, status, scraped_status, extract_error, retry_count,
                    last_retry_at, failure_category
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 'resolved', 'success', NULL, 0, NULL, NULL)
                ON CONFLICT(url) DO UPDATE SET
                    hn_id = excluded.hn_id,
                    hn_score = excluded.hn_score,
                    hn_comments = excluded.hn_comments,
                    hn_title = excluded.hn_title,
                    hn_timestamp = excluded.hn_timestamp,
                    hn_author = excluded.hn_author,
                    scraped_status = 'success',
                    extract_error = NULL,
                    retry_count = 0,
                    last_retry_at = NULL,
                    failure_category = NULL
                """,
                (
                    url,
                    hn_id,
                    item.get("score") or 0,
                    item.get("descendants") or 0,
                    title,
                    item.get("time") or 0,
                    item.get("by") or "",
                ),
            )
            if existing:
                updated += 1
            else:
                inserted += 1

        connection.commit()
    finally:
        connection.close()

    return ReconciliationSummary(
        scanned=len(article_ids),
        updated=updated,
        inserted=inserted,
        skipped=skipped,
        failed=failed,
    )


def main() -> int:
    data_dir = get_pipeline_data_dir()
    parser = argparse.ArgumentParser(
        description="Register article text files in pipeline.db and repair stale scrape states."
    )
    parser.add_argument("--db", type=Path, default=get_pipeline_db_path())
    parser.add_argument("--text-dir", type=Path, default=data_dir / "articles-text")
    args = parser.parse_args()

    summary = reconcile_article_texts(args.db, args.text_dir)
    print(
        f"Scanned {summary.scanned}; inserted {summary.inserted}; "
        f"updated {summary.updated}; skipped {summary.skipped}; failed {summary.failed}."
    )
    return 1 if summary.failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
