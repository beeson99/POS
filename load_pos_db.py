import sqlite3

conn = sqlite3.connect("pos.db")
cur = conn.cursor()

products = [
    ("1001", "Coffee", "Food", 2.50),
    ("1002", "Bagel", "Food", 1.75),
    ("2001", "Notebook", "Office", 4.99),
    ("2002", "Pen", "Office", 1.25),
    ("3001", "B&W Print", "Printing", 0.10),
    ("3002", "Color Print", "Printing", 0.50)
]

for product in products:
    cur.execute("""
        INSERT OR IGNORE INTO products
        (sku, description, department, price)
        VALUES (?, ?, ?, ?)
    """, product)

conn.commit()
conn.close()
