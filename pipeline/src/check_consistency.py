import sys
from pathlib import Path
import polars as pl

# Add src to path
current_dir = Path(__file__).resolve().parent
if str(current_dir) not in sys.path:
    sys.path.append(str(current_dir))

from store.db import get_db_connection
from store.parquet import read_articles

def check_consistency(fix=False):
    print("Checking consistency between Database and Parquet files...")

    # 1. Get DB successful IDs
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, url FROM urls WHERE scraped_status = 'success'")
    db_rows = cursor.fetchall()
    conn.close()

    db_ids = {row[0] for row in db_rows}
    print(f"Database reports {len(db_ids)} successfully scraped articles.")

    # 2. Get Parquet IDs
    data_dir = Path(__file__).resolve().parent.parent / "data" / "articles"
    if not data_dir.exists() or not list(data_dir.glob("articles_*.parquet")):
        print("No parquet files found.")
        parquet_ids = set()
    else:
        try:
            # We use helper to read all files with consistent schema
            df = read_articles(shard_dir=data_dir).select("url_id").collect()
            parquet_ids = set(df["url_id"].to_list())
            print(f"Parquet files contain {len(parquet_ids)} unique articles.")
        except (FileNotFoundError, OSError) as e:
            print(f"File system error reading parquet files: {e}")
            parquet_ids = set()
        except Exception as e:
            print(f"Unexpected error reading parquet files: {e}")
            parquet_ids = set()

    # 3. Find Phantom Articles (In DB but not in Parquet)
    missing_ids = db_ids - parquet_ids

    if missing_ids:
        print(f"\nFOUND {len(missing_ids)} PHANTOM ARTICLES (in DB but missing from content storage).")
        print("These articles cause 'Content not found' errors.")

        if fix:
            print("Fixing consistency by resetting status to 'pending'...")
            conn = get_db_connection()
            cursor = conn.cursor()

            # Using executemany might be faster but simple loop is fine for <10k
            # Convert set to list of tuples for executemany
            to_update = [(id,) for id in missing_ids]

            cursor.executemany("UPDATE urls SET scraped_status = 'pending' WHERE id = ?", to_update)
            conn.commit()
            conn.close()
            print("Fixed. You can now re-run the scraper to fetch these articles.")
        else:
            print("Run with --fix to reset their status to 'pending'.")
    else:
        print("\nConsistency check passed. No phantom articles found.")

    # 4. Check for orphans (In Parquet but not in DB) - less critical but good to know
    orphans = parquet_ids - db_ids
    if orphans:
        print(f"Found {len(orphans)} orphan articles in Parquet (not marked success in DB).")

if __name__ == "__main__":
    fix_flag = "--fix" in sys.argv
    check_consistency(fix=fix_flag)
