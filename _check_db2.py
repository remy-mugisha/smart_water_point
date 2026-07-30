import sqlite3
conn = sqlite3.connect('D:\\water_project\\instance\\smart_water.db')
cur = conn.cursor()
cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
tables = [r[0] for r in cur.fetchall()]
print(f'Tables: {tables}')
for t in tables:
    cur.execute(f'SELECT COUNT(*) FROM "{t}"')
    print(f'  {t}: {cur.fetchone()[0]} rows')
conn.close()
