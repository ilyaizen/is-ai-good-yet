#!/usr/bin/env python3
"""Bootstrap pipeline/data/pipeline.db from the exported static article data.

This is a recovery tool for fresh checkouts where the mutable pipeline DB is
missing. It reconstructs the SQLite rows from:
- src/lib/data/articles.json
- src/lib/data/llm-metrics.json

The goal is not to invent data. It mirrors the latest exported pipeline state
already checked into the repo so local admin tooling can read a real DB again.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sqlite3
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
ARTICLES_PATH = REPO_ROOT / "src" / "lib" / "data" / "articles.json"
METRICS_PATH = REPO_ROOT / "src" / "lib" / "data" / "llm-metrics.json"
DATA_DIR = REPO_ROOT / "pipeline" / "data"
DB_PATH = DATA_DIR / "pipeline.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS urls (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    url TEXT UNIQUE NOT NULL,
    hn_id INTEGER,
    hn_score INTEGER,
    hn_comments INTEGER,
    hn_title TEXT,
    hn_timestamp INTEGER,
    hn_author TEXT,
    status TEXT DEFAULT 'pending',
    scraped_status TEXT,
    filter_score INTEGER,
    opinion TEXT,
    is_opinion BOOLEAN,
    sentiment_score REAL,
    content_category TEXT,
    content_confidence REAL,
    classification_json TEXT,
    content_filter_json TEXT,
    extract_error TEXT,
    retry_count INTEGER DEFAULT 0,
    last_retry_at INTEGER,
    failure_category TEXT,
    groq_metrics_json TEXT
);

CREATE TABLE IF NOT EXISTS prefilter_state (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS themes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sentiment_group TEXT NOT NULL,
    theme_title TEXT NOT NULL,
    theme_description TEXT NOT NULL,
    sentiment_verdict TEXT,
    article_count INTEGER DEFAULT 0,
    model TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(sentiment_group, theme_title)
);
"""


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def json_dump(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def ensure_parent_dirs() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def bootstrap_db(force: bool) -> dict[str, int]:
    if not ARTICLES_PATH.exists():
        raise FileNotFoundError(f"Missing articles export: {ARTICLES_PATH}")
    if not METRICS_PATH.exists():
        raise FileNotFoundError(f"Missing metrics export: {METRICS_PATH}")

    if DB_PATH.exists():
        if not force:
            raise FileExistsError(
                f"{DB_PATH} already exists. Use --force to rebuild it from the exported data."
            )
        backup_path = DB_PATH.with_suffix(".bak")
        if backup_path.exists():
            backup_path.unlink()
        shutil.copy2(DB_PATH, backup_path)
        DB_PATH.unlink()

    ensure_parent_dirs()

    articles = load_json(ARTICLES_PATH)
    metrics = load_json(METRICS_PATH)
    source_metrics_by_id = {str(key): value for key, value in metrics.items()}

    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA synchronous = NORMAL")
        conn.executescript(SCHEMA)
        conn.execute("DELETE FROM urls")
        conn.execute("DELETE FROM prefilter_state")
        conn.execute("DELETE FROM themes")

        refused = 0
        approved = 0
        latest_timestamp = 0

        for article in sorted(articles, key=lambda item: (item.get("hn_timestamp") or 0, item.get("hn_id") or 0)):
            hn_id = article["hn_id"]
            latest_timestamp = max(latest_timestamp, int(article.get("hn_timestamp") or 0))
            source = source_metrics_by_id.get(str(hn_id), {})
            prefilter = dict(source.get("prefilter", {}).get("response", {}) or {})
            classifier = dict(source.get("sentiment", {}).get("response", {}) or {})
            prefilter_metrics = source.get("prefilter", {}).get("metrics")
            classifier_metrics = source.get("sentiment", {}).get("metrics")

            prefilter.setdefault("reject", False)
            classifier.setdefault("reject", False)

            content_category = prefilter.get("category") or None
            content_confidence = prefilter.get("confidence")
            classification_json = json_dump(classifier) if classifier else None
            content_filter_json = json_dump(prefilter) if prefilter else None

            groq_metrics: dict[str, Any] = {}
            if prefilter_metrics:
                groq_metrics["prefilter"] = prefilter_metrics
            if classifier_metrics:
                groq_metrics["classifier"] = classifier_metrics
            groq_metrics_json = json_dump(groq_metrics) if groq_metrics else None

            is_refused = bool(prefilter.get("reject")) or bool(classifier.get("reject")) or (
                content_category is not None and content_category != "AI_DISCOURSE"
            )
            if is_refused:
                refused += 1
            else:
                approved += 1

            conn.execute(
                """
                INSERT INTO urls (
                    url,
                    hn_id,
                    hn_score,
                    hn_comments,
                    hn_title,
                    hn_timestamp,
                    hn_author,
                    status,
                    scraped_status,
                    filter_score,
                    opinion,
                    is_opinion,
                    sentiment_score,
                    content_category,
                    content_confidence,
                    classification_json,
                    content_filter_json,
                    extract_error,
                    retry_count,
                    last_retry_at,
                    failure_category,
                    groq_metrics_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    article["url"],
                    hn_id,
                    article.get("hn_score"),
                    article.get("hn_comments"),
                    article.get("hn_title"),
                    article.get("hn_timestamp"),
                    article.get("hn_author"),
                    "analyzed" if classifier else "prefiltered",
                    "success",
                    None,
                    None,
                    None,
                    article.get("sentiment_score"),
                    content_category,
                    content_confidence,
                    classification_json,
                    content_filter_json,
                    None,
                    0,
                    None,
                    None,
                    groq_metrics_json,
                ),
            )

        if latest_timestamp:
            conn.execute(
                "INSERT OR REPLACE INTO prefilter_state (key, value) VALUES (?, ?)",
                ("last_catch_up", str(latest_timestamp)),
            )

        conn.commit()
        return {"articles": len(articles), "approved": approved, "refused": refused}
    finally:
        conn.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Bootstrap pipeline/data/pipeline.db from exported JSON.")
    parser.add_argument("--force", action="store_true", help="Overwrite an existing pipeline.db")
    args = parser.parse_args()

    summary = bootstrap_db(force=args.force)
    print(f"Created {DB_PATH}")
    print(f"Rows: {summary['articles']}  approved: {summary['approved']}  refused: {summary['refused']}")
    if summary["refused"] == 0:
        print("Note: the checked-in exported data contains no refusals, so refused-links will still be empty.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
