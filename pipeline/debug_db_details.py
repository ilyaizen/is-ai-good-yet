import sqlite3
import os

db_path = "pipeline/data/pipeline.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

cursor.execute("""
    SELECT hn_id, hn_score, hn_comments, sentiment_score, scraped_status 
    FROM urls 
    WHERE content_category = 'AI_DISCOURSE'
""")
rows = cursor.fetchall()

print("AI_DISCOURSE Articles Details:")
print("ID | Score | Comments | Sentiment | Status")
for row in rows:
    print(f"{row[0]} | {row[1]} | {row[2]} | {row[3]} | {row[4]}")

conn.close()
