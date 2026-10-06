"""Scrape-queue selection modes for src/store/db.py::get_urls_to_scrape.

Regression coverage for the 2026-10-06 deep-catch-up fixes:
- --retry-failed used to pull EVERY non-success row (10k+ permanent paywall
  failures) because the Mar–Aug coverage hole could never surface through the
  newest-first pending queue. The contract under test: retry mode is windowable
  (retry_window_days / min_timestamp) and skips terminal failure categories
  (archive_failed, empty_content) unless explicitly included.
"""
import sqlite3
import sys
import tempfile
import time
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from src.store import db as store_db  # noqa: E402


class ScrapeSelectionTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._old_db_path = store_db.DB_PATH
        store_db.DB_PATH = Path(self._tmp.name) / "test.db"
        store_db.init_db()
        store_db.migrate_database()
        self.now = int(time.time())
        self.conn = sqlite3.connect(store_db.DB_PATH)

    def tearDown(self):
        self.conn.close()
        store_db.DB_PATH = self._old_db_path
        self._tmp.cleanup()

    def _insert(self, url, scraped_status=None, hn_id=1, hn_score=100,
                hn_comments=10, hn_timestamp=None, failure_category=None):
        self.conn.execute(
            """
            INSERT INTO urls (url, hn_id, hn_score, hn_comments, hn_timestamp,
                              status, scraped_status, failure_category)
            VALUES (?, ?, ?, ?, ?, 'resolved', ?, ?)
            """,
            (url, hn_id, hn_score, hn_comments,
             self.now if hn_timestamp is None else hn_timestamp,
             scraped_status, failure_category),
        )
        self.conn.commit()

    def _select(self, **kwargs):
        kwargs.setdefault("randomize", False)
        kwargs.setdefault("batch_size", 100)
        return store_db.get_urls_to_scrape(**kwargs)

    def test_default_mode_ignores_failed(self):
        """Without retry_failed, only NULL/pending rows are candidates."""
        self._insert("https://fresh.example/a")
        self._insert("https://failed.example/b", scraped_status="failed",
                     failure_category="blocked", hn_id=2)
        rows = self._select()
        self.assertEqual([r[1] for r in rows], ["https://fresh.example/a"])

    def test_retry_failed_includes_failed(self):
        self._insert("https://fresh.example/a", hn_id=1)
        self._insert("https://failed.example/b", scraped_status="failed",
                     failure_category="blocked", hn_id=2)
        rows = self._select(retry_failed=True)
        self.assertEqual({r[1] for r in rows},
                         {"https://fresh.example/a", "https://failed.example/b"})

    def test_retry_failed_excludes_skipped(self):
        """'skipped' is terminal (irrelevant domain): re-selecting it re-queues
        the item every batch forever — 150 re-skips/30min observed live."""
        self._insert("https://fresh.example/a", hn_id=1)
        self._insert("https://github.com/x/y", scraped_status="skipped",
                     failure_category="skipped", hn_id=2)
        rows = self._select(retry_failed=True)
        self.assertEqual([r[1] for r in rows], ["https://fresh.example/a"])

    def test_window_days_bounds_retries(self):
        """retry_window_days excludes failures older than the window."""
        self._insert("https://old-fail.example/a", scraped_status="failed",
                     failure_category="blocked", hn_id=1,
                     hn_timestamp=self.now - 60 * 86400)
        self._insert("https://recent-fail.example/b", scraped_status="failed",
                     failure_category="blocked", hn_id=2,
                     hn_timestamp=self.now - 2 * 86400)
        rows = self._select(retry_failed=True, window_days=7)
        self.assertEqual([r[1] for r in rows], ["https://recent-fail.example/b"])

    def test_terminal_failure_categories_excluded_by_default(self):
        """archive_failed/empty_content are paywall/bot-wall terminals — not retried."""
        self._insert("https://archive-fail.example/a", scraped_status="failed",
                     failure_category="archive_failed", hn_id=1)
        self._insert("https://paywalled.example/b", scraped_status="failed",
                     failure_category="empty_content", hn_id=2)
        self._insert("https://blocked.example/c", scraped_status="failed",
                     failure_category="blocked", hn_id=3)
        rows = self._select(retry_failed=True)
        self.assertEqual([r[1] for r in rows], ["https://blocked.example/c"])

    def test_include_terminal_failures_opt_in(self):
        self._insert("https://archive-fail.example/a", scraped_status="failed",
                     failure_category="archive_failed", hn_id=1)
        rows = self._select(retry_failed=True, exclude_failure_categories=None)
        self.assertEqual([r[1] for r in rows], ["https://archive-fail.example/a"])

    def test_min_timestamp_applies_in_all_modes(self):
        """min_timestamp bounds the pool regardless of retry mode."""
        self._insert("https://ancient.example/a", hn_id=1,
                     hn_timestamp=self.now - 400 * 86400)
        self._insert("https://recent.example/b", hn_id=2)
        rows = self._select(min_timestamp=self.now - 30 * 86400)
        self.assertEqual([r[1] for r in rows], ["https://recent.example/b"])

    def test_transient_dns_category_not_terminal(self):
        """unsafe_url_transient must survive the default terminal-category filter."""
        self._insert("https://dns-blip.example/a", scraped_status="failed",
                     failure_category="unsafe_url_transient", hn_id=1)
        rows = self._select(retry_failed=True)
        self.assertEqual([r[1] for r in rows], ["https://dns-blip.example/a"])

    def test_score_comment_gate_excludes_below_gate(self):
        """Coverage gates keep below-gate items pending instead of burning scrape hours."""
        self._insert("https://hot.example/a", hn_id=1, hn_score=120, hn_comments=30)
        self._insert("https://lukewarm.example/b", hn_id=2, hn_score=4, hn_comments=1)
        rows = self._select(min_score=5, min_comments=2)
        self.assertEqual([r[1] for r in rows], ["https://hot.example/a"])

    def test_gate_zero_means_unfiltered(self):
        self._insert("https://low.example/a", hn_id=1, hn_score=1, hn_comments=0)
        rows = self._select(min_score=0, min_comments=0)
        self.assertEqual([r[1] for r in rows], ["https://low.example/a"])

    def test_retry_count_cap_excludes_livelocked_items(self):
        """A cert-broken item inside the window (retry_count>=cap) must stop being
        re-selected by every batch — without the cap the drain loop never ends."""
        self._insert("https://livelock.example/a", scraped_status="failed",
                     failure_category="blocked", hn_id=1,
                     hn_timestamp=self.now - 86400)
        self.conn.execute(
            "UPDATE urls SET retry_count = 5 WHERE url = 'https://livelock.example/a'")
        self.conn.commit()
        rows = self._select(retry_failed=True, window_days=30, max_retry_count=3)
        self.assertEqual(rows, [])

    def test_retry_count_cap_keeps_fresh_failures(self):
        self._insert("https://once-failed.example/a", scraped_status="failed",
                     failure_category="blocked", hn_id=1,
                     hn_timestamp=self.now - 86400)
        self.conn.execute(
            "UPDATE urls SET retry_count = 1 WHERE url = 'https://once-failed.example/a'")
        self.conn.commit()
        rows = self._select(retry_failed=True, window_days=30, max_retry_count=3)
        self.assertEqual([r[1] for r in rows], ["https://once-failed.example/a"])


if __name__ == "__main__":
    unittest.main()
