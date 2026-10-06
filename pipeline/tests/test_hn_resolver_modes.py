"""URL selection modes for src/hn_resolver.py.

Regression coverage for the 2026-10-06 ingestion-gap fix: catch-up always
passes --update-recent, and the previous elif chain made that mode REPLACE
default new-URL ingestion (731 new Histre links stranded on one run). The
contract under test: --update-recent is additive — new URLs always process,
recent-resolved URLs additionally refresh.
"""
import sys
import unittest
from pathlib import Path
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from src import hn_resolver  # noqa: E402


def _sel(all_urls, **kwargs):
    return hn_resolver.select_urls_to_process(all_urls, **kwargs)


class DefaultModeTests(unittest.TestCase):
    def test_processes_only_new_urls(self):
        with mock.patch.object(hn_resolver, "get_existing_urls", return_value={"old.com"}):
            to_process, summary = _sel(["old.com", "new.com"])
        self.assertEqual(to_process, ["new.com"])
        self.assertIn("To process: 1", summary)

    def test_empty_feed_processes_nothing(self):
        with mock.patch.object(hn_resolver, "get_existing_urls", return_value=set()):
            to_process, _ = _sel([])
        self.assertEqual(to_process, [])


class UpdateRecentModeTests(unittest.TestCase):
    def test_update_recent_is_additive(self):
        """New URLs must ingest AND recent-resolved URLs refresh — the regression."""
        feed = ["brand-new.com", "recent.com", "ancient.com"]
        with mock.patch.object(hn_resolver, "get_existing_urls", return_value={"recent.com", "ancient.com"}), \
             mock.patch.object(hn_resolver, "get_recent_resolved_urls", return_value={"recent.com"}):
            to_process, summary = _sel(feed, update_recent=True)
        self.assertIn("brand-new.com", to_process)
        self.assertIn("recent.com", to_process)
        self.assertNotIn("ancient.com", to_process)

    def test_update_recent_ignores_legacy_no_match(self):
        """A stale no_match row outside the recency window stays out of scope."""
        feed = ["new.com", "stale-no-match.com"]
        with mock.patch.object(hn_resolver, "get_existing_urls", return_value={"stale-no-match.com"}), \
             mock.patch.object(hn_resolver, "get_recent_resolved_urls", return_value=set()):
            to_process, _ = _sel(feed, update_recent=True)
        self.assertEqual(to_process, ["new.com"])

    def test_new_urls_cannot_double_process(self):
        """New URLs are not in the DB, so they can never also be refresh targets."""
        feed = ["new.com"]
        with mock.patch.object(hn_resolver, "get_existing_urls", return_value=set()), \
             mock.patch.object(hn_resolver, "get_recent_resolved_urls", return_value={"new.com"}):
            to_process, _ = _sel(feed, update_recent=True)
        self.assertEqual(to_process.count("new.com"), 1)

    def test_recent_days_forwarded(self):
        captured = {}
        def fake_recent(days):
            captured["days"] = days
            return set()
        with mock.patch.object(hn_resolver, "get_existing_urls", return_value=set()), \
             mock.patch.object(hn_resolver, "get_recent_resolved_urls", side_effect=fake_recent):
            _sel(["a.com"], update_recent=True, recent_days=7)
        self.assertEqual(captured["days"], 7)


class ModePrecedenceTests(unittest.TestCase):
    def test_force_wins_over_update_recent(self):
        with mock.patch.object(hn_resolver, "get_existing_urls", return_value={"x.com"}):
            to_process, summary = _sel(["x.com"], force=True, update_recent=True)
        self.assertEqual(to_process, ["x.com"])
        self.assertIn("Force", summary)

    def test_retry_failed_includes_failed_and_new(self):
        feed = ["failed.com", "new.com", "happy.com"]
        with mock.patch.object(hn_resolver, "get_failed_urls", return_value={"failed.com"}), \
             mock.patch.object(hn_resolver, "get_existing_urls", return_value={"failed.com", "happy.com"}):
            to_process, summary = _sel(feed, retry_failed=True)
        self.assertEqual(sorted(to_process), ["failed.com", "new.com"])
        self.assertIn("Retry", summary)

    def test_fix_missing_selects_intersection(self):
        feed = ["a.com", "b.com"]
        with mock.patch.object(hn_resolver, "get_urls_missing_author", return_value={"b.com", "not-in-feed.com"}):
            to_process, summary = _sel(feed, fix_missing=True)
        self.assertEqual(to_process, ["b.com"])
        self.assertIn("Fix Missing", summary)


if __name__ == "__main__":
    unittest.main()
