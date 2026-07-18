import sqlite3

from typing import Set, Optional, List, Tuple
import logging

from .paths import get_pipeline_db_path

DB_PATH = get_pipeline_db_path()
logger = logging.getLogger(__name__)


def get_db_connection():
    """Returns a connection to the SQLite database."""
    return sqlite3.connect(DB_PATH)


def init_db():
    """
    Initializes the SQLite database with the required schema.
    """
    # Ensure data directory exists
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    conn = get_db_connection()
    cursor = conn.cursor()

    # Create urls table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS urls (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        url TEXT UNIQUE NOT NULL,
        hn_id INTEGER,
        hn_score INTEGER,
        hn_comments INTEGER,
        hn_title TEXT,
        hn_timestamp INTEGER,
        hn_author TEXT,
        status TEXT DEFAULT 'pending',
        scraped_status TEXT,
        filter_score INTEGER,
        opinion TEXT,
        is_opinion BOOLEAN,
        sentiment_score REAL,
        classification_json TEXT
    )
    """)
    # V2 eligibility queries (pending_rows / get_story_rows) correlate on hn_id + scraped_status;
    # without this index those subqueries are O(n^2) and hang for minutes on a large urls table.
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_urls_hn_status ON urls(hn_id, scraped_status)"
    )
    conn.commit()
    conn.close()


def migrate_database():
    """
    Migrates the database schema to add missing columns.
    Adds 'opinion' and 'is_opinion' columns if they don't exist.
    Adds retry tracking columns: retry_count, last_retry_at, failure_category.
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Check if opinion column exists
        cursor.execute("PRAGMA table_info(urls)")
        columns = [column[1] for column in cursor.fetchall()]

        if "opinion" not in columns:
            logger.info("Adding missing 'opinion' column to urls table")
            cursor.execute("ALTER TABLE urls ADD COLUMN opinion TEXT")

        if "is_opinion" not in columns:
            logger.info("Adding missing 'is_opinion' column to urls table")
            cursor.execute("ALTER TABLE urls ADD COLUMN is_opinion BOOLEAN")

        if "sentiment_score" not in columns:
            logger.info("Adding missing 'sentiment_score' column to urls table")
            cursor.execute("ALTER TABLE urls ADD COLUMN sentiment_score REAL")

        if "classification_json" not in columns:
            logger.info("Adding missing 'classification_json' column to urls table")
            cursor.execute("ALTER TABLE urls ADD COLUMN classification_json TEXT")

        if "extract_error" not in columns:
            logger.info("Adding missing 'extract_error' column to urls table")
            cursor.execute("ALTER TABLE urls ADD COLUMN extract_error TEXT")

        if "hn_author" not in columns:
            logger.info("Adding missing 'hn_author' column to urls table")
            cursor.execute("ALTER TABLE urls ADD COLUMN hn_author TEXT")

        # Retry tracking columns for modern scraper
        if "retry_count" not in columns:
            logger.info("Adding missing 'retry_count' column to urls table")
            cursor.execute("ALTER TABLE urls ADD COLUMN retry_count INTEGER DEFAULT 0")

        if "last_retry_at" not in columns:
            logger.info("Adding missing 'last_retry_at' column to urls table")
            cursor.execute("ALTER TABLE urls ADD COLUMN last_retry_at INTEGER")

        if "failure_category" not in columns:
            logger.info("Adding missing 'failure_category' column to urls table")
            cursor.execute("ALTER TABLE urls ADD COLUMN failure_category TEXT")

        if "groq_metrics_json" not in columns:
            logger.info("Adding missing 'groq_metrics_json' column to urls table")
            cursor.execute("ALTER TABLE urls ADD COLUMN groq_metrics_json TEXT")

        conn.commit()

        # Create themes table for Phase 5 summary summarization
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS themes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sentiment_group TEXT NOT NULL,
                theme_title TEXT NOT NULL,
                theme_description TEXT NOT NULL,
                sentiment_verdict TEXT,
                article_count INTEGER DEFAULT 0,
                model TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(sentiment_group, theme_title)
            )
        """)
        conn.commit()
        logger.info("Database migration completed successfully")

    except Exception as e:
        logger.error(f"Error during database migration: {e}")
    finally:
        if conn:
            conn.close()


def init_prefilter_state_table():
    """
    Initializes the prefilter_state table for tracking progress.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS prefilter_state (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    conn.commit()
    conn.close()


def get_existing_urls() -> Set[str]:
    """Retrieves a set of all URLs currently in the database."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT url FROM urls")
        rows = cursor.fetchall()
        return {row[0] for row in rows}
    except sqlite3.OperationalError:
        # Table might not exist yet
        return set()
    finally:
        if conn:
            conn.close()


def get_failed_urls() -> Set[str]:
    """Retrieves a set of URLs that previously failed or had no match."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        # Fetch URLs where we have a record but no hn_id (no_match)
        cursor.execute("SELECT url FROM urls WHERE hn_id IS NULL")
        rows = cursor.fetchall()
        return {row[0] for row in rows}
    except sqlite3.OperationalError:
        return set()
    finally:
        if conn:
            conn.close()


def get_urls_missing_author() -> Set[str]:
    """Retrieves a set of URLs that are resolved but missing author."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT url FROM urls WHERE hn_id IS NOT NULL AND (hn_author IS NULL OR hn_author = '')"
        )
        rows = cursor.fetchall()
        return {row[0] for row in rows}
    except sqlite3.OperationalError:
        return set()
    finally:
        if conn:
            conn.close()


def get_recent_resolved_urls(days: int = 30) -> Set[str]:
    """
    Retrieves URLs resolved within the last N days that need metadata refresh.
    Uses hn_timestamp to determine recency. Recent articles on HN continue to
    accumulate votes and comments, so their metadata should be periodically updated.
    """
    import time

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        # Calculate cutoff timestamp (N days ago)
        cutoff_timestamp = int(time.time()) - (days * 86400)
        cursor.execute(
            "SELECT url FROM urls WHERE hn_id IS NOT NULL AND hn_timestamp > ?",
            (cutoff_timestamp,),
        )
        rows = cursor.fetchall()
        return {row[0] for row in rows}
    except sqlite3.OperationalError:
        return set()
    finally:
        if conn:
            conn.close()


def upsert_hn_metadata(
    url: str,
    hn_id: Optional[int],
    hn_score: int,
    hn_comments: int,
    hn_title: str,
    hn_timestamp: int,
    hn_author: str,
):
    """Inserts or updates the HN metadata for a given URL."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        status = "resolved" if hn_id else "no_match"

        cursor.execute(
            """
        INSERT INTO urls (url, hn_id, hn_score, hn_comments, hn_title, hn_timestamp, hn_author, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(url) DO UPDATE SET
            hn_id=excluded.hn_id,
            hn_score=excluded.hn_score,
            hn_comments=excluded.hn_comments,
            hn_title=excluded.hn_title,
            hn_timestamp=excluded.hn_timestamp,
            hn_author=excluded.hn_author,
            status=excluded.status,
            scraped_status = CASE WHEN urls.scraped_status = 'failed' THEN NULL ELSE urls.scraped_status END,
            retry_count = CASE WHEN urls.scraped_status = 'failed' THEN 0 ELSE urls.retry_count END
        """,
            (
                url,
                hn_id,
                hn_score,
                hn_comments,
                hn_title,
                hn_timestamp,
                hn_author,
                status,
            ),
        )
        conn.commit()
    except Exception as e:
        logger.error(f"Error upserting metadata for {url}: {e}")
    finally:
        if conn:
            conn.close()


def get_resolved_urls_for_prefiltering() -> List[Tuple[str, str]]:
    """
    Retrieves URLs that have been resolved (have HN metadata) but not yet prefiltered.
    Returns list of tuples: (url, hn_title)
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT url, hn_title
            FROM urls
            WHERE status = 'resolved'
            AND hn_title IS NOT NULL
            AND (filter_score IS NULL OR status != 'prefiltered')
        """)
        return cursor.fetchall()
    except sqlite3.OperationalError:
        return []
    finally:
        if conn:
            conn.close()


