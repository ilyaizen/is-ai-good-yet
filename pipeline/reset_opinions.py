
import sqlite3
from pathlib import Path

DB_PATH = Path('pipeline/data/pipeline.db')

def reset_all_opinion_data():
    if not DB_PATH.exists():
        print(f"Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        print("Resetting opinion data in urls table...")
        # Reset all opinion-related columns and status
        cursor.execute("""
            UPDATE urls
            SET
                filter_score = NULL,
                opinion = NULL,
                is_opinion = NULL,
                sentiment_score = NULL,
                classification_json = NULL,
                status = CASE
                    WHEN hn_id IS NOT NULL THEN 'resolved'
                    ELSE 'pending'
                END
            WHERE
                filter_score IS NOT NULL
                OR opinion IS NOT NULL
                OR is_opinion IS NOT NULL
                OR sentiment_score IS NOT NULL
                OR status = 'prefiltered'
                OR status = 'analyzed'
        """)
        print(f"Rows updated: {cursor.rowcount}")

        print("Clearing prefilter_state table...")
        cursor.execute("DELETE FROM prefilter_state")
        print(f"Rows deleted: {cursor.rowcount}")

        conn.commit()
        print("Successfully reset both databases to have no opinion.")

    except Exception as e:
        print(f"Error resetting database: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    reset_all_opinion_data()
