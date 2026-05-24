"""Reset sentiment data for re-analysis."""
from src.store.db import get_db_connection

conn = get_db_connection()
cursor = conn.cursor()
cursor.execute("""
    UPDATE urls
    SET sentiment_score = NULL,
        classification_json = NULL,
        status = 'prefiltered'
    WHERE content_category IN ('AI_DISCOURSE', 'AI_NEWS')
""")
print(f"Reset {conn.total_changes} articles")
conn.commit()
conn.close()
