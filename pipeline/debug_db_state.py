import sqlite3
import os
import json

db_path = "pipeline/data/pipeline.db"

if not os.path.exists(db_path):
    print(f"Database not found at {db_path}")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

try:
    # Check counts of content categories
    cursor.execute("SELECT content_category, COUNT(*) FROM urls GROUP BY content_category")
    rows = cursor.fetchall()
    print("Content Category Distribution:")
    for row in rows:
        print(f"  {row[0]}: {row[1]}")

    # Check pending analysis for AI_DISCOURSE
    cursor.execute("""
        SELECT COUNT(*) FROM urls 
        WHERE content_category = 'AI_DISCOURSE' 
        AND scraped_status = 'success'
        AND sentiment_score IS NULL
        AND hn_score >= 20
        AND hn_comments >= 5
    """)
    pending = cursor.fetchone()[0]
    print(f"\nPending Analysis (AI_DISCOURSE, score>=20, comments>=5): {pending}")

    # Check if we have OPINION_CODING (legacy)
    cursor.execute("SELECT COUNT(*) FROM urls WHERE content_category = 'OPINION_CODING'")
    legacy = cursor.fetchone()[0]
    print(f"Legacy OPINION_CODING articles: {legacy}")

finally:
    conn.close()
