import argparse
import json
import sys
from pathlib import Path
import polars as pl

# Add src to path
current_dir = Path(__file__).resolve().parent
if str(current_dir) not in sys.path:
    sys.path.append(str(current_dir))

from store.parquet import read_articles

def get_article(article_id: int):
    try:
        # Scan parquet files
        # We catch the case where no data exists
        try:
            # Calculate absolute path to data/articles
            # This file is in pipeline/src, so data/articles is ../data/articles
            data_dir = Path(__file__).resolve().parent.parent / "data" / "articles"

            # Ensure directory exists to avoid "expanded paths were empty" if completely empty
            if not data_dir.exists():
                print(json.dumps({"error": "Data directory not found"}))
                return

            # Check if any parquet files exist
            if not list(data_dir.glob("articles_*.parquet")):
                print(json.dumps({"error": "No article data files found"}))
                return

            lf = read_articles(shard_dir=data_dir)
        except (FileNotFoundError, OSError, ValueError):
            print(json.dumps({"error": "No data found"}))
            return

        # Filter by url_id
        # We need to collect to get the result
        result = lf.filter(pl.col("url_id") == article_id).collect()  # noqa: F821

        if result.height > 0:
            # Convert to dict
            row = result.row(0, named=True)
            # Handle non-serializable types if any (e.g. dates)
            # Polars usually returns python objects.
            print(json.dumps(row, default=str))
        else:
            print(json.dumps({"error": "Article not found"}))

    except (ValueError, KeyError) as e:
        print(json.dumps({"error": str(e)}))

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--id", type=int, required=True, help="Article ID (url_id)")
    args = parser.parse_args()

    get_article(args.id)
