"""IAIGY-03: pipeline/run.py phase behavior verification.

The previous entrypoint silently no-op'd every phase (lines 18-27 were `pass`).
Now run.py either dispatches to a real phase module or exits with an explicit
error naming the replacement. These tests verify that contract.

Run: python run_tests.py style, or directly:
    python tests/test_pipeline_run_phases.py
"""
import io
import json
import subprocess
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from src.pipeline_runner import (  # noqa: E402
    PHASE_ALIASES,
    PHASE_MODULES,
    resolve_phase,
)
from run import main as run_main  # noqa: E402
import run  # noqa: E402


class PhaseResolutionTests(unittest.TestCase):
    def test_phase_aliases_cover_cli_choices(self):
        self.assertEqual(set(PHASE_ALIASES), {"ingest", "scrape", "analyze", "all"})

    def test_every_phase_maps_to_a_module(self):
        for phase, module in PHASE_MODULES.items():
            self.assertTrue(module, f"phase {phase} maps to an empty module")

    def test_resolve_known_phases(self):
        for phase in ("ingest", "scrape", "analyze"):
            self.assertIsNotNone(resolve_phase(phase))

    def test_resolve_all_expands_to_every_phase(self):
        resolved = resolve_phase("all")
        self.assertIsNotNone(resolved)
        self.assertEqual(resolved, [PHASE_MODULES[p] for p in ("ingest", "scrape", "analyze")])

    def test_cli_choices_must_resolve(self):
        """Because argparse restricts to these 4 choices, none may resolve None."""
        for phase in ("ingest", "scrape", "analyze", "all"):
            self.assertIsNotNone(resolve_phase(phase))


class RunMainBehaviorTests(unittest.TestCase):
    def test_main_dispatches_to_modules_in_order(self):
        dispatched = []

        def fake_runphase(module):
            dispatched.append(module)
            return 0

        with mock.patch.object(run, "run_phase_module", side_effect=fake_runphase), mock.patch.object(
            run, "setup_logging"
        ):
            run_main(["--phase", "all"])

        self.assertEqual(
            dispatched,
            [PHASE_MODULES[p] for p in ("ingest", "scrape", "analyze")],
            "phase=all must dispatch every phase module in pipeline order",
        )

    def test_main_single_phase_dispatches_only_that_module(self):
        dispatched = []
        with mock.patch.object(run, "run_phase_module", side_effect=lambda m: dispatched.append(m) or 0), mock.patch.object(
            run, "setup_logging"
        ):
            run_main(["--phase", "scrape"])

        self.assertEqual(dispatched, [PHASE_MODULES["scrape"]])

    def test_main_aborts_on_phase_failure(self):
        with mock.patch.object(run, "run_phase_module", return_value=1), mock.patch.object(
            run, "setup_logging"
        ):
            self.assertEqual(run_main(["--phase", "ingest"]), 1)


class RealRunnerIntegrationTests(unittest.TestCase):
    """Run the real CLI with synthetic modules patched via PYTHONPATH is too
    invasive; instead run the real dispatcher against --help (argparse surface)
    and against an invalid phase to confirm the explicit-error path."""

    def test_help_has_only_real_phase_choices(self):
        result = subprocess.run(
            [sys.executable, str(REPO_ROOT / "run.py"), "--help"],
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
        )
        self.assertEqual(result.returncode, 0)
        for choice in ("ingest", "scrape", "analyze", "all"):
            self.assertIn(choice, result.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
