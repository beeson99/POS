"""
Database layer for the POS system.
Centralizes all PostgreSQL connections and queries.
"""
import psycopg2
from config import DB_HOST, DB_PORT, DB_NAME, DB_USER


def get_connection():
    """Return a new psycopg2 connection to the POS database."""
    return psycopg2.connect(
        f"host={DB_HOST} port={DB_PORT} dbname={DB_NAME} user={DB_USER}"
    )


# ── Users / Auth ─────────────────────────────────────────────────────

def validate_login(username, password):
    """Return (role,) tuple if credentials are valid, else None."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
    
        SELECT role FROM users
        WHERE username = %s AND password = %s
    """, (username, password))
    row = cur.fetchone()
    conn.close()
    return row


def get_user_name(username):
    """Return the display name for a username."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT name FROM users WHERE username = %s", (username,))
    row = cur.fetchone()
    conn.close()
    return row[0] if row else username


def list_users():
    """Return list of (username, name, role) tuples."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT username, name, role FROM users ORDER BY username")
    rows = cur.fetchall()
    conn.close()
    return rows


def add_user(username, password, name, role):
    """Insert a new user. Raises psycopg2.IntegrityError on conflict."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO users (username, password, name, role)
        VALUES (%s, %s, %s, %s)
    """, (username, password, name, role))
    conn.commit()
    conn.close()


def delete_user(username):
    """Delete a user by username."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM users WHERE username = %s", (username,))
    conn.commit()
    conn.close()


def verify_manager_password(password):
    """Return manager username if password matches a manager, else None."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT username FROM users
        WHERE password = %s AND role = 'manager'
    """, (password,))
    row = cur.fetchone()
    conn.close()
    return row[0] if row else None


def verify_admin_password(password):
    """Return True if password matches the admin account."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT role FROM users
        WHERE username = 'admin' AND password = %s
    """, (password,))
    row = cur.fetchone()
    conn.close()
    return row is not None


# ── Products ─────────────────────────────────────────────────────────

def get_product(sku):
    """Return a product row (id, sku, description, department, price, ...) or None."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM products WHERE sku = %s AND active = 1", (sku,))
    row = cur.fetchone()
    conn.close()
    return row


def get_product_department(sku):
    """Return the department string for a product SKU."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT department FROM products WHERE sku = %s", (sku,))
    row = cur.fetchone()
    conn.close()
    return row[0] if row else None


def decrement_inventory(sku, quantity, cur=None):
    """Reduce quantity_on_hand for a product.
    Pass an existing cursor to share a transaction."""
    sql = """
        UPDATE products
        SET quantity_on_hand = quantity_on_hand - %s
        WHERE sku = %s
    """
    if cur:
        cur.execute(sql, (quantity, sku))
    else:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(sql, (quantity, sku))
        conn.commit()
        conn.close()


def restore_inventory(sku, quantity, cur=None):
    """Increase quantity_on_hand (used when voiding a sale)."""
    sql = """
        UPDATE products
        SET quantity_on_hand = quantity_on_hand + %s
        WHERE sku = %s
    """
    if cur:
        cur.execute(sql, (quantity, sku))
    else:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(sql, (quantity, sku))
        conn.commit()
        conn.close()


# ── Sales ────────────────────────────────────────────────────────────

def insert_sale(subtotal, tax, total, cash, change, cashier, payment_type,
                check_number, card_last4, register_id):
    """Insert a sale record and return the new sale_id."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO sales
            (subtotal, tax, total, cash_received, change_given,
             cashier, payment_type, check_number, card_last4, register_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING sale_id
    """, (subtotal, tax, total, cash, change, cashier,
          payment_type, check_number, card_last4, register_id))
    sale_id = cur.fetchone()[0]
    conn.commit()
    conn.close()
    return sale_id


def insert_sale_item(sale_id, sku, description, quantity, price, cashier):
    """Insert a single sale_items row."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO sale_items
            (sale_id, sku, description, quantity, price, cashier)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (sale_id, sku, description, quantity, price, cashier))
    conn.commit()
    conn.close()


def insert_department(sale_id, dept, price, quantity, register_id, z_id=None):
    """Insert a department record for a sold item."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO department
            (sale_id, Department, price, z_id, register_id, quantity)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (sale_id, dept, price * quantity, z_id, register_id, quantity))
    conn.commit()
    conn.close()


def get_sale(sale_id):
    """Return a sale row or None."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM sales WHERE sale_id = %s", (sale_id,))
    row = cur.fetchone()
    conn.close()
    return row


def is_sale_voided(sale_id):
    """Return True if the sale has been voided."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT voided FROM sales WHERE sale_id = %s", (sale_id,))
    row = cur.fetchone()
    conn.close()
    return bool(row and row[0] == 1)


def get_sale_items(sale_id):
    """Return list of dicts for sale_items belonging to a sale."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT sku, description, quantity, price
        FROM sale_items
        WHERE sale_id = %s
        ORDER BY sale_item_id
    """, (sale_id,))
    items = []
    for sku, desc, qty, price in cur.fetchall():
        items.append({
            "sku": str(sku),
            "description": str(desc),
            "price": price,
            "quantity": qty,
        })
    conn.close()
    return items


def get_sale_items_for_void(sale_id):
    """Return list of (sku, quantity) for restoring inventory on void."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT sku, quantity FROM sale_items WHERE sale_id = %s
    """, (sale_id,))
    rows = cur.fetchall()
    conn.close()
    return rows


def void_sale(sale_id, manager_name):
    """Mark a sale and its department entries as voided. Restores inventory."""
    conn = get_connection()
    cur = conn.cursor()

    # Restore inventory for non-department items
    items = get_sale_items_for_void(sale_id)
    for sku, qty in items:
        if not sku.startswith("DEPT"):
            restore_inventory(sku, qty, cur)

    cur.execute("""
        UPDATE sales
        SET voided = 1, void_date = CURRENT_TIMESTAMP, voided_by = %s
        WHERE sale_id = %s
    """, (manager_name, sale_id))

    cur.execute("""
        UPDATE department
        SET voided = 1, void_date = CURRENT_TIMESTAMP, voided_by = %s
        WHERE sale_id = %s
    """, (manager_name, sale_id))

    conn.commit()
    conn.close()


# ── Z Reports ────────────────────────────────────────────────────────

def create_z_report(transaction_count, sales_total, tax_total, register_id):
    """Insert a z_report row and return the z_id."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO z_reports
            (transaction_count, sales_total, tax_total, register_id)
        VALUES (%s, %s, %s, %s)
        RETURNING z_id
    """, (transaction_count, sales_total, tax_total, register_id))
    z_id = cur.fetchone()[0]
    conn.commit()
    conn.close()
    return z_id


def assign_z_id_to_sales(z_id, register_id):
    """Assign z_id to all unassigned, non-voided sales on a register."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        UPDATE sales SET z_id = %s
        WHERE z_id IS NULL AND COALESCE(voided, 0) = 0
          AND register_id = %s
    """, (z_id, register_id))
    conn.commit()
    conn.close()


def assign_z_id_to_departments(z_id, register_id):
    """Assign z_id to all unassigned, non-voided department entries on a register."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        UPDATE department SET z_id = %s
        WHERE z_id IS NULL AND voided = 0
          AND register_id = %s
    """, (z_id, register_id))
    conn.commit()
    conn.close()
