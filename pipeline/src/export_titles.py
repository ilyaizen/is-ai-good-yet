"""
Export randomized article titles for prompt improvement.

Generates a plain text file with randomized article titles from the database,
useful for feeding to an LLM to generate better classification examples.

Usage (from project root):
    python pipeline/src/export_titles.py
    python pipeline/src/export_titles.py -n 200 -m -o titles.txt
"""

import argparse
import random
import sys
from pathlib import Path
from typing import Optional

# Ensure proper path for imports (works from any directory)
current_dir = Path(__file__).resolve().parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

from rich.console import Console

from store.db import get_db_connection

console = Console()


def export_titles(
    output_file: str = "titles_export.txt",
    limit: int = 100,
    category: Optional[str] = None,
    min_score: int = 0,
    include_metadata: bool = False,
    seed: Optional[int] = None,
) -> int:
    """
    Export randomized article titles to a text file.

    Args:
        output_file: Output file path
        limit: Maximum number of titles to export
        category: Filter by content_category (AI_DISCOURSE, AI_NEWS, AI_OTHER, etc.)
        min_score: Minimum HN score filter
        include_metadata: Include HN ID and score in output
        seed: Random seed for reproducibility

    Returns:
        Number of titles exported
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Build query based on filters
        where_clauses = ["hn_title IS NOT NULL", "hn_title != ''"]
        params = []

        if category:
            where_clauses.append("content_category = ?")
            params.append(category)

        if min_score > 0:
            where_clauses.append("hn_score >= ?")
            params.append(min_score)

        where_sql = " AND ".join(where_clauses)

        # Fetch all matching titles
        cursor.execute(
            f"""
            SELECT hn_id, hn_title, hn_score, content_category
            FROM urls
            WHERE {where_sql}
            ORDER BY hn_score DESC
            """,
            params,
        )
        rows = cursor.fetchall()

        if not rows:
            console.print("[yellow]No titles found matching criteria.[/yellow]")
            return 0

        # Randomize
        if seed is not None:
            random.seed(seed)
        random.shuffle(rows)

        # Limit
        selected = rows[:limit]

        # Write to file
        output_path = Path(output_file)
        with output_path.open("w", encoding="utf-8") as f:
            if include_metadata:
                f.write("# Randomized Article Titles Export\n")
                f.write(f"# Total: {len(selected)} titles\n")
                if category:
                    f.write(f"# Category: {category}\n")
                if min_score > 0:
                    f.write(f"# Min Score: {min_score}\n")
                f.write("#\n")
                f.write("# Format: HN_ID | Score | Category | Title\n")
                f.write("#" + "=" * 60 + "\n\n")

                for hn_id, title, score, cat in selected:
                    f.write(f"{hn_id} | {score:4d} | {cat or 'UNKNOWN':12} | {title}\n")
            else:
                # Plain titles only, one per line
                for _, title, _, _ in selected:
                    f.write(f"{title}\n")

        console.print(f"[green]Exported {len(selected)} titles to {output_path}[/green]")
        return len(selected)

    except Exception as e:
        console.print(f"[red]Error exporting titles: {e}[/red]")
        return 0
    finally:
        if conn:
            conn.close()


def show_categories():
    """Display available content categories and their counts."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT content_category, COUNT(*) as count
            FROM urls
            WHERE hn_title IS NOT NULL AND hn_title != ''
            GROUP BY content_category
            ORDER BY count DESC
            """
        )
        rows = cursor.fetchall()

        console.print("\n[bold blue]Available Content Categories:[/bold blue]")
        for category, count in rows:
            cat_display = category or "NULL"
            console.print(f"  {cat_display:20} {count:5d} articles")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Export randomized article titles for prompt improvement."
    )
    parser.add_argument(
        "-o",
        "--output",
        default="titles_export.txt",
        help="Output file path (default: titles_export.txt)",
    )
    parser.add_argument(
        "-n",
        "--limit",
        type=int,
        default=100,
        help="Maximum number of titles to export (default: 100)",
    )
    parser.add_argument(
        "-c",
        "--category",
        help="Filter by content_category (e.g., AI_DISCOURSE, AI_NEWS)",
    )
    parser.add_argument(
        "--min-score",
        type=int,
        default=0,
        help="Minimum HN score filter (default: 0)",
    )
    parser.add_argument(
        "-m",
        "--metadata",
        action="store_true",
        help="Include HN ID, score, and category in output",
    )
    parser.add_argument(
        "--seed",
        type=int,
        help="Random seed for reproducibility",
    )
    parser.add_argument(
        "--list-categories",
        action="store_true",
        help="List available content categories and exit",
    )

    args = parser.parse_args()

    if args.list_categories:
        show_categories()
    else:
        export_titles(
            output_file=args.output,
            limit=args.limit,
            category=args.category,
            min_score=args.min_score,
            include_metadata=args.metadata,
            seed=args.seed,
        )
