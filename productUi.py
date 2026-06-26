import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
import psycopg2

DB_NAME = "pos.db"


class ProductMaintenance:

    def __init__(self, root):
        self.root = root
        self.root.title("Product Maintenance")
        self.root.geometry("1000x600")

        self.create_widgets()
        self.load_products()

    def get_connection(self):
       # return sqlite3.connect(DB_NAME)
        return psycopg2.connect(
            "host=localhost port=5432 dbname=posdb user=pos"
        )

    def create_widgets(self):

        frm = tk.Frame(self.root)
        frm.pack(fill="x", padx=10, pady=10)

        tk.Label(frm, text="SKU").grid(row=0, column=0, sticky="w")
        self.sku = tk.Entry(frm, width=20)
        self.sku.grid(row=0, column=1)

        tk.Label(frm, text="Description").grid(row=0, column=2, sticky="w")
        self.description = tk.Entry(frm, width=40)
        self.description.grid(row=0, column=3)

        tk.Label(frm, text="Department").grid(row=1, column=0, sticky="w")
        self.department = tk.Entry(frm, width=20)
        self.department.grid(row=1, column=1)

        tk.Label(frm, text="Price").grid(row=1, column=2, sticky="w")
        self.price = tk.Entry(frm, width=20)
        self.price.grid(row=1, column=3)

        tk.Label(frm, text="Qty On Hand").grid(row=2, column=0, sticky="w")
        self.qty = tk.Entry(frm, width=20)
        self.qty.grid(row=2, column=1)

        self.active_var = tk.IntVar(value=1)

        tk.Checkbutton(
            frm,
            text="Active",
            variable=self.active_var
        ).grid(row=2, column=2, sticky="w")

        btn_frame = tk.Frame(frm)
        btn_frame.grid(row=3, column=0, columnspan=4, pady=10)

        tk.Button(
            btn_frame,
            text="Add",
            width=12,
            command=self.add_product
        ).pack(side="left", padx=5)

        tk.Button(
            btn_frame,
            text="Update",
            width=12,
            command=self.update_product
        ).pack(side="left", padx=5)

        tk.Button(
            btn_frame,
            text="Delete",
            width=12,
            command=self.delete_product
        ).pack(side="left", padx=5)

        tk.Button(
            btn_frame,
            text="Clear",
            width=12,
            command=self.clear_fields
        ).pack(side="left", padx=5)

        tk.Label(frm, text="Search").grid(row=4, column=0)

        self.search = tk.Entry(frm, width=30)
        self.search.grid(row=4, column=1)

        tk.Button(
            frm,
            text="Search",
            command=self.search_products
        ).grid(row=4, column=2)

        columns = (
            "id",
            "sku",
            "description",
            "department",
            "price",
            "qty",
            "active"
        )

        self.tree = ttk.Treeview(
            self.root,
            columns=columns,
            show="headings",
            height=20
        )

        self.tree.heading("id", text="ID")
        self.tree.heading("sku", text="SKU")
        self.tree.heading("description", text="Description")
        self.tree.heading("department", text="Department")
        self.tree.heading("price", text="Price")
        self.tree.heading("qty", text="Qty")
        self.tree.heading("active", text="Active")

        self.tree.column("id", width=60)
        self.tree.column("sku", width=120)
        self.tree.column("description", width=300)
        self.tree.column("department", width=120)
        self.tree.column("price", width=100)
        self.tree.column("qty", width=100)
        self.tree.column("active", width=80)

        self.tree.pack(fill="both", expand=True, padx=10, pady=10)

        self.tree.bind(
            "<<TreeviewSelect>>",
            self.on_select
        )

    def load_products(self):

        for row in self.tree.get_children():
            self.tree.delete(row)

        conn = self.get_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT
                id,
                sku,
                description,
                department,
                price,
                quantity_on_hand,
                active
            FROM products
            ORDER BY description
        """)

        for row in cur.fetchall():
            self.tree.insert("", "end", values=row)

        conn.close()

    def add_product(self):

        try:
            conn = self.get_connection()
            cur = conn.cursor()

            cur.execute("""
                INSERT INTO products
                (
                    sku,
                    description,
                    department,
                    price,
                    quantity_on_hand,
                    active
                )
                VALUES (%s,%s,%s,%s,%s,%s)
            """,
            (
                self.sku.get(),
                self.description.get(),
                self.department.get(),
                float(self.price.get()),
                int(self.qty.get()),
                self.active_var.get()
            ))

            conn.commit()
            conn.close()

            self.load_products()
            self.clear_fields()

        except Exception as e:
            messagebox.showerror("Error", str(e))

    def update_product(self):

        selected = self.tree.focus()

        if not selected:
            return

        product_id = self.tree.item(selected)["values"][0]

        try:
            conn = self.get_connection()
            cur = conn.cursor()

            cur.execute("""
                UPDATE products
                SET
                    sku=%s,
                    description=%s,
                    department=%s,
                    price=%s,
                    quantity_on_hand=%s,
                    active=%s
                WHERE id=%s
            """,
            (
                self.sku.get(),
                self.description.get(),
                self.department.get(),
                float(self.price.get()),
                int(self.qty.get()),
                self.active_var.get(),
                product_id
            ))

            conn.commit()
            conn.close()

            self.load_products()

        except Exception as e:
            messagebox.showerror("Error", str(e))

    def delete_product(self):

        selected = self.tree.focus()

        if not selected:
            return

        product_id = self.tree.item(selected)["values"][0]

        if not messagebox.askyesno(
            "Delete",
            "Delete selected product?"
        ):
            return

        conn = self.get_connection()
        cur = conn.cursor()

        cur.execute(
            "DELETE FROM products WHERE id=%s",
            (product_id,)
        )

        conn.commit()
        conn.close()

        self.load_products()
        self.clear_fields()

    def search_products(self):

        text = self.search.get()

        for row in self.tree.get_children():
            self.tree.delete(row)

        conn = self.get_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT
                id,
                sku,
                description,
                department,
                price,
                quantity_on_hand,
                active
            FROM products
            WHERE
                sku LIKE %s
                OR description LIKE %s
            ORDER BY description
        """,
        (
            f"%{text}%",
            f"%{text}%"
        ))

        for row in cur.fetchall():
            self.tree.insert("", "end", values=row)

        conn.close()

    def on_select(self, event):

        selected = self.tree.focus()

        if not selected:
            return

        row = self.tree.item(selected)["values"]

        self.clear_fields()

        self.sku.insert(0, row[1])
        self.description.insert(0, row[2])
        self.department.insert(0, row[3])
        self.price.insert(0, row[4])
        self.qty.insert(0, row[5])

        self.active_var.set(row[6])

    def clear_fields(self):

        self.sku.delete(0, tk.END)
        self.description.delete(0, tk.END)
        self.department.delete(0, tk.END)
        self.price.delete(0, tk.END)
        self.qty.delete(0, tk.END)

        self.active_var.set(1)


if __name__ == "__main__":

    root = tk.Tk()

    ProductMaintenance(root)

    root.mainloop()