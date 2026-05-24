
import sqlite3
import json
conn = sqlite3.connect('pipeline/data/pipeline.db')
c = conn.cursor()
c.execute("SELECT id, url, scraped_status FROM urls WHERE scraped_status='success' LIMIT 5")
rows = c.fetchall()
print(json.dumps(rows, indent=2))
conn.close()
