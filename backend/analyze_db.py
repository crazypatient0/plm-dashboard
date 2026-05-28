import sqlite3
conn = sqlite3.connect('plm_dashboard.db')
cur = conn.cursor()

# Schema of all tables
cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
tables = [r[0] for r in cur.fetchall()]
print('=== TABLES ===')
for t in tables:
    print(f'\n-- {t} --')
    cur.execute(f"PRAGMA table_info({t})")
    cols = cur.fetchall()
    for c in cols:
        print(f'  {c[1]} {c[2]} nullable={not c[3]} default={c[4]}')

# Sample data per data_type
print('\n=== SCRAPE_HISTORY sample ===')
cur.execute("SELECT data_type, COUNT(*), MIN(scraped_at), MAX(scraped_at) FROM scrape_history GROUP BY data_type")
for r in cur.fetchall():
    print(f'  {r}')

print('\n=== SCRAPE_CURRENT sample ===')
cur.execute("SELECT data_type, COUNT(*) FROM scrape_current GROUP BY data_type")
for r in cur.fetchall():
    print(f'  {r}')

print('\n=== RAW_DATA samples ===')
for dt in ['part', 'document', 'conversion']:
    cur.execute(f"SELECT raw_data FROM scrape_history WHERE data_type='{dt}' LIMIT 1")
    r = cur.fetchone()
    if r:
        import json
        d = json.loads(r[0])
        print(f'\n  {dt}:')
        for k, v in d.items():
            print(f'    {k}: {v}')

conn.close()
