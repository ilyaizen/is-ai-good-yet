"""Phase orchestration for the pipeline entrypoint (pipeline/run.py).

Each CLI phase maps to the real phase module that the interactive CLI and the
catch-up orchestrator already use. run.py no longer silently no-ops: it either
dispatches those modules in pipeline order or refuses to run at all.
"""

from __future__ import annotations

import asyncio
import runpy
import sys
from typing import Callable, List, Optional

# Phase -> real module that implements it (as a -m-able module name, '' = none
# available yet). Keys are the argparse choices of run.py.
PHASE_MODULES: dict[str, str] = {
    "ingest": "src.backfill_histre",
    "scrape": "src.scraper",
    "analyze": "src.prefilter_content",
}

# Display order used when --phase all is requested.
PHASE_ORDER: tuple[str, ...] = ("ingest", "scrape", "analyze")

PHASE_ALIASES: frozenset[str] = frozenset(["ingest", "scrape", "analyze", "all"])


def run_phase_module(module_name: str) -> int:
    """Run a phase module by name once, as `python -m <module>` would."""
    module = __import__(module_name, fromlist=["*"])
    main = getattr(module, "main", None)
    if callable(main):
        result = main()
        return int(result) if isinstance(result, int) else 0

    # No callable `main` — fall back to executing the module's __main__ block
    # semantics via runpy so sys.argv matches `python -m <module>` usage.
    argv_backup = sys.argv
    sys.argv = [module_name]
    try:
        runpy.run_module(module_name, run_name="__main__", alter_sys=True)
        return 0
    finally:
        sys.argv = argv_backup


def resolve_phase(phase: str) -> Optional[List[str]]:
    """Expand a phase into the ordered list of module names to run.

    Returns None if the phase is unknown (defensive only — argparse restricts
    choices upstream).
    """
    if phase == "all":
        return [PHASE_MODULES[p] for p in PHASE_ORDER]
    module = PHASE_MODULES.get(phase)
    if module is None:
        return None
    return [module]
