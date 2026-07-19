"""Materialize article text files from the canonical Parquet store (Phase 3.6).

Parquet is the single canonical write target for scraped articles (refactor
e410767, "use parquet as canonical article store"). The scraper no longer writes
plain-text files. Several consumers still want them though: sentiment_v2 falls
back to data/articles-text/*.txt, and operators inspect articles as .txt.

This derives that view idempotently from Parquet. By default it only writes
files that are MISSING, so existing files (including any cleaned by
clean_articles) are never touched. Use --all to refresh every file from Parquet.

Usage:
    python -m src.materialize_text           # write missing text files only
    python -m src.materialize_text --all     # refresh every file from Parquet
    python -m src.materialize_text --dry-run # report the gap, write nothing
"""

import argparse
import sys
from pathlib import Path

from rich.console import Console

# Allow running both as `python -m src.materialize_text` and as a plain script:
# resolve `from store.*` against this module's dir (src/), matching sibling scripts.
current_dir = Path(__file__).resolve().parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

import polars as pl  # noqa: E402

from store.parquet import read_articles  # noqa: E402
from store.paths import get_articles_text_dir  # noqa: E402
from store.text_store import TextArticleStore  # noqa: E402

console = Console()


def main() -> int:
    parser = argparse.ArgumentParser(description="Materialize article text files from Parquet.")
    parser.add_argument(
        "--all",
        action="store_true",
        help="Refresh every file from Parquet (default: only write missing files).",
    )
    parser.add_argument("--dry-run", action="store_true", help="Report the gap without writing.")
    args = parser.parse_args()

    text_dir = get_articles_text_dir()
    text_store = TextArticleStore(text_dir)

    existing_ids = set(text_store.list_article_ids())
    parquet_id_rows = read_articles().select("hn_id").unique().collect()
    parquet_ids = {row[0] for row in parquet_id_rows.iter_rows() if row[0] is not None}

    missing = sorted(parquet_ids - existing_ids)
    console.print(
        f"[blue]Parquet articles: {len(parquet_ids)} | text files: {len(existing_ids)} | "
        f"missing: {len(missing)}[/blue]"
    )

    targets = sorted(parquet_ids) if args.all else missing
    if not targets:
        console.print("[green]Nothing to materialize — text dir is up to date.[/green]")
        return 0

    if args.dry_run:
        console.print(f"[yellow]DRY RUN: would write {len(targets)} files.[/yellow]")
        for hn_id in targets[-10:]:
            console.print(f"  {hn_id}.txt")
        return 0

    # Push the filter into the LazyFrame so we only collect the rows we need.
    rows = read_articles().filter(pl.col("hn_id").is_in(targets)).collect()

    written = 0
    for row in rows.iter_rows(named=True):
        hn_id = row["hn_id"]
        text_store.save_article(
            hn_id,
            row.get("title"),
            row.get("author"),
            row.get("publish_date"),
            row.get("url") or "",
            row.get("text") or "",
        )
        written += 1

    console.print(f"[bold green]Materialized {written} text files into {text_dir}.[/bold green]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
