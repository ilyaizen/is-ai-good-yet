import asyncio
import aiohttp
import json
import os
import argparse
import logging
import sys
from pathlib import Path
from bs4 import BeautifulSoup
from rich.console import Console
from rich.logging import RichHandler
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, TimeRemainingColumn

# Add parent and current directory to path for imports
current_dir = Path(__file__).resolve().parent
parent_dir = current_dir.parent

if str(current_dir) not in sys.path:
    sys.path.append(str(current_dir))
if str(parent_dir) not in sys.path:
    sys.path.append(str(parent_dir))

from interactive import InteractiveSession
from store.paths import get_data_path

# Setup Rich Console
console = Console()
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(console=console, rich_tracebacks=True, markup=True)]
)

# Constants
DEFAULT_TIMEOUT = 15
DEFAULT_END_PAGE = 10  # Only scrape recent pages by default (page 1 = newest)

STATE_FILE = get_data_path("backfill_state.json")

def load_state():
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {}
    return {}

def save_state(page):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, 'w') as f:
        json.dump({"last_page": page}, f)

async def fetch_page(session, url):
    try:
        async with session.get(url, timeout=DEFAULT_TIMEOUT) as response:
            if response.status != 200:
                logging.warning(f"Failed to fetch {url}: Status {response.status}")
                return None
            return await response.text()
    except aiohttp.ClientError as e:
        logging.error(f"HTTP client error fetching {url}: {e}")
        return None
    except Exception as e:
        logging.error(f"Unexpected error fetching {url}: {e}")
        return None

async def backfill(start_page, end_page, output_file, recent_file=None, resume=False):
    # Determine start page
    current_page = start_page
    if resume:
        state = load_state()
        last_page = state.get("last_page")
        if last_page:
            current_page = last_page + 1
            console.print(f"[bold yellow]Resuming from page {current_page}[/bold yellow]")

    if current_page > end_page:
        console.print("[green]Backfill already complete.[/green]")
        return

    # Load existing links
    output_path = Path(output_file)
    if output_path.exists():
        with open(output_path, 'r', encoding='utf-8') as f:
            try:
                existing_links = set(json.load(f))
            except json.JSONDecodeError:
                console.print("[red]Invalid JSON in output file. Starting fresh.[/red]")
                existing_links = set()
    else:
        existing_links = set()

    console.print(f"[blue]Loaded {len(existing_links)} existing links.[/blue]")
    initial_count = len(existing_links)
    found_links = []
    new_links = []  # Track only truly new links

    interactive_session = InteractiveSession(console)
    interactive_session.start()

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    async with aiohttp.ClientSession(headers=headers) as session:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeRemainingColumn(),
            console=console
        ) as progress:

            task_id = progress.add_task("[cyan]Backfilling Pages...", total=(end_page - current_page + 1))

            for page in range(current_page, end_page + 1):
                if interactive_session.check_shutdown():
                    console.print("[bold yellow]Shutdown requested. Saving state...[/bold yellow]")
                    save_state(page - 1)
                    break

                await interactive_session.wait_if_paused()

                url = f"https://histre.com/hn/?tags=+ai&page={page}"
                html = await fetch_page(session, url)

                if html:
                    soup = BeautifulSoup(html, "html.parser")
                    blocks = soup.find_all('div', class_='col-lg')

                    page_new_links = 0
                    for block in blocks:
                        link_element = block.find('a')
                        if not link_element:
                            continue

                        href = link_element.get('href')
                        if not href:
                            continue

                        found_links.append(href)
                        if href not in existing_links:
                            existing_links.add(href)
                            new_links.append(href)
                            page_new_links += 1

                    logging.info(f"Page {page}: Found {len(blocks)} total links, {page_new_links} new")

                # Update progress
                progress.advance(task_id)

                # Incremental save per few pages
                if page % 5 == 0:
                     save_state(page)
                     with open(output_path, 'w', encoding='utf-8') as f:
                        json.dump(list(existing_links), f, indent=2)

                # Polite delay
                await asyncio.sleep(1)

    # Final save
    save_state(page if not interactive_session.check_shutdown() else page - 1)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(list(existing_links), f, indent=2)

    added = len(existing_links) - initial_count
    total_found = len(set(found_links))
    truly_new = len(new_links)

    console.print(f"\n[bold green]Backfill complete![/bold green]")
    console.print(f"  Total links scraped this run: {total_found}")
    console.print(f"  Truly NEW links: [bold cyan]{truly_new}[/bold cyan]")
    console.print(f"  Already existed: {total_found - truly_new}")
    console.print(f"  Total in database: {len(existing_links)}")

    if recent_file:
        recent_path = Path(recent_file)
        with open(recent_path, 'w', encoding='utf-8') as f:
            json.dump(new_links, f, indent=2)
        console.print(f"\n[bold yellow]Saved {len(new_links)} NEW links to {recent_path}[/bold yellow]")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Backfill HN links from Histre")
    parser.add_argument("--start", type=int, default=1, help="Start page number")
    parser.add_argument("--end", type=int, default=DEFAULT_END_PAGE, help="End page number")
    parser.add_argument("--output", type=str, help="Output JSON file (default: adjacent data/ directory)")
    parser.add_argument("--recent", type=str, help="Optional: Output for recent links")
    parser.add_argument("--resume", action="store_true", help="Resume from last saved state")

    args = parser.parse_args()

    # Set default output path relative to script location if not provided
    if args.output is None:
        args.output = str(get_data_path("histre_feed.json"))

    # Ensure output directory exists
    os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)

    try:
        asyncio.run(backfill(args.start, args.end, args.output, args.recent, args.resume))
    except KeyboardInterrupt:
        pass