def update_prefilter_status(url: str, filter_score: int):
    """
    Updates the prefilter status, filter_score, opinion, and is_opinion for a given URL.
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Map filter_score to opinion text and boolean
        opinion_text = (
            "opinion"
            if filter_score == 1
            else "neutral"
            if filter_score == 0
            else "unclear"
        )
        is_opinion = 1 if filter_score == 1 else 0

        cursor.execute(
            """
        UPDATE urls
        SET filter_score = ?, opinion = ?, is_opinion = ?, status = 'prefiltered'
        WHERE url = ?
        """,
            (filter_score, opinion_text, is_opinion, url),
        )
        conn.commit()
    except Exception as e:
        logger.error(f"Error updating prefilter status for {url}: {e}")
    finally:
        if conn:
            conn.close()


def get_prefilter_state() -> dict:
    """
    Load saved state for resumable execution.
    Returns dictionary with state keys and values.
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT key, value FROM prefilter_state")
        return {row[0]: row[1] for row in cursor.fetchall()}
    except sqlite3.OperationalError:
        # Table might not exist yet
        return {}
    finally:
        if conn:
            conn.close()


def save_prefilter_state(key: str, value: str):
    """
    Save a single state key-value pair.
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT OR REPLACE INTO prefilter_state (key, value)
            VALUES (?, ?)
        """,
            (key, value),
        )
        conn.commit()
    except Exception as e:
        logger.error(f"Error saving prefilter state {key}: {e}")
    finally:
        if conn:
            conn.close()


