import sys
from pathlib import Path
import sqlite3

# Add src to path so we can import store.db
current_dir = Path(__file__).resolve().parent
if str(current_dir) not in sys.path:
    sys.path.append(str(current_dir))

import polars as pl
from store.db import get_db_connection
from store.parquet import read_articles

def fix_missing_content():
    print("Checking data integrity...")

    # 1. Get all success IDs from DB
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, url FROM urls WHERE scraped_status = 'success'")
    db_success = {row[0]: row[1] for row in cursor.fetchall()}
    conn.close()

    print(f"DB reports {len(db_success)} successful scrapes.")

    if not db_success:
        print("No successful scrapes found in DB.")
        return

    # 2. Get all available IDs from Parquet
    # This path assumes we are running from project root or the file is in pipeline/src
    data_dir = Path(__file__).resolve().parent.parent / "data" / "articles"

    parquet_ids = set()
    if not data_dir.exists():
        print(f"No data directory found at {data_dir}")
    else:
        try:
            # check if any files exist
            files = list(data_dir.glob("articles_*.parquet"))
            if not files:
                print("No parquet files found.")
            else:
                print(f"Scanning {len(files)} parquet files...")
                lf = read_articles(shard_dir=data_dir)
                # We interpret url_id as Int (Polars infers types, usually Int64)
                parquet_ids = set(lf.select("url_id").collect().to_series().to_list())  # noqa: F821
                print(f"Found {len(parquet_ids)} articles in Parquet storage.")
        except Exception as e:
            print(f"Error reading parquet: {e}")
            # If we error reading parquet, we probably shouldn't reset everything unless we are sure.
            # But usually it means empty or corrupt.
            pass

    # 3. Find missing IDs
    missing_ids = set(db_success.keys()) - parquet_ids
    print(f"Found {len(missing_ids)} IDs marked success in DB but missing content in Parquet.")

    if not missing_ids:
        print("Data integrity check passed. All success items have content.")
        return

    # 4. Update DB
    print("Resetting missing items to 'pending' state...")
    conn = get_db_connection()
    cursor = conn.cursor()

    # Batch update
    # split into chunks to avoid too many SQL variables if necessary, but sqlite handles many
    missing_ids_list = list(missing_ids)

    # SQLite has a limit on variables, usually 32766 or so.
    chunk_size = 1000
    for i in range(0, len(missing_ids_list), chunk_size):
        chunk = missing_ids_list[i:i+chunk_size]
        placeholders = ','.join(['?'] * len(chunk))
        cursor.execute(f"UPDATE urls SET scraped_status = 'pending' WHERE id IN ({placeholders})", chunk)

    conn.commit()
    conn.close()

    print(f"Successfully reset {len(missing_ids)} items. Please run the scraper again.")

if __name__ == "__main__":
    fix_missing_content()
