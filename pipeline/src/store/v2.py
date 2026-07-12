"""SQLite persistence for the additive v2 sentiment pipeline."""

from __future__ import annotations

import json
import sqlite3
from typing import Any, Iterable

from .db import get_db_connection
from ..v2_models import SelectedComment


def init_v2_schema() -> None:
    """Create v2-only tables without changing the v1 urls contract."""
    conn = get_db_connection()
    try:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS hn_comments (
                hn_comment_id INTEGER PRIMARY KEY,
                hn_story_id INTEGER NOT NULL,
                parent_id INTEGER NOT NULL,
                root_id INTEGER NOT NULL,
                author TEXT NOT NULL,
                text TEXT NOT NULL,
                depth INTEGER NOT NULL,
                display_order INTEGER NOT NULL DEFAULT 0,
                root_rank INTEGER,
                sibling_rank INTEGER,
                ancestry_json TEXT,
                created_at INTEGER,
                fetched_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_hn_comments_story ON hn_comments(hn_story_id);

            CREATE TABLE IF NOT EXISTS v2_comment_selections (
                hn_story_id INTEGER NOT NULL,
                hn_comment_id INTEGER NOT NULL,
                selection_version TEXT NOT NULL,
                selection_rank INTEGER NOT NULL,
                selection_reason TEXT NOT NULL,
                selection_weight REAL NOT NULL,
                candidate_rank INTEGER,
                selection_pass TEXT,
                refill_status TEXT NOT NULL DEFAULT 'pending',
                selected_at TEXT NOT NULL,
                PRIMARY KEY (hn_story_id, hn_comment_id, selection_version),
                FOREIGN KEY (hn_comment_id) REFERENCES hn_comments(hn_comment_id)
            );

            CREATE TABLE IF NOT EXISTS v2_analysis_runs (
                hn_story_id INTEGER NOT NULL,
                source TEXT NOT NULL,
                analysis_version TEXT NOT NULL,
                selection_version TEXT NOT NULL DEFAULT '',
                contract_version TEXT NOT NULL,
                prompt_version TEXT NOT NULL,
                prompt_hash TEXT NOT NULL,
                input_hash TEXT NOT NULL,
                input_snapshot_json TEXT NOT NULL,
                parser_version TEXT NOT NULL,
                model TEXT NOT NULL,
                parameters_json TEXT NOT NULL,
                status TEXT NOT NULL,
                reason_code TEXT,
                reason TEXT,
                result_json TEXT NOT NULL,
                metrics_json TEXT,
                analyzed_at TEXT NOT NULL,
                PRIMARY KEY (hn_story_id, source, analysis_version, selection_version)
            );

            CREATE TABLE IF NOT EXISTS v2_dimension_analyses (
                hn_story_id INTEGER NOT NULL,
                source TEXT NOT NULL,
                analysis_version TEXT NOT NULL,
                selection_version TEXT NOT NULL DEFAULT '',
                dimension TEXT NOT NULL,
                applicability TEXT NOT NULL,
                score REAL,
                confidence REAL NOT NULL,
                disagreement REAL,
                evidence_count INTEGER NOT NULL,
                diagnostics_json TEXT,
                PRIMARY KEY (
                    hn_story_id, source, analysis_version, selection_version, dimension
                )
            );

            CREATE TABLE IF NOT EXISTS v2_comment_analyses_normalized (
                hn_story_id INTEGER NOT NULL,
                hn_comment_id INTEGER NOT NULL,
                analysis_version TEXT NOT NULL,
                selection_version TEXT NOT NULL,
                status TEXT NOT NULL,
                result_json TEXT NOT NULL,
                analyzed_at TEXT NOT NULL,
                PRIMARY KEY (
                    hn_story_id, hn_comment_id, analysis_version, selection_version
                )
            );

            """
        )
        selection_columns = {
            row[1] for row in conn.execute("PRAGMA table_info(v2_comment_selections)")
        }
        for name, definition in (
            ("candidate_rank", "INTEGER"),
            ("selection_pass", "TEXT"),
            ("refill_status", "TEXT NOT NULL DEFAULT 'pending'"),
        ):
            if name not in selection_columns:
                conn.execute(f"ALTER TABLE v2_comment_selections ADD COLUMN {name} {definition}")
        comment_columns = {row[1] for row in conn.execute("PRAGMA table_info(hn_comments)")}
        for name, definition in (
            ("root_rank", "INTEGER"),
            ("sibling_rank", "INTEGER"),
            ("ancestry_json", "TEXT"),
        ):
            if name not in comment_columns:
                conn.execute(f"ALTER TABLE hn_comments ADD COLUMN {name} {definition}")
        dimension_columns = {
            row[1] for row in conn.execute("PRAGMA table_info(v2_dimension_analyses)")
        }
        if "diagnostics_json" not in dimension_columns:
            conn.execute("ALTER TABLE v2_dimension_analyses ADD COLUMN diagnostics_json TEXT")
        run_columns = {row[1] for row in conn.execute("PRAGMA table_info(v2_analysis_runs)")}
        if "input_snapshot_json" not in run_columns:
            conn.execute(
                "ALTER TABLE v2_analysis_runs ADD COLUMN input_snapshot_json TEXT NOT NULL DEFAULT '{}'"
            )
        conn.commit()
    finally:
        conn.close()


def replace_story_comments(
    story_id: int,
    comments: Iterable[dict[str, Any]],
    fetched_at: str,
) -> None:
    conn = get_db_connection()
    try:
        with conn:
            conn.executemany(
                """
                INSERT INTO hn_comments (
                    hn_comment_id, hn_story_id, parent_id, root_id, author, text,
                    depth, display_order, root_rank, sibling_rank, ancestry_json,
                    created_at, fetched_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(hn_comment_id) DO UPDATE SET
                    hn_story_id = excluded.hn_story_id,
                    parent_id = excluded.parent_id,
                    root_id = excluded.root_id,
                    author = excluded.author,
                    text = excluded.text,
                    depth = excluded.depth,
                    display_order = excluded.display_order,
                    root_rank = excluded.root_rank,
                    sibling_rank = excluded.sibling_rank,
                    ancestry_json = excluded.ancestry_json,
                    created_at = excluded.created_at,
                    fetched_at = excluded.fetched_at
                """,
                [
                    (
                        item["id"], story_id, item["parent_id"], item["root_id"],
                        item["author"], item["text"], item["depth"], item.get("display_order", 0),
                        item["root_rank"], item["sibling_rank"],
                        json.dumps(item["ancestry_ids"]), item.get("created_at"), fetched_at,
                    )
                    for item in comments
                ],
            )
    finally:
        conn.close()


def replace_selection(story_id: int, version: str, comments: list[SelectedComment], selected_at: str) -> None:
    conn = get_db_connection()
    try:
        with conn:
            conn.execute(
                "DELETE FROM v2_comment_selections WHERE hn_story_id = ? AND selection_version = ?",
                (story_id, version),
            )
            conn.executemany(
                """
                INSERT INTO v2_comment_selections (
                    hn_story_id, hn_comment_id, selection_version, selection_rank,
                    selection_reason, selection_weight, candidate_rank, selection_pass,
                    refill_status, selected_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        story_id, item.hn_comment_id, version, item.candidate_rank,
                        item.selection_reason, item.raw_visibility_weight, item.candidate_rank,
                        item.selection_pass, "pending", selected_at,
                    )
                    for item in comments
                ],
            )
    finally:
        conn.close()


