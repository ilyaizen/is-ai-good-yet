from pathlib import Path
import asyncio
import json
import sqlite3

import polars as pl
from pipeline.src import hn_comments_v2, sentiment_v2, v2_prefilter
from pipeline.src.store import db
from pipeline.src.store.v2 import init_v2_schema, replace_selection


def test_get_article_content_falls_back_to_text_store_for_missing_parquet_url(
    tmp_path: Path, monkeypatch,
) -> None:
    configured_data_dir = tmp_path / "configured"
    articles_text_dir = configured_data_dir / "articles-text"
    articles_text_dir.mkdir(parents=True)
    (articles_text_dir / "202.txt").write_text(
        "Title: Text-only article\nURL: https://example.com/text-only\n\nBody from the reconciled text store."
    )
    monkeypatch.setenv("PIPELINE_DATA_DIR", str(configured_data_dir))
    parquet = pl.DataFrame(
        {
            "url": ["https://example.com/parquet"],
            "text": ["Body from Parquet."],
        }
    ).lazy()
    monkeypatch.setattr(sentiment_v2, "read_articles", lambda _directory: parquet)

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


def test_analyze_community_budget_skips_ineligible_before_eligible(
    tmp_path: Path, monkeypatch,
) -> None:
    """Ineligible candidates before eligible ones must not produce model calls.

    Verifies that candidate_is_eligible() is checked before the model call,
    so cap-ineligible rows never consume API budget.
    """
    db_path = tmp_path / "pipeline.db"
    monkeypatch.setattr(db, "DB_PATH", db_path)
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        CREATE TABLE urls (
            id INTEGER PRIMARY KEY, url TEXT UNIQUE NOT NULL, hn_id INTEGER,
            hn_score INTEGER, hn_comments INTEGER, hn_title TEXT,
            hn_timestamp INTEGER, scraped_status TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE hn_comments (
            hn_comment_id INTEGER PRIMARY KEY, hn_story_id INTEGER,
            parent_id INTEGER, root_id INTEGER, author TEXT, text TEXT,
            depth INTEGER, root_rank INTEGER, sibling_rank INTEGER,
            ancestry_json TEXT
        )
        """
    )
    conn.commit()
    conn.close()
    init_v2_schema()

    # 5 root comments each with unique root_id: 3 by "capped" (3rd blocked by AUTHOR_CAP=2),
    # 2 by diverse authors. Unique root_ids avoid branch_cap interference.
    comments = [
        (1, 100, 0, 1, "capped", "First", 0, 1, 1, "[1]"),
        (2, 100, 0, 2, "capped", "Second", 0, 2, 1, "[2]"),
        (3, 100, 0, 3, "capped", "Third - blocked by author cap", 0, 3, 1, "[3]"),
        (4, 100, 0, 4, "diverse1", "Pro AI", 0, 4, 1, "[4]"),
        (5, 100, 0, 5, "diverse2", "Mixed", 0, 5, 1, "[5]"),
    ]
    conn = sqlite3.connect(db_path)
    for c in comments:
        conn.execute("INSERT INTO hn_comments VALUES (?,?,?,?,?,?,?,?,?,?)", c)
    conn.commit()
    conn.close()

    story = {"hn_id": 100, "hn_title": "Test", "hn_score": 10}
    rows = hn_comments_v2.build_candidate_stream(100, [
        dict(zip(
            ["id", "hn_story_id", "parent_id", "root_id", "author", "text",
             "depth", "root_rank", "sibling_rank", "ancestry_ids"],
            c,
        ))
        for c in comments
    ])
    replace_selection(100, hn_comments_v2.SELECTION_VERSION, rows, "now")
    conn = sqlite3.connect(db_path)
    conn.commit()
    conn.close()

    called_ids: list[int] = []

    async def fake_call_model(*_args: object, **_kwargs: object):
        user_prompt = str(_args[2]) if len(_args) > 2 else ""
        lines = user_prompt.strip().split("\n")
        comment_id = json.loads(lines[-1]).get("comment_id", 0)
        called_ids.append(comment_id)
        return (
            {
                "contract_version": "comment-v2.0.0",
                "comment_id": comment_id,
                "ai_dimensions": {
                    dim: {"applicability": "explicit", "score": 1, "confidence": 0.8, "stance_basis": "direct", "rationale": "r"}
                    for dim in sentiment_v2.DIMENSIONS
                },
                "article_relation": {"relation": "supports", "targets": [], "confidence": 0.5, "rationale": "r"},
                "parent_relation": {"relation": "not_applicable", "confidence": 0, "rationale": "r"},
                "summary": "test",
            },
            {"input_tokens": 10, "output_tokens": 10, "inference_time_ms": 1.0},
        )

    monkeypatch.setattr(sentiment_v2, "call_model", fake_call_model)

    # Convert SelectedComment instances back to the row-dict shape that as_selected() expects.
    raw_rows = []
    for r in rows:
        raw_rows.append({
            "hn_comment_id": r.hn_comment_id,
            "parent_id": r.parent_id,
            "root_id": r.root_id,
            "author": r.author,
            "text": r.text,
            "depth": r.depth,
            "root_rank": r.root_rank,
            "sibling_rank": r.sibling_rank,
            "ancestry_json": json.dumps(list(r.ancestry_ids)),
            "candidate_rank": r.candidate_rank,
            "selection_pass": r.selection_pass,
            "selection_reason": r.selection_reason,
            "selection_weight": r.raw_visibility_weight,
        })

    result = asyncio.run(
        sentiment_v2.analyze_community(
            "fake_client", story, raw_rows, None, None,
        )
    )
    assert result is not None
    # Comment 3 (3rd by "capped") is blocked by AUTHOR_CAP=2 — never receives a model call.
    assert 3 not in called_ids
    # Comments 1, 2, 4, 5 are eligible and do receive model calls.
    assert 1 in called_ids and 2 in called_ids
    assert 4 in called_ids and 5 in called_ids
