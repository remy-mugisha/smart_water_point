import sqlite3
conn = sqlite3.connect('D:\\water_project\\instance\\smart_water.db')
cur = conn.cursor()

cur.execute('SELECT COUNT(*) FROM water_points')
print(f'Total water points: {cur.fetchone()[0]}')

cur.execute('SELECT DISTINCT district FROM water_points')
print(f'Districts: {[r[0] for r in cur.fetchall()]}')

print('\n--- Bugesera water points ---')
cur.execute("SELECT water_point_id, sector, cell, current_status FROM water_points WHERE district='Bugesera' LIMIT 15")
for row in cur.fetchall():
    print(f'  {row[0]}: sector={row[1]}, cell={row[2]}, status={row[3]}')

print('\n--- Bugesera distinct sectors ---')
cur.execute("SELECT DISTINCT sector FROM water_points WHERE district='Bugesera' ORDER BY sector")
for row in cur.fetchall():
    print(f'  {row[0]}')

print('\n--- Bugesera cells ---')
cur.execute("SELECT COUNT(*) FROM water_points WHERE district='Bugesera' AND (cell IS NULL OR cell = '')")
print(f'  Empty cells: {cur.fetchone()[0]}')
cur.execute("SELECT COUNT(*) FROM water_points WHERE district='Bugesera' AND cell IS NOT NULL AND cell != ''")
print(f'  Non-empty cells: {cur.fetchone()[0]}')

print('\n--- Non-Bugesera distinct sectors ---')
cur.execute("SELECT DISTINCT sector FROM water_points WHERE district != 'Bugesera' ORDER BY sector")
for row in cur.fetchall():
    print(f'  {row[0]}')

print('\n--- Non-Bugesera cells ---')
cur.execute("SELECT COUNT(*) FROM water_points WHERE district != 'Bugesera' AND (cell IS NULL OR cell = '')")
print(f'  Empty cells: {cur.fetchone()[0]}')

conn.close()