def clear_prefilter_state():
    """
    Clear all prefilter state after successful completion.
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM prefilter_state")
        conn.commit()
    except Exception as e:
        logger.error(f"Error clearing prefilter state: {e}")
    finally:
        if conn:
            conn.close()


def get_processed_urls() -> Set[str]:
    """
    Get set of URLs that have already been processed.
    """
    state = get_prefilter_state()
    return {
        k.replace("processed_", "")
        for k, v in state.items()
        if k.startswith("processed_") and v == "1"
    }


def get_prefiltered_stats() -> dict:
    """
    Returns statistics about prefiltered URLs.
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Get counts for different statuses
        cursor.execute("SELECT COUNT(*) FROM urls WHERE status = 'resolved'")
        resolved_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM urls WHERE status = 'prefiltered'")
        prefiltered_count = cursor.fetchone()[0]

        cursor.execute(
            "SELECT COUNT(*) FROM urls WHERE status = 'resolved' AND filter_score IS NULL"
        )
        pending_prefilter_count = cursor.fetchone()[0]

        return {
            "resolved": resolved_count,
            "prefiltered": prefiltered_count,
            "pending_prefilter": pending_prefilter_count,
        }
    except sqlite3.OperationalError:
        return {"resolved": 0, "prefiltered": 0, "pending_prefilter": 0}
    finally:
        if conn:
            conn.close()


