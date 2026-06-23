import sqlite3

def get_product(sku):
    conn = sqlite3.connect("pos.db")
    conn.row_factory = sqlite3.Row

    cur = conn.cursor()

    cur.execute("""
        SELECT *
        FROM products
        WHERE sku = ?
          AND active = 1
    """, (sku,))

    row = cur.fetchone()

    conn.close()

    return row

td = get_product(1001)
print (td)
