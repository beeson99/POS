import sqlite3

conn = sqlite3.connect("pos.db")
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sku TEXT UNIQUE,
    description TEXT NOT NULL,
    department TEXT,
    price REAL NOT NULL,
    active INTEGER DEFAULT 1
)
""")

conn.commit()
conn.close()