def reset_prefilter_data():
    """
    Resets all prefilter-related data to start the process over.
    This clears filter_score, opinion, is_opinion, and status for all URLs.
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Reset prefilter-related columns for all URLs
        cursor.execute("""
        UPDATE urls
        SET filter_score = NULL,
        opinion = NULL,
        is_opinion = NULL,
        status = CASE
            WHEN hn_id IS NOT NULL AND hn_title IS NOT NULL THEN 'resolved'
            ELSE 'pending'
        END
        """)

        # Clear prefilter state table
        cursor.execute("DELETE FROM prefilter_state")

        conn.commit()
        logger.info("Prefilter data has been reset successfully")
        return True
    except Exception as e:
        logger.error(f"Error resetting prefilter data: {e}")
        return False
    finally:
        if conn:
            conn.close()


def get_urls_to_scrape(
    batch_size: int = 100,
    prioritize_opinion: bool = True,
    retry_failed: bool = False,
    randomize: bool = True,
    newest_first: bool = True,
) -> List[Tuple]:
    """
    Retrieves a batch of URLs that need to be scraped.
    Prioritizes URLs with is_opinion=1 if prioritize_opinion is True.
    If retry_failed is True, includes URLs that previously failed.
    If randomize is True (default), shuffles the results to avoid predictable patterns.
    If newest_first is True (default), orders by HN ID DESC (newer articles first).
    Returns list of tuples: (url_id, url, hn_id, hn_score, hn_comments, hn_timestamp)
    """
    import random as rand

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Determine filtering logic
        if retry_failed:
            # Get everything that isn't success
            status_filter = "(scraped_status IS NULL OR scraped_status != 'success')"
        else:
            # Only fresh items
            status_filter = "(scraped_status IS NULL OR scraped_status = 'pending')"

        # Base query - fetch more than needed for better randomization
        fetch_limit = batch_size * 3 if randomize else batch_size
        query = f"""
            SELECT id, url, hn_id, hn_score, hn_comments, hn_timestamp
            FROM urls
            WHERE {status_filter}
            AND hn_id IS NOT NULL
        """

        # Order by HN ID DESC (newest first) or by score (oldest/highest score first)
        # When newest_first=True, we want larger HN IDs (more recent) first
        if prioritize_opinion:
            if newest_first:
                query += " ORDER BY CASE WHEN is_opinion = 1 THEN 1 ELSE 0 END DESC, hn_id DESC"
            else:
                query += " ORDER BY CASE WHEN is_opinion = 1 THEN 1 ELSE 0 END DESC, hn_score DESC"
        else:
            if newest_first:
                query += " ORDER BY hn_id DESC"
            else:
                query += " ORDER BY hn_score DESC"

        query += f" LIMIT {fetch_limit}"

        cursor.execute(query)
        results = cursor.fetchall()

        # Log the ordering being used
        order_desc = "hn_id DESC (newest first)" if newest_first else "hn_score DESC (highest score first)"
        logger.debug(f"get_urls_to_scrape: fetched {len(results)} URLs, ordered by {order_desc}")

        # Randomize the order to avoid predictable scraping patterns
        if randomize and len(results) > 1:
            rand.shuffle(results)
            results = results[:batch_size]

        return results
    except sqlite3.OperationalError:
        return []
    finally:
        if conn:
            conn.close()


def get_pending_scrape_count() -> int:
    """Returns the total number of URLs pending scraping."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM urls WHERE (scraped_status IS NULL OR scraped_status = 'pending') AND hn_id IS NOT NULL"
        )
        return cursor.fetchone()[0]
    except sqlite3.OperationalError:
        return 0
    finally:
        if conn:
            conn.close()


def get_pending_opinion_count() -> int:
    """Returns the number of pending URLs that are suspected opinions."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM urls WHERE (scraped_status IS NULL OR scraped_status = 'pending') AND hn_id IS NOT NULL AND is_opinion = 1"
        )
        return cursor.fetchone()[0]
    except sqlite3.OperationalError:
        return 0
    finally:
        if conn:
            conn.close()


def update_scraped_status(
    url: str,
    status: str,
    error: Optional[str] = None,
    failure_category: Optional[str] = None,
):
    """
    Updates the scraped_status for a URL.
    Also tracks retry count and failure category for modern retry logic.
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Get current retry count
        cursor.execute("SELECT retry_count FROM urls WHERE url = ?", (url,))
        result = cursor.fetchone()
        retry_count = (result[0] or 0) if result else 0

        # Increment retry count if this is a failure
        if status == "failed":
            retry_count += 1

        query = "UPDATE urls SET scraped_status = ?, retry_count = ?, last_retry_at = ?"
        params = [status, retry_count, int(__import__("time").time())]

        if error:
            query += ", extract_error = ?"
            params.append(error)

        if failure_category:
            query += ", failure_category = ?"
            params.append(failure_category)

        query += " WHERE url = ?"
        params.append(url)

        cursor.execute(query, params)
        conn.commit()
    except Exception as e:
        logger.error(f"Error updating scraped status for {url}: {e}")
        # If extract_error column doesn't exist, try adding it or ignoring
        if "no column named extract_error" in str(e).lower():
            try:
                pass
            except:
                pass
    finally:
        if conn:
            conn.close()


