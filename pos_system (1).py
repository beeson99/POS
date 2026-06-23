
import tkinter as tk
from tkinter import messagebox
import sqlite3

DB_NAME = "pos.db"

def initialize_database():
    conn = sqlite3.connect(DB_NAME)
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

    cur.execute("""
    CREATE TABLE IF NOT EXISTS sales (
        sale_id INTEGER PRIMARY KEY AUTOINCREMENT,
        sale_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        total REAL
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS sale_items (
        sale_item_id INTEGER PRIMARY KEY AUTOINCREMENT,
        sale_id INTEGER,
        sku TEXT,
        description TEXT,
        quantity INTEGER,
        price REAL
    )
    """)

    products = [
        ("1001", "Coffee", "Food", 2.50),
        ("1002", "Bagel", "Food", 1.75),
        ("1003", "Sandwich", "Food", 5.99),
        ("2001", "Notebook", "Office", 4.99),
        ("2002", "Pen", "Office", 1.25),
        ("3001", "B&W Print", "Printing", 0.10),
        ("3002", "Color Print", "Printing", 0.50)
    ]

    for p in products:
        cur.execute("""
        INSERT OR IGNORE INTO products
        (sku, description, department, price)
        VALUES (?, ?, ?, ?)
        """, p)

    conn.commit()
    conn.close()

def get_product(sku):
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute(
        "SELECT * FROM products WHERE sku=? AND active=1",
        (sku,)
    )

    row = cur.fetchone()
    conn.close()
    return row

class POS:

    def __init__(self, root):
        self.root = root
        self.root.title("POS System")
        self.root.geometry("900x650")

        self.total = 0.0
        self.cart = []
        self.sku_var = tk.StringVar()

        self.build_ui()

    def build_ui(self):

        tk.Label(self.root, text="SKU Entry",
                 font=("Arial", 16)).grid(row=0, column=0, sticky="w")

        tk.Entry(
            self.root,
            textvariable=self.sku_var,
            font=("Arial", 20),
            width=20
        ).grid(row=1, column=0, columnspan=4, sticky="ew")

        self.cart_list = tk.Listbox(
            self.root,
            width=80,
            height=15,
            font=("Courier", 12)
        )
        self.cart_list.grid(row=2, column=0, columnspan=4)

        self.total_label = tk.Label(
            self.root,
            text="TOTAL: $0.00",
            font=("Arial", 20, "bold")
        )
        self.total_label.grid(row=3, column=0, columnspan=4)

        keypad = [
            ["7", "8", "9"],
            ["4", "5", "6"],
            ["1", "2", "3"],
            ["0", "C", "Enter"]
        ]

        for r, row in enumerate(keypad):
            for c, key in enumerate(row):
                tk.Button(
                    self.root,
                    text=key,
                    width=10,
                    height=3,
                    command=lambda k=key: self.key_press(k)
                ).grid(row=r + 4, column=c)

        buttons = ["Food", "Office", "Printing", "Checkout"]

        for i, b in enumerate(buttons):
            tk.Button(
                self.root,
                text=b,
                width=15,
                height=3,
                command=lambda x=b: self.department_click(x)
            ).grid(row=4 + i, column=3)

    def key_press(self, key):

        if key == "C":
            self.sku_var.set("")
            return

        if key == "Enter":
            self.add_item()
            return

        self.sku_var.set(self.sku_var.get() + key)

    def add_item(self):

        sku = self.sku_var.get().strip()

        if not sku:
            return

        product = get_product(sku)

        if not product:
            messagebox.showerror("Not Found", f"SKU {sku} not found")
            return

        self.cart.append({
            "sku": product["sku"],
            "description": product["description"],
            "price": product["price"],
            "quantity": 1
        })

        self.cart_list.insert(
            tk.END,
            f"{product['sku']:6} {product['description']:<25} ${product['price']:>7.2f}"
        )

        self.total += product["price"]
        self.total_label.config(text=f"TOTAL: ${self.total:.2f}")
        self.sku_var.set("")

    def department_click(self, dept):

        if dept == "Checkout":
            self.checkout()
            return

        messagebox.showinfo("Department", f"{dept} selected")

    def checkout(self):

        if not self.cart:
            return

        win = tk.Toplevel(self.root)
        win.title("Checkout")
        win.geometry("350x250")

        tk.Label(
            win,
            text=f"Sale Total: ${self.total:.2f}",
            font=("Arial", 18)
        ).pack(pady=10)

        cash_var = tk.StringVar()

        tk.Label(
            win,
            text="Cash Received",
            font=("Arial", 14)
        ).pack()

        tk.Entry(
            win,
            textvariable=cash_var,
            font=("Arial", 18),
            justify="right"
        ).pack(pady=10)

        change_label = tk.Label(
            win,
            text="Change: $0.00",
            font=("Arial", 18, "bold")
        )
        change_label.pack(pady=10)

        def calc():
            try:
                cash = float(cash_var.get())
                change_label.config(
                    text=f"Change: ${cash - self.total:.2f}"
                )
            except ValueError:
                messagebox.showerror("Error", "Invalid amount")

        def complete():
            try:
                cash = float(cash_var.get())

                if cash < self.total:
                    messagebox.showerror(
                        "Insufficient Cash",
                        "Cash received is less than total."
                    )
                    return

                change = cash - self.total

                conn = sqlite3.connect(DB_NAME)
                cur = conn.cursor()

                cur.execute(
                    "INSERT INTO sales(total) VALUES(?)",
                    (self.total,)
                )

                sale_id = cur.lastrowid

                for item in self.cart:
                    cur.execute("""
                    INSERT INTO sale_items
                    (sale_id, sku, description, quantity, price)
                    VALUES (?, ?, ?, ?, ?)
                    """, (
                        sale_id,
                        item["sku"],
                        item["description"],
                        item["quantity"],
                        item["price"]
                    ))

                conn.commit()
                conn.close()

                messagebox.showinfo(
                    "Sale Complete",
                    f"Sale #{sale_id}\n"
                    f"Total: ${self.total:.2f}\n"
                    f"Cash: ${cash:.2f}\n"
                    f"Change: ${change:.2f}"
                )

                self.cart.clear()
                self.cart_list.delete(0, tk.END)
                self.total = 0.0
                self.total_label.config(text="TOTAL: $0.00")

                win.destroy()

            except ValueError:
                messagebox.showerror("Error", "Invalid amount")

        tk.Button(win, text="Calculate Change",
                  command=calc).pack(pady=5)

        tk.Button(win, text="Complete Sale",
                  command=complete).pack(pady=5)

if __name__ == "__main__":
    initialize_database()

    root = tk.Tk()
    app = POS(root)
    root.mainloop()
