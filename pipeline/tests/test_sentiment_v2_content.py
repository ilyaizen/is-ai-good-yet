from pathlib import Path
import sqlite3

import polars as pl

from pipeline.src.store.text_store import TextArticleStore
from pipeline.src import hn_comments_v2, sentiment_v2, v2_prefilter
from pipeline.src.store import db
from pipeline.src.store.v2 import init_v2_schema


def test_get_article_content_falls_back_to_text_store_for_missing_parquet_url(
    tmp_path: Path, monkeypatch,
) -> None:
    text_store = TextArticleStore(tmp_path / "articles-text")
    text_store.save_article(
        202,
        "Text-only article",
        None,
        None,
        "https://example.com/text-only",
        "Body from the reconciled text store.",
    )
    parquet = pl.DataFrame(
        {
            "url": ["https://example.com/parquet"],
            "text": ["Body from Parquet."],
        }
    ).lazy()
    monkeypatch.setattr(sentiment_v2, "read_articles", lambda _directory: parquet)
    monkeypatch.setattr(sentiment_v2, "TextArticleStore", lambda: text_store)

    content = sentiment_v2.get_article_content(
        [
            {"hn_id": 101, "url": "https://example.com/parquet"},
            {"hn_id": 202, "url": "https://example.com/text-only"},
        ]
    )

    assert content == {
        "https://example.com/parquet": "Body from Parquet.",
        "https://example.com/text-only": "Body from the reconciled text store.",
    }


def test_v2_stage_queries_process_each_hn_story_once(tmp_path: Path, monkeypatch) -> None:
    db_path = tmp_path / "pipeline.db"
    monkeypatch.setattr(db, "DB_PATH", db_path)
    connection = sqlite3.connect(db_path)
    connection.execute(
        """
        CREATE TABLE urls (
            id INTEGER PRIMARY KEY,
            url TEXT UNIQUE NOT NULL,
            hn_id INTEGER,
            hn_score INTEGER,
            hn_comments INTEGER,
            hn_title TEXT,
            hn_timestamp INTEGER,
            scraped_status TEXT
        )
        """
    )
    connection.executemany(
        "INSERT INTO urls VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        [
            (1, "https://example.com/older", 42, 100, 10, "Story", 1, "success"),
            (2, "https://example.com/canonical", 42, 100, 20, "Story", 2, "success"),
        ],
    )
    connection.commit()
    connection.close()
    init_v2_schema()
    assert v2_prefilter.pending_rows(None, False) == [
        {"hn_id": 42, "hn_title": "Story", "url": "https://example.com/canonical"}
    ]
    connection = sqlite3.connect(db_path)
    connection.execute(
        """
        INSERT INTO v2_prefilter_decisions VALUES (
            42, 'prefilter-v2.0.0', 'prompt', 'hash', 'input', 1,
            '["general"]', 'eligible', 'reason', 'model', 'now'
        )
        """
    )
    connection.commit()
    connection.close()

    assert [row["hn_id"] for row in sentiment_v2.get_story_rows(None, False)] == [42]
    assert hn_comments_v2.get_story_ids(None, 20, 5) == [42]