def save_normalized_analysis(
    run: dict[str, Any], dimensions: dict[str, dict[str, Any]],
    comment_results: list[dict[str, Any]] | None = None,
) -> None:
    """Atomically persist one versioned source run and its normalized dimensions."""
    conn = get_db_connection()
    try:
        with conn:
            run_columns = list(run)
            run_placeholders = ", ".join("?" for _ in run_columns)
            run_updates = ", ".join(
                f"{column} = excluded.{column}" for column in run_columns[4:]
            )
            conn.execute(
                f"INSERT INTO v2_analysis_runs ({', '.join(run_columns)}) "
                f"VALUES ({run_placeholders}) ON CONFLICT("
                "hn_story_id, source, analysis_version, selection_version"
                f") DO UPDATE SET {run_updates}",
                [
                    json.dumps(value) if isinstance(value, (dict, list)) else value
                    for value in run.values()
                ],
            )
            key = (
                run["hn_story_id"], run["source"], run["analysis_version"],
                run["selection_version"],
            )
            conn.execute(
                "DELETE FROM v2_dimension_analyses WHERE hn_story_id = ? AND source = ? "
                "AND analysis_version = ? AND selection_version = ?",
                key,
            )
            conn.executemany(
                """
                INSERT INTO v2_dimension_analyses (
                    hn_story_id, source, analysis_version, selection_version, dimension,
                    applicability, score, confidence, disagreement, evidence_count
                    , diagnostics_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        *key, name, value["applicability"], value["score"],
                        value["confidence"], value.get("disagreement"),
                        len(value.get("evidence_ids", [])),
                        json.dumps(value, ensure_ascii=False),
                    )
                    for name, value in dimensions.items()
                ],
            )
            if comment_results is not None:
                conn.execute(
                    "DELETE FROM v2_comment_analyses_normalized WHERE hn_story_id = ? "
                    "AND analysis_version = ? AND selection_version = ?",
                    (run["hn_story_id"], run["analysis_version"], run["selection_version"]),
                )
                conn.executemany(
                    """
                    INSERT INTO v2_comment_analyses_normalized (
                        hn_story_id, hn_comment_id, analysis_version, selection_version,
                        status, result_json, analyzed_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    [
                        (
                            run["hn_story_id"], item["comment_id"], run["analysis_version"],
                            run["selection_version"],
                            "rejected" if item.get("reject") else "accepted",
                            json.dumps(item, ensure_ascii=False), run["analyzed_at"],
                        )
                        for item in comment_results
                    ],
                )
    finally:
        conn.close()


def connect_rows() -> sqlite3.Connection:
    """Return a row-enabled connection for v2 query modules."""
    conn = get_db_connection()
    conn.row_factory = sqlite3.Row
    return conn


def update_candidate_outcomes(
    story_id: int, selection_version: str, outcomes: dict[int, str],
) -> None:
    """Persist every considered candidate's accepted or refill outcome."""
    conn = connect_rows()
    try:
        with conn:
            conn.executemany(
                """
                UPDATE v2_comment_selections SET refill_status = ?
                WHERE hn_story_id = ? AND selection_version = ? AND hn_comment_id = ?
                """,
                [
                    (status, story_id, selection_version, comment_id)
                    for comment_id, status in outcomes.items()
                ],
            )
    finally:
        conn.close()
