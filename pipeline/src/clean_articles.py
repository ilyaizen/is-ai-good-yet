"""
Clean Article Text (Phase 4.5a).

Features:
- Configurable cleaning patterns (curly quotes, dashes, extra newlines)
- Preserves emojis via Unicode range filtering
- Optional backup before cleaning
- Incremental mode (--new-only) to process only recently added files

Incremental mode uses a timestamp file to track the last clean time.
Only files modified after this timestamp are processed.
"""

import sys
import re
import shutil
import argparse
import json
from pathlib import Path
from datetime import datetime
from rich.console import Console
from rich.progress import track

console = Console()

# Timestamp file location (in data directory)
LAST_CLEAN_TIMESTAMP_FILE = "last_clean_timestamp.json"

CLEANING_PATTERNS = {
    'curly_quotes_double_left': (r'[\u201C]', '"'),
    'curly_quotes_double_right': (r'[\u201D]', '"'),
    'curly_quotes_single_left': (r'[\u2018]', "'"),
    'curly_quotes_single_right': (r'[\u2019]', "'"),
    'ellipsis': (r'[\u2026]', '...'),
    'em_dash': (r'[\u2014]', '-'),
    'en_dash': (r'[\u2013]', '-'),
    'triple_newlines': (r'\n\n\n+', '\n\n'),
}


def remove_short_title_lines(text: str) -> str:
    """Remove short standalone title-like lines (4-15 words, isolated)."""
    lines = text.split('\n')
    result = []

    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            result.append(line)
            continue

        word_count = len(stripped.split())
        if 4 <= word_count <= 15:
            prev_empty = (i == 0) or (not lines[i-1].strip())
            next_empty = (i == len(lines) - 1) or (not lines[i+1].strip() if i+1 < len(lines) else True)
            if prev_empty and next_empty and not stripped.endswith(('.', '!', '?', ':', ';', ',')):
                continue

        result.append(line)

    return '\n'.join(result)


def apply_cleaning_patterns(text: str) -> str:
    """Apply all regex-based cleaning patterns."""
    for name, (pattern, replacement) in CLEANING_PATTERNS.items():
        text = re.sub(pattern, replacement, text)  # noqa: F821
    return text


def update_header_format(content: str) -> str:
    """Convert old header format (Title/Author/Date/URL) to new format (Title/URL)."""
    parts = content.split('\n\n', 1)
    if len(parts) < 2:
        return content

    header_block = parts[0]
    body_text = parts[1]

    metadata = {}
    for line in header_block.split('\n'):
        if ': ' in line:
            key, val = line.split(': ', 1)
            metadata[key.lower()] = val.strip()

    title = metadata.get('title', '')
    url = metadata.get('url', '')

    new_content = f"Title: {title}\nURL: {url}\n\n{body_text}"
    return new_content


def clean_file(file_path: Path) -> str:
    """Clean a single article file and return the cleaned content."""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    content = update_header_format(content)

    parts = content.split('\n\n', 1)
    if len(parts) == 2:
        header = parts[0]
        body = parts[1]
        body = apply_cleaning_patterns(body)
        body = remove_short_title_lines(body)
        content = f"{header}\n\n{body}"
    else:
        content = apply_cleaning_patterns(content)

    return content


def get_last_clean_timestamp(data_dir: Path) -> float | None:
    """Get the timestamp of the last clean run, or None if never run."""
    timestamp_file = data_dir / LAST_CLEAN_TIMESTAMP_FILE
    if not timestamp_file.exists():
        return None
    try:
        with open(timestamp_file, 'r') as f:
            data = json.load(f)
            return data.get('last_clean_timestamp')
    except (json.JSONDecodeError, IOError):
        return None


def save_last_clean_timestamp(data_dir: Path, timestamp: float):
    """Save the current timestamp as the last clean time."""
    timestamp_file = data_dir / LAST_CLEAN_TIMESTAMP_FILE
    with open(timestamp_file, 'w') as f:
        json.dump({
            'last_clean_timestamp': timestamp,
            'last_clean_datetime': datetime.fromtimestamp(timestamp).isoformat()
        }, f, indent=2)


def get_files_to_clean(articles_dir: Path, data_dir: Path, new_only: bool) -> list[Path]:
    """Get list of files to clean, optionally filtering by modification time."""
    all_files = list(articles_dir.glob('*.txt'))

    if not new_only:
        return all_files

    last_timestamp = get_last_clean_timestamp(data_dir)
    if last_timestamp is None:
        # First run - process all files
        console.print("[yellow]No previous clean timestamp found - processing all files[/yellow]")
        return all_files

    # Filter to only files modified after last clean
    new_files = [f for f in all_files if f.stat().st_mtime > last_timestamp]

    if not new_files:
        console.print(f"[dim]Last clean: {datetime.fromtimestamp(last_timestamp).strftime('%Y-%m-%d %H:%M:%S')}[/dim]")
        console.print("[green]No new files to clean since last run[/green]")
    else:
        console.print(f"[blue]Found {len(new_files)} new files since last clean ({len(all_files)} total)[/blue]")

    return new_files


def main():
    parser = argparse.ArgumentParser(description='Clean article text files')
    parser.add_argument('--no-backup', action='store_true',
                        help='Skip creating backup of original files')
    parser.add_argument('--new-only', action='store_true',
                        help='Only clean files added since last run (incremental mode)')
    parser.add_argument('--clean-all', action='store_true',
                        help='Clean all files regardless of modification time')
    args = parser.parse_args()

    current_dir = Path(__file__).resolve().parent
    data_dir = current_dir.parent / 'data'
    articles_dir = data_dir / 'articles-text'
    backup_dir = data_dir / 'articles-text-backup'

    if not articles_dir.exists():
        console.print(f"[red]Articles directory not found: {articles_dir}[/red]")
        sys.exit(1)

    # Determine which files to clean
    # --clean-all overrides --new-only
    new_only = args.new_only and not args.clean_all
    txt_files = get_files_to_clean(articles_dir, data_dir, new_only)

    if not txt_files:
        # Save timestamp even if no files to clean (to update the checkpoint)
        if new_only:
            save_last_clean_timestamp(data_dir, datetime.now().timestamp())
        return

    console.print(f"[blue]Cleaning {len(txt_files)} article files[/blue]")

    # Backup only the files we're about to clean
    if not args.no_backup:
        console.print(f"[blue]Creating backup in {backup_dir}...[/blue]")
        backup_dir.mkdir(parents=True, exist_ok=True)
        for f in track(txt_files, description="Backing up..."):
            shutil.copy2(f, backup_dir / f.name)
        console.print(f"[green]Backup complete: {len(txt_files)} files[/green]")

    # Clean the files
    for f in track(txt_files, description="Cleaning articles..."):
        cleaned_content = clean_file(f)
        with open(f, 'w', encoding='utf-8') as out:
            out.write(cleaned_content)

    # Save the current timestamp for incremental mode
    save_last_clean_timestamp(data_dir, datetime.now().timestamp())

    console.print(f"[bold green]Cleaning complete! {len(txt_files)} files cleaned.[/bold green]")


if __name__ == '__main__':
    main()
