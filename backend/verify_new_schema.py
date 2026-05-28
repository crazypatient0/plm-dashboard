import sqlite3
conn = sqlite3.connect('plm_dashboard.db')
cur = conn.cursor()

cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
tables = [r[0] for r in cur.fetchall()]
print(f"Tables ({len(tables)}): {tables}")

for t in ['part_current', 'part_history', 'document_current', 'document_history', 'conversion_current', 'conversion_history']:
    print(f"\n-- {t} --")
    cur.execute(f"PRAGMA table_info({t})")
    for c in cur.fetchall():
        print(f"  {c[1]} {c[2]}")

for t in ['part_history', 'document_history', 'conversion_history']:
    cur.execute(f"SELECT COUNT(*) FROM {t}")
    print(f"\n{t}: {cur.fetchone()[0]} rows")

for t in ['part_current', 'document_current', 'conversion_current']:
    cur.execute(f"SELECT COUNT(*) FROM {t}")
    print(f"{t}: {cur.fetchone()[0]} rows")

conn.close()
print("\nAll OK!")
