import sys
from pathlib import Path
import sqlite3
import glob
import os

# Add src to path
current_dir = Path(__file__).resolve().parent
if str(current_dir) not in sys.path:
    sys.path.append(str(current_dir))

from store.db import get_db_connection

def reset_scraping_state():
    print("Resetting database scraping status...")
    conn = get_db_connection()
    cursor = conn.cursor()

    # Set all 'success' or 'failed' back to 'pending'
    # Use raw SQL to ensure it works even if store.db update didn't apply
    cursor.execute("""
    UPDATE urls
    SET scraped_status = 'pending',
        extract_error = NULL
    WHERE scraped_status IS NOT NULL
    """)
    rows = cursor.rowcount
    conn.commit()
    conn.close()
    print(f"Updated {rows} rows in database.")

def delete_parquet_files():
    print("Deleting parquet files...")
    # Assume data/articles is relatively located
    data_dir = current_dir.parent / "data" / "articles"
    files = list(data_dir.glob("*.parquet"))

    if not files:
        print("No parquet files found to delete.")
        return

    for f in files:
        try:
            os.remove(f)
            print(f"Deleted {f.name}")
        except (OSError, PermissionError) as e:
            print(f"Error deleting {f.name}: {e}")

if __name__ == "__main__":
    reset_scraping_state()
    delete_parquet_files()
    print("Reset complete. You can now run the scraper.")
