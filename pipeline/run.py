import argparse
import sys

from src.pipeline_runner import PHASE_MODULES, resolve_phase, run_phase_module
from src.utils import setup_logging


def main(argv=None):
    """
    Entrypoint for the 'Is AI Good Yet?' pipeline.

    Every phase maps to the real phase module already used by the interactive
    CLI and the catch-up orchestrator (`src.catch_up`). If a phase has no
    module yet, run.py refuses to fake it: it exits non-zero with an explicit
    error naming the replacement command instead of a silent no-op.
    """
    parser = argparse.ArgumentParser(description="Run the data processing pipeline.")
    parser.add_argument(
        "--phase",
        choices=["ingest", "scrape", "analyze", "all"],
        default="all",
        help="Pipeline phase to run",
    )
    args = parser.parse_args(argv)

    setup_logging()

    modules = resolve_phase(args.phase)
    if not modules:
        # Explicit error naming the replacement — never a silent pass-through.
        print(
            f"error: phase '{args.phase}' is not implemented in pipeline/run.py.",
            file=sys.stderr,
        )
        print(
            "replacement: use the phase-specific orchestrators instead, e.g. "
            "`python -m src.catch_up` (all phases) or run individual modules: "
            + ", ".join(sorted(PHASE_MODULES.values())),
            file=sys.stderr,
        )
        return 2

    print(f"Starting pipeline phase: {args.phase}")

    replacement = "python -m src.catch_up"

    for module_name in modules:
        print(f"-> dispatching module: {module_name}")
        try:
            code = run_phase_module(module_name)
        except ModuleNotFoundError as exc:
            print(
                f"error: phase module '{module_name}' cannot run in this "
                f"environment ({exc}).\nreplacement: use the CLI/venv path: "
                f"`{replacement}` from pipeline/ (or run "
                f"`python -m {module_name}` inside the pipeline venv).",
                file=sys.stderr,
            )
            return 2
        if code != 0:
            print(
                f"phase module {module_name} exited with code {code}; aborting pipeline.",
                file=sys.stderr,
            )
            return code

    print(f"Pipeline phase '{args.phase}' finished.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nPipeline interrupted by user.")
        sys.exit(0)
