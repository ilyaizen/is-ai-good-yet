"""
Initial E2E Pipeline - Full Database Scrape with High Concurrency.

This module provides a complete end-to-end pipeline for scraping all articles
from scratch with aggressive concurrency settings:

1. Backfill Histre (all pages)
2. Resolve HN Links
3. Scrape Content (HIGH CONCURRENCY - 100-200 tabs)
4. Clean Article Text
5. Content Prefilter
6. Sentiment Analysis
7. Export to Frontend

Key Features:
- High concurrency: 100-200 concurrent browser tabs
- Smart headful fallback: Start headless -> Headless Retry -> Headful Retry
- Three-pass scraping: Fast headless pass, targeted headless retry, then headful retry
"""

import sys
import io
import subprocess
import signal
import argparse
import time
from dataclasses import dataclass, field
from typing import Optional
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

# Force UTF-8 encoding for standard output (handles piping issues on Windows)
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

# Setup Rich Console
console = Console()

# Get Python interpreter path
PYTHON_CMD = sys.executable

# Pipeline directory
PIPELINE_DIR = Path(__file__).resolve().parent.parent


@dataclass
class PhaseResult:
    """Result from a single phase execution."""

    name: str
    phase_id: str
    success: bool
    duration_seconds: float
    return_code: int = 0
    skipped: bool = False
    skip_reason: str = ""


@dataclass
class PhaseConfig:
    """Configuration for a pipeline phase."""

    name: str
    phase_id: str
    module: str
    args: list[str] = field(default_factory=list)
    is_script: bool = False  # True if running as script, False for -m module


