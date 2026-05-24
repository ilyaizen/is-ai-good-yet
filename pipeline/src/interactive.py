import sys
import asyncio
import signal
import threading
import logging
import platform
import time
from rich.console import Console

# Check for Windows
IS_WINDOWS = platform.system() == "Windows"
if IS_WINDOWS:
    import msvcrt

class InteractiveSession:
    """
    Manages interactive session control (Quit, Pause, Resume) via keyboard inputs
    and system signals (SIGINT, SIGTERM).
    """
    def __init__(self, console: Console | None = None):
        self.console = console or Console()
        self.shutdown_requested = False
        self.is_paused = False
        self._running = False
        self._thread = None

        # Get the running loop or create a new one if necessary
        try:
            self._loop = asyncio.get_running_loop()
        except RuntimeError:
            self._loop = asyncio.get_event_loop()

        # Async event for pausing
        self._resume_event = asyncio.Event()
        self._resume_event.set() # Start unpaused

    def start(self):
        """Start the keyboard monitor thread and signal handlers."""
        if self._running:
            return

        self._running = True
        self.setup_signal_handlers()

        if IS_WINDOWS:
            self._thread = threading.Thread(target=self._keyboard_monitor_windows, daemon=True)
            self._thread.start()
            self.console.print(
                "[dim]Interactive controls enabled: [bold]q[/bold] (quit), "
                "[bold]p[/bold] (pause), [bold]r[/bold] (resume)[/dim]"
            )
        else:
            self.console.print("[dim]Interactive controls not fully supported on this OS (Signals only)[/dim]")

    def stop(self):
        self._running = False
        # Thread is daemon, will die naturally or on exit

    def setup_signal_handlers(self):
        """Setup signal handlers for Ctrl+C and termination signals."""
        try:
            # Only add signal handlers if we are in the main thread/loop
            self._loop.add_signal_handler(signal.SIGINT, self.request_shutdown)
            self._loop.add_signal_handler(signal.SIGTERM, self.request_shutdown)
        except (NotImplementedError, RuntimeError):
            # Windows or not main thread
            try:
                signal.signal(signal.SIGINT, lambda s, f: self.request_shutdown())
                signal.signal(signal.SIGTERM, lambda s, f: self.request_shutdown())
            except (ValueError, AttributeError):
                pass

    def request_shutdown(self):
        if not self.shutdown_requested:
            self.shutdown_requested = True
            if self.console:
                self.console.print("\n[bold yellow]Shutdown requested (Graceful)...[/bold yellow]")
            else:
                print("\nShutdown requested...")

            # If paused, we must unpause to allow loop to exit
            self.resume()

    def pause(self):
        if not self.is_paused and not self.shutdown_requested:
            self.is_paused = True
            self._resume_event.clear()
            if self.console:
                self.console.print("\n[bold yellow]PAUSED. Press 'r' to resume or 'q' to quit.[/bold yellow]")

    def resume(self):
        if self.is_paused:
            self.is_paused = False
            self._resume_event.set()
            if self.console:
                self.console.print("\n[bold green]RESUMED.[/bold green]")

    async def wait_if_paused(self):
        """Await this in the processing loop to respect pause state."""
        if self.shutdown_requested:
            return

        if self.is_paused:
            await self._resume_event.wait()

    def check_shutdown(self) -> bool:
        return self.shutdown_requested

    def _keyboard_monitor_windows(self):
        while self._running:
            if msvcrt.kbhit():
                try:
                    ch = msvcrt.getch()
                    try:
                        char = ch.decode('utf-8').lower()
                    except UnicodeDecodeError:
                        continue

                    if char == 'q':
                        # Use call_soon_threadsafe to interact with asyncio loop
                        self._loop.call_soon_threadsafe(self.request_shutdown)
                    elif char == 'p':
                        if not self.is_paused:
                            self._loop.call_soon_threadsafe(self.pause)
                    elif char == 'r':
                        if self.is_paused:
                            self._loop.call_soon_threadsafe(self.resume)
                except (KeyboardInterrupt, SystemExit):
                    pass
                except Exception:
                    logging.error("Error in keyboard monitoring thread", exc_info=True)

            time.sleep(0.1)
