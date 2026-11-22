import json
import time
from contextlib import closing

from pipeline.src import export
from pipeline.src.store import db


def test_export_counts_each_eligible_hn_story_once(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "pipeline.db")
    db.init_db()
    db.migrate_database()
    now = int(time.time())
    rows = [
        ("canonical", 123, now, "success", -2.0),
        ("older-alias", 123, now - 86400, "success", 1.5),
        ("newer-ineligible", 123, now, "failed", 1.5),
        ("same-date-alias", 123, now, "success", -0.5),
        ("another-story", 456, now, "success", 1.5),
        ("unresolved", None, now, "success", 1.5),
    ]
    with closing(db.get_db_connection()) as conn, conn:
        conn.execute("ALTER TABLE urls ADD COLUMN content_category TEXT")
        conn.execute("ALTER TABLE urls ADD COLUMN content_filter_json TEXT")
        conn.executemany(
            """
            INSERT INTO urls (url, hn_id, hn_score, hn_comments, hn_timestamp, scraped_status,
                              sentiment_score, content_category, classification_json)
            VALUES (?, ?, 38, 10, ?, ?, ?, 'AI_DISCOURSE', ?)
            """,
            [
                (f"https://example.com/{slug}", hn_id, stamp, status, score,
                 json.dumps({"topic": "workflow", "summary": slug}))
                for slug, hn_id, stamp, status, score in rows
            ]
        )

    output = tmp_path / "export"
    export.export_data(output)

    articles = json.loads((output / "articles.json").read_text(encoding="utf-8"))
    assert [article["hn_id"] for article in articles] == [456, 123]
    assert articles[1]["summary"] == "canonical"
    assert articles[1]["sentiment_score"] == -2.0
    verdict = json.loads((output / "verdict.json").read_text(encoding="utf-8"))
    assert verdict["current"]["totalArticles"] == 2
    assert verdict["permanent"]["totalArticles"] == 2
    metrics = json.loads((output / "llm-metrics.json").read_text(encoding="utf-8"))
    assert metrics["123"]["sentiment"]["response"]["summary"] == "canonical"
    with closing(db.get_db_connection()) as conn:
        assert conn.execute("SELECT COUNT(*) FROM urls").fetchone()[0] == len(rows)