class InitialE2EPipeline:
    """Full database scrape with high concurrency.
    
    This pipeline is designed for initial setup or recovery after data loss.
    It scrapes everything from scratch with aggressive concurrency settings.
    
    Key differences from Catch-Up Pipeline:
    - Scrapes ALL Histre pages (not just recent)
    - Uses high concurrency (100-200 tabs vs 10-16)
    - Three-pass scraping: headless -> headless retry -> headful retry
    - No resume functionality (fresh start each time)
    """

    def __init__(
        self,
        concurrency: int = 100,
        batch_size: int = 500,
        headful_fallback: bool = True,
        headful_concurrency: int = 10,
        pages: int = 100,
        verbose: bool = False,
        dry_run: bool = False,
        use_proxy: bool = False,
    ):
        self.concurrency = concurrency
        self.batch_size = batch_size
        self.headful_fallback = headful_fallback
        self.headful_concurrency = headful_concurrency
        self.pages = pages
        self.verbose = verbose
        self.dry_run = dry_run
        self.use_proxy = use_proxy
        self.results: list[PhaseResult] = []
        self.shutdown_requested = False
        self._original_sigint = None
        self._current_process: Optional[subprocess.Popen] = None

    def setup_signals(self):
        """Setup Ctrl+C handling for graceful abort."""
        self._original_sigint = signal.getsignal(signal.SIGINT)
        signal.signal(signal.SIGINT, self._handle_sigint)
        if sys.platform != "win32":
            signal.signal(signal.SIGTERM, self._handle_sigint)

    def restore_signals(self):
        """Restore original signal handlers."""
        if self._original_sigint:
            signal.signal(signal.SIGINT, self._original_sigint)

    def _handle_sigint(self, signum, frame):
        """Handle Ctrl+C gracefully."""
        if not self.shutdown_requested:
            self.shutdown_requested = True
            console.print(
                "\n[yellow]Shutdown requested. Finishing current phase...[/yellow]"
            )
            # Kill current subprocess if running
            if self._current_process and self._current_process.poll() is None:
                if sys.platform == "win32":
                    subprocess.run(
                        [
                            "taskkill",
                            "/pid",
                            str(self._current_process.pid),
                            "/t",
                            "/f",
                        ],
                        capture_output=True,
                        shell=True,
                    )
                else:
                    self._current_process.terminate()

    def get_phases(self) -> list[PhaseConfig]:
        """Build list of phases to run based on configuration."""
        phases = []

        # Phase 1: Backfill Histre (ALL pages)
        phases.append(
            PhaseConfig(
                name="Backfill Histre",
                phase_id="1",
                module="src.backfill_histre",
                args=["--end", str(self.pages)],
            )
        )

        # Phase 2: Resolve HN Links
        resolve_args = []
        if self.verbose:
            resolve_args.append("-v")
        phases.append(
            PhaseConfig(
                name="Resolve HN Links",
                phase_id="2",
                module="src.hn_resolver",
                args=resolve_args,
            )
        )

        # Phase 3: Scrape Content - HIGH CONCURRENCY (headless first pass)
        scrape_args = [
            "--lean",
            "--stealth-mode=seleniumbase",
            "-b", str(self.batch_size),
            "-c", str(self.concurrency),
            "-r", "0",  # No rate limit
            "--max-retries", "1",
        ]
        if self.verbose:
            scrape_args.insert(0, "-v")
        if self.use_proxy:
            scrape_args.append("--use-proxy")
        # Note: We intentionally run headless first for speed
        phases.append(
            PhaseConfig(
                name="Scrape Content (Headless - High Concurrency)",
                phase_id="3a",
                module="src.scraper",
                args=scrape_args,
            )
        )

        # Phase 3b: Retry Failed (Headless) - Reduce concurrency slightly for stability
        retry_headless_args = [
            "--lean",
            "--stealth-mode=seleniumbase",
            "--retry-failed",
            "-b", str(self.batch_size),
            "-c", str(max(10, self.concurrency // 2)),  # Half concurrency for retry
            "-r", "0",
            "--max-retries", "2",
        ]
        if self.verbose:
            retry_headless_args.insert(0, "-v")
        if self.use_proxy:
            retry_headless_args.append("--use-proxy")
        phases.append(
            PhaseConfig(
                name="Retry Failed (Headless)",
                phase_id="3b",
                module="src.scraper",
                args=retry_headless_args,
            )
        )

        # Phase 3c: Retry Failed (Headful) (if enabled)
        if self.headful_fallback:
            retry_args = [
                "--lean",
                "--stealth-mode=seleniumbase",
                "--retry-failed",
                "--headful",
                "--use-selenium",
                "-b", "100",
                "-c", str(self.headful_concurrency),
                "-r", "0",
                "--max-retries", "2",
            ]
            if self.verbose:
                retry_args.insert(0, "-v")
            if self.use_proxy:
                retry_args.append("--use-proxy")
            phases.append(
                PhaseConfig(
                    name="Retry Failed (Headful)",
                    phase_id="3c",
                    module="src.scraper",
                    args=retry_args,
                )
            )

        # Phase 3.5a: Clean Article Text
        phases.append(
            PhaseConfig(
                name="Clean Article Text",
                phase_id="3.5a",
                module="src/clean_articles.py",
                args=["--no-backup", "--clean-all"],
                is_script=True,
            )
        )

        # Phase 4: Content Prefilter
        prefilter_args = []
        if self.verbose:
            prefilter_args.append("-v")
        phases.append(
            PhaseConfig(
                name="Content Prefilter",
                phase_id="4",
                module="src.prefilter_content",
                args=prefilter_args,
            )
        )

        # Phase 5: Sentiment Analysis
        sentiment_args = []
        if self.verbose:
            sentiment_args.append("-v")
        phases.append(
            PhaseConfig(
                name="Sentiment Analysis",
                phase_id="5",
                module="src.sentiment_analyzer",
                args=sentiment_args,
            )
        )

        # Phase 6: Export to Frontend
        export_args = []
        if self.verbose:
            export_args.append("-v")
        phases.append(
            PhaseConfig(
                name="Export to Frontend",
                phase_id="6",
                module="src.export",
                args=export_args,
            )
        )

        return phases

    def run_phase(self, phase: PhaseConfig) -> PhaseResult:
        """Execute a phase via subprocess."""
        if self.shutdown_requested:
            return PhaseResult(
                name=phase.name,
                phase_id=phase.phase_id,
                success=False,
                duration_seconds=0,
                skipped=True,
                skip_reason="User abort",
            )

        # Build command
        if phase.is_script:
            cmd = [PYTHON_CMD, phase.module] + phase.args
        else:
            cmd = [PYTHON_CMD, "-m", phase.module] + phase.args

        console.print(f"\n[bold cyan]{'=' * 60}[/bold cyan]")
        console.print(f"[bold]Phase {phase.phase_id}: {phase.name}[/bold]")
        console.print(f"[dim]> {' '.join(cmd)}[/dim]")
        console.print(f"[bold cyan]{'=' * 60}[/bold cyan]\n")

        if self.dry_run:
            return PhaseResult(
                name=phase.name,
                phase_id=phase.phase_id,
                success=True,
                duration_seconds=0,
                skipped=True,
                skip_reason="Dry run",
            )

        start_time = time.time()

        try:
            # Run subprocess with real-time output
            self._current_process = subprocess.Popen(
                cmd,
                cwd=str(PIPELINE_DIR),
                env={
                    **dict(__import__("os").environ),
                    "PYTHONIOENCODING": "utf-8",
                    "PYTHONUTF8": "1",
                },
                shell=False,
            )

            return_code = self._current_process.wait()
            duration = time.time() - start_time
            self._current_process = None

            success = return_code == 0
            return PhaseResult(
                name=phase.name,
                phase_id=phase.phase_id,
                success=success,
                duration_seconds=duration,
                return_code=return_code,
            )

        except Exception as e:
            duration = time.time() - start_time
            console.print(f"[red]Error running phase: {e}[/red]")
            return PhaseResult(
                name=phase.name,
                phase_id=phase.phase_id,
                success=False,
                duration_seconds=duration,
                return_code=-1,
            )

    def display_phase_summary(self, result: PhaseResult):
        """Display summary after a phase completes with brief pause."""
        if result.skipped:
            console.print(
                Panel(
                    f"[dim]Skipped: {result.skip_reason}[/dim]",
                    title=f"Phase {result.phase_id}: {result.name}",
                    border_style="dim",
                )
            )
            return

        if result.success:
            color = "green"
            icon = "[bold green]OK[/bold green]"
        else:
            color = "red"
            icon = f"[bold red]FAILED (exit {result.return_code})[/bold red]"

        summary = f"""
{icon}
Duration: {result.duration_seconds:.1f}s
"""

        console.print(
            Panel(
                summary.strip(),
                title=f"Phase {result.phase_id}: {result.name}",
                border_style=color,
            )
        )

        # Brief pause for user to see results (unless shutting down)
        if not self.shutdown_requested and not self.dry_run:
            time.sleep(2)

    def display_final_summary(self):
        """Display final summary of all phases."""
        console.print("\n")
        console.print(
            Panel(
                "[bold]Initial E2E Pipeline Complete[/bold]",
                border_style="blue",
            )
        )

        # Build results table
        table = Table(title="Phase Results", show_header=True)
        table.add_column("Phase", style="cyan")
        table.add_column("Name", style="white")
        table.add_column("Status", justify="center")
        table.add_column("Duration", justify="right")

        for result in self.results:
            if result.skipped:
                status = f"[dim]SKIPPED ({result.skip_reason})[/dim]"
                duration = "-"
            elif result.success:
                status = "[green]OK[/green]"
                duration = f"{result.duration_seconds:.1f}s"
            else:
                status = f"[red]FAILED ({result.return_code})[/red]"
                duration = f"{result.duration_seconds:.1f}s"

            table.add_row(result.phase_id, result.name, status, duration)

        console.print(table)

        # Summary stats
        total = len(self.results)
        succeeded = sum(1 for r in self.results if r.success and not r.skipped)
        failed = sum(1 for r in self.results if not r.success and not r.skipped)
        skipped = sum(1 for r in self.results if r.skipped)
        total_time = sum(r.duration_seconds for r in self.results)

        console.print(f"\n[bold]Summary:[/bold]")
        console.print(f"  Total Phases: {total}")
        console.print(f"  [green]Succeeded:[/green] {succeeded}")
        console.print(f"  [red]Failed:[/red] {failed}")
        console.print(f"  [dim]Skipped:[/dim] {skipped}")
        console.print(f"  Total Time: {total_time:.1f}s ({total_time/60:.1f}m)")

        if failed > 0:
            console.print(
                "\n[yellow]Some phases failed. Check the output above for details.[/yellow]"
            )

    def run(self) -> int:
        """Execute the full Initial E2E pipeline. Returns exit code."""
        self.setup_signals()

        try:
            # Header
            console.print(
                Panel(
                    f"[bold]Initial E2E Pipeline - Full Database Scrape[/bold]\n"
                    f"Pages: {self.pages} | "
                    f"Concurrency: {self.concurrency} | "
                    f"Batch Size: {self.batch_size} | "
                    f"Headful Fallback: {self.headful_fallback} | "
                    f"Proxy: {self.use_proxy} | "
                    f"Dry Run: {self.dry_run}",
                    title="Full Pipeline",
                    border_style="magenta",
                )
            )

            phases = self.get_phases()

            if self.dry_run:
                console.print(
                    "\n[yellow]DRY RUN MODE - No phases will be executed[/yellow]\n"
                )
                for phase in phases:
                    if phase.is_script:
                        cmd = f"{PYTHON_CMD} {phase.module} {' '.join(phase.args)}"
                    else:
                        cmd = f"{PYTHON_CMD} -m {phase.module} {' '.join(phase.args)}"
                    console.print(f"  Phase {phase.phase_id}: {phase.name}")
                    console.print(f"    [dim]{cmd}[/dim]")
                return 0

            # Execute phases
            for phase in phases:
                if self.shutdown_requested:
                    result = PhaseResult(
                        name=phase.name,
                        phase_id=phase.phase_id,
                        success=False,
                        duration_seconds=0,
                        skipped=True,
                        skip_reason="User abort",
                    )
                else:
                    result = self.run_phase(phase)

                self.results.append(result)
                self.display_phase_summary(result)

                if self.shutdown_requested:
                    break

            # Final summary
            self.display_final_summary()

            # Return exit code based on results
            any_failed = any(not r.success and not r.skipped for r in self.results)
            return 1 if any_failed else 0

        finally:
            self.restore_signals()


def main():
    """Main entry point for the Initial E2E pipeline."""
    parser = argparse.ArgumentParser(
        description="Initial E2E pipeline: Full database scrape with high concurrency.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m src.initial_e2e -v                     # Balanced (100 tabs)
  python -m src.initial_e2e -v -c 200              # Aggressive (200 tabs)
  python -m src.initial_e2e -v -c 50               # Conservative (50 tabs)
  python -m src.initial_e2e --dry-run              # Show what would run
  python -m src.initial_e2e -v --use-proxy         # With proxy rotation
  python -m src.initial_e2e -v --no-headful        # Skip headful retry pass
""",
    )
    parser.add_argument(
        "--pages",
        "-p",
        type=int,
        default=400,
        help="Number of Histre pages to backfill (default: 400 = all)",
    )
    parser.add_argument(
        "--concurrency",
        "-c",
        type=int,
        default=100,
        help="Number of concurrent browser tabs (default: 100)",
    )
    parser.add_argument(
        "--batch-size",
        "-b",
        type=int,
        default=500,
        help="Batch size for URL processing (default: 500)",
    )
    parser.add_argument(
        "--headful-concurrency",
        type=int,
        default=10,
        help="Concurrency for headful retry pass (default: 10)",
    )
    parser.add_argument(
        "--no-headful",
        action="store_true",
        help="Skip headful retry pass for failed URLs",
    )
    parser.add_argument(
        "--use-proxy",
        action="store_true",
        help="Use proxy rotation (requires PROXY_* env vars)",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose output for sub-phases",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without executing",
    )

    args = parser.parse_args()

    pipeline = InitialE2EPipeline(
        pages=args.pages,
        concurrency=args.concurrency,
        batch_size=args.batch_size,
        headful_fallback=not args.no_headful,
        headful_concurrency=args.headful_concurrency,
        use_proxy=args.use_proxy,
        verbose=args.verbose,
        dry_run=args.dry_run,
    )

    exit_code = pipeline.run()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
