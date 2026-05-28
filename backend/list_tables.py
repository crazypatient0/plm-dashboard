import sqlite3
conn = sqlite3.connect('plm_dashboard.db')
cur = conn.cursor()
cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
rows = cur.fetchall()
print(f'Total tables: {len(rows)}')
for r in rows:
    print(r[0])
