import sqlite3

try:
    conn = sqlite3.connect('.coverage')
    cur = conn.cursor()
    tables = [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'")]
    print('tables:', tables)
    for t in tables:
        cur.execute(f'SELECT COUNT(*) FROM {t}')
        print(t, cur.fetchone()[0])
except Exception as e:
    print('err', repr(e))
