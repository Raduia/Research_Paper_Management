import sqlite3
conn = sqlite3.connect('db.sqlite3')
cur = conn.cursor()
print('profile columns:', cur.execute("PRAGMA table_info(research_portfolio_profile)").fetchall())
print('paper columns:', cur.execute("PRAGMA table_info(research_portfolio_paper)").fetchall())
print('migrations rows:', cur.execute("SELECT app, name, applied FROM django_migrations WHERE app='research_portfolio'").fetchall())
conn.close()