def upsert_theme(
    sentiment_group: str,
    theme_title: str,
    theme_description: str,
    sentiment_verdict: str,
    article_count: int,
    model: str,
):
    """
    Insert or update a theme from Phase 5 summary summarization.
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO themes (sentiment_group, theme_title, theme_description, sentiment_verdict, article_count, model)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(sentiment_group, theme_title) DO UPDATE SET
                theme_description = excluded.theme_description,
                sentiment_verdict = excluded.sentiment_verdict,
                article_count = excluded.article_count,
                model = excluded.model,
                created_at = CURRENT_TIMESTAMP
        """,
            (
                sentiment_group,
                theme_title,
                theme_description,
                sentiment_verdict,
                article_count,
                model,
            ),
        )
        conn.commit()
    except Exception as e:
        logger.error(f"Error upserting theme '{theme_title}': {e}")
    finally:
        if conn:
            conn.close()


def get_all_themes() -> List[Tuple]:
    """
    Retrieve all themes for frontend display.
    Returns list of tuples: (id, sentiment_group, theme_title, theme_description, sentiment_verdict, article_count)
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, sentiment_group, theme_title, theme_description, sentiment_verdict, article_count
            FROM themes
            ORDER BY article_count DESC
        """)
        return cursor.fetchall()
    except sqlite3.OperationalError:
        return []
    finally:
        if conn:
            conn.close()


def clear_themes():
    """
    Clear all themes from the themes table.
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM themes")
        conn.commit()
        logger.info("Cleared all themes from database")
    except Exception as e:
        logger.error(f"Error clearing themes: {e}")
    finally:
        if conn:
            conn.close()


def get_themes_stats() -> dict:
    """
    Returns statistics about themes.
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM themes")
        total = cursor.fetchone()[0]

        cursor.execute("""
            SELECT sentiment_group, COUNT(*) as count
            FROM themes
            GROUP BY sentiment_group
        """)
        by_group = {row[0]: row[1] for row in cursor.fetchall()}

        return {
            "total": total,
            "positive": by_group.get("positive", 0),
            "neutral": by_group.get("neutral", 0),
            "negative": by_group.get("negative", 0),
        }
    except sqlite3.OperationalError:
        return {"total": 0, "positive": 0, "neutral": 0, "negative": 0}
    finally:
        if conn:
            conn.close()


def update_last_catch_up(timestamp: int):
    """
    Updates the last catch-up timestamp.
    Stores the Unix timestamp in the prefilter_state table.
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT OR REPLACE INTO prefilter_state (key, value)
            VALUES ('last_catch_up', ?)
        """,
            (str(timestamp),),
        )
        conn.commit()
        logger.info(f"Updated last catch-up timestamp: {timestamp}")
    except Exception as e:
        logger.error(f"Error updating last catch-up timestamp: {e}")
    finally:
        if conn:
            conn.close()


def get_last_catch_up() -> Optional[int]:
    """
    Retrieves the last catch-up timestamp.
    Returns Unix timestamp or None if never run.
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM prefilter_state WHERE key = 'last_catch_up'")
        result = cursor.fetchone()
        if result:
            return int(result[0])
        return None
    except sqlite3.OperationalError:
        return None
    finally:
        if conn:
            conn.close()
