from __future__ import annotations

import sqlite3
from pathlib import Path

from pipeline.src.reconcile_article_texts import reconcile_article_texts


def create_db(path: Path) -> None:
    connection = sqlite3.connect(path)
    connection.execute(
        """
        CREATE TABLE urls (
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
            extract_error TEXT,
            retry_count INTEGER DEFAULT 0,
            last_retry_at INTEGER,
            failure_category TEXT
        )
        """
    )
    connection.commit()
    connection.close()


def write_article(directory: Path, hn_id: int, title: str, url: str) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / f"{hn_id}.txt").write_text(
        f"Title: {title}\nURL: {url}\n\nArticle body",
        encoding="utf-8",
    )


def test_existing_failed_row_is_marked_scraped_when_text_exists(tmp_path: Path) -> None:
    db_path = tmp_path / "pipeline.db"
    text_dir = tmp_path / "articles-text"
    create_db(db_path)
    write_article(text_dir, 123, "Existing", "https://example.com/existing")

    connection = sqlite3.connect(db_path)
    connection.execute(
        """
        INSERT INTO urls (url, hn_id, status, scraped_status, extract_error, retry_count, failure_category)
        VALUES (?, ?, 'resolved', 'failed', 'timeout', 3, 'network')
        """,
        ("https://example.com/existing", 123),
    )
    connection.commit()
    connection.close()

    summary = reconcile_article_texts(db_path, text_dir, fetch_item=lambda _hn_id: None)

    connection = sqlite3.connect(db_path)
    row = connection.execute(
        "SELECT scraped_status, extract_error, retry_count, failure_category FROM urls WHERE hn_id = 123"
    ).fetchone()
    connection.close()

    assert row == ("success", None, 0, None)
    assert summary.updated == 1
    assert summary.inserted == 0


def test_orphan_text_file_is_inserted_with_hn_metadata(tmp_path: Path) -> None:
    db_path = tmp_path / "pipeline.db"
    text_dir = tmp_path / "articles-text"
    create_db(db_path)
    write_article(text_dir, 456, "Text title", "https://example.com/orphan")

    summary = reconcile_article_texts(
        db_path,
        text_dir,
        fetch_item=lambda hn_id: {
            "id": hn_id,
            "title": "HN title",
            "url": "https://example.com/orphan",
            "score": 91,
            "descendants": 24,
            "time": 1_700_000_000,
            "by": "alice",
        },
    )

    connection = sqlite3.connect(db_path)
    row = connection.execute(
        """
        SELECT url, hn_id, hn_score, hn_comments, hn_title, hn_timestamp,
               hn_author, status, scraped_status
        FROM urls WHERE hn_id = 456
        """
    ).fetchone()
    connection.close()

    assert row == (
        "https://example.com/orphan",
        456,
        91,
        24,
        "HN title",
        1_700_000_000,
        "alice",
        "resolved",
        "success",
    )
    assert summary.inserted == 1
    assert summary.failed == 0


def test_duplicate_url_keeps_existing_canonical_hn_submission(tmp_path: Path) -> None:
    db_path = tmp_path / "pipeline.db"
    text_dir = tmp_path / "articles-text"
    create_db(db_path)
    write_article(text_dir, 222, "Duplicate submission", "https://example.com/shared")

    connection = sqlite3.connect(db_path)
    connection.execute(
        """
        INSERT INTO urls (
            url, hn_id, hn_score, hn_comments, hn_title, hn_timestamp,
            hn_author, status, scraped_status
        ) VALUES (?, 111, 300, 80, 'Canonical', 1600000000, 'bob', 'analyzed', 'success')
        """,
        ("https://example.com/shared",),
    )
    connection.commit()
    connection.close()

    summary = reconcile_article_texts(
        db_path,
        text_dir,
        fetch_item=lambda hn_id: {
            "id": hn_id,
            "title": "Duplicate submission",
            "url": "https://example.com/shared",
            "score": 20,
            "descendants": 4,
            "time": 1_700_000_000,
            "by": "carol",
        },
    )

    connection = sqlite3.connect(db_path)
    row = connection.execute(
        "SELECT hn_id, hn_title, status, scraped_status FROM urls WHERE url = ?",
        ("https://example.com/shared",),
    ).fetchone()
    connection.close()

    assert row == (111, "Canonical", "analyzed", "success")
    assert summary.inserted == 0
    assert summary.skipped == 1
