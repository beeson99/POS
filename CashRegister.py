
"""
Integrated POS System
Features:
- SQLite product database
- Inventory tracking
- SKU sales screen
- Tax calculation
- Cash checkout/change
- Daily sales report
- Product maintenance (add/edit/delete)
- Cash drawer reconciliation
- CSV export
- Excel export (openpyxl)
- PDF export (reportlab)
"""

import sqlite3, csv
from tkinter import *
from tkinter import ttk, messagebox

DB="pos_integrated.db"
TAX_RATE=0.08

def conn():
    return sqlite3.connect(DB)

def init_db():
    c=conn(); cur=c.cursor()

    cur.execute("""CREATE TABLE IF NOT EXISTS products(
        sku TEXT PRIMARY KEY,
        description TEXT,
        department TEXT,
        price REAL,
        qty INTEGER
    )""")

    cur.execute("""CREATE TABLE IF NOT EXISTS sales(
        sale_id INTEGER PRIMARY KEY AUTOINCREMENT,
        sale_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        subtotal REAL,
        tax REAL,
        total REAL,
        cash REAL,
        change REAL
    )""")

    cur.execute("""CREATE TABLE IF NOT EXISTS sale_items(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sale_id INTEGER,
        sku TEXT,
        description TEXT,
        qty INTEGER,
        price REAL
    )""")

    cur.execute("""CREATE TABLE IF NOT EXISTS drawer(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        business_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        opening_cash REAL,
        expected_cash REAL,
        actual_cash REAL,
        over_short REAL
    )""")

    cur.executemany(
        "INSERT OR IGNORE INTO products VALUES(?,?,?,?,?)",
        [
            ("1001","Coffee","Food",2.50,100),
            ("1002","Bagel","Food",1.75,100),
            ("2001","Notebook","Office",4.99,50),
        ]
    )
    c.commit(); c.close()

class ProductWindow(Toplevel):
    def __init__(self,parent):
        super().__init__(parent)
        self.title("Products")

        self.entries={}
        for r,l in enumerate(["SKU","Description","Department","Price","Qty"]):
            Label(self,text=l).grid(row=r,column=0)
            e=Entry(self); e.grid(row=r,column=1)
            self.entries[l]=e

        Button(self,text="Save",command=self.save).grid(row=5,column=0)
        Button(self,text="Delete",command=self.delete).grid(row=5,column=1)

    def save(self):
        c=conn(); cur=c.cursor()
        cur.execute("""INSERT OR REPLACE INTO products
        VALUES(?,?,?,?,?)""",
        (
            self.entries["SKU"].get(),
            self.entries["Description"].get(),
            self.entries["Department"].get(),
            float(self.entries["Price"].get()),
            int(self.entries["Qty"].get())
        ))
        c.commit(); c.close()
        messagebox.showinfo("Saved","Product saved")

    def delete(self):
        c=conn(); cur=c.cursor()
        cur.execute("DELETE FROM products WHERE sku=?",
                    (self.entries["SKU"].get(),))
        c.commit(); c.close()
        messagebox.showinfo("Deleted","Product deleted")

class POS(Tk):

    def __init__(self):
        super().__init__()
        self.title("Integrated POS")
        self.geometry("1000x700")

        self.cart=[]
        self.subtotal=0.0
        self.sku=StringVar()

        self.build_menu()
        self.build_ui()

    def build_menu(self):
        m=Menu(self)

        maint=Menu(m,tearoff=0)
        maint.add_command(label="Products",
                          command=lambda:ProductWindow(self))

        reports=Menu(m,tearoff=0)
        reports.add_command(label="Daily Report",
                            command=self.daily_report)
        reports.add_command(label="Export CSV",
                            command=self.export_csv)
        reports.add_command(label="Export Excel",
                            command=self.export_excel)
        reports.add_command(label="Export PDF",
                            command=self.export_pdf)

        cash=Menu(m,tearoff=0)
        cash.add_command(label="Reconcile Drawer",
                         command=self.reconcile)

        m.add_cascade(label="Maintenance",menu=maint)
        m.add_cascade(label="Reports",menu=reports)
        m.add_cascade(label="Cash Drawer",menu=cash)
        self.config(menu=m)

    def build_ui(self):
        Entry(self,textvariable=self.sku,font=("Arial",20)).pack(fill=X)

        Button(self,text="Add SKU",command=self.add_item).pack()

        self.lst=Listbox(self,width=100,height=20)
        self.lst.pack(fill=BOTH,expand=True)

        self.total_lbl=Label(self,text="Total: $0.00",
                             font=("Arial",18,"bold"))
        self.total_lbl.pack()

        Button(self,text="Checkout",
               command=self.checkout).pack(pady=10)

    def update_total(self):
        tax=self.subtotal*TAX_RATE
        total=self.subtotal+tax
        self.total_lbl.config(
            text=f"Subtotal ${self.subtotal:.2f}  Tax ${tax:.2f}  Total ${total:.2f}"
        )

    def add_item(self):
        sku=self.sku.get()

        c=conn(); c.row_factory=sqlite3.Row
        cur=c.cursor()
        cur.execute("SELECT * FROM products WHERE sku=?",(sku,))
        p=cur.fetchone()
        c.close()

        if not p:
            messagebox.showerror("Error","SKU not found")
            return

        if p["qty"]<=0:
            messagebox.showerror("Error","Out of stock")
            return

        self.cart.append(dict(p))
        self.lst.insert(END,f"{p['sku']} {p['description']} ${p['price']:.2f}")
        self.subtotal += p["price"]
        self.update_total()
        self.sku.set("")

    def checkout(self):
        if not self.cart:
            return

        tax=self.subtotal*TAX_RATE
        total=self.subtotal+tax

        w=Toplevel(self)
        w.title("Checkout")

        Label(w,text=f"Total Due ${total:.2f}").pack()

        cash_var=StringVar()
        Entry(w,textvariable=cash_var).pack()

        def complete():
            cash=float(cash_var.get())
            if cash<total:
                messagebox.showerror("Error","Insufficient cash")
                return

            change=cash-total

            c=conn(); cur=c.cursor()

            cur.execute("""INSERT INTO sales
            (subtotal,tax,total,cash,change)
            VALUES(?,?,?,?,?)""",
            (self.subtotal,tax,total,cash,change))

            sale_id=cur.lastrowid

            for item in self.cart:
                cur.execute("""INSERT INTO sale_items
                (sale_id,sku,description,qty,price)
                VALUES(?,?,?,?,?)""",
                (sale_id,item["sku"],item["description"],1,item["price"]))

                cur.execute(
                    "UPDATE products SET qty=qty-1 WHERE sku=?",
                    (item["sku"],)
                )

            c.commit(); c.close()

            messagebox.showinfo("Sale Complete",
                                f"Change ${change:.2f}")

            self.cart.clear()
            self.lst.delete(0,END)
            self.subtotal=0
            self.update_total()
            w.destroy()

        Button(w,text="Complete Sale",
               command=complete).pack()

    def daily_report(self):
        c=conn(); cur=c.cursor()
        cur.execute("""SELECT COUNT(*),COALESCE(SUM(total),0)
                    FROM sales
                    WHERE DATE(sale_date)=DATE('now')""")
        cnt,total=cur.fetchone()
        c.close()
        messagebox.showinfo("Daily Report",
                            f"Transactions: {cnt}\nSales: ${total:.2f}")

    def reconcile(self):
        c=conn(); cur=c.cursor()
        cur.execute("SELECT COALESCE(SUM(cash),0) FROM sales")
        expected=cur.fetchone()[0]
        c.close()
        messagebox.showinfo("Reconciliation",
                            f"Expected cash: ${expected:.2f}")

    def export_csv(self):
        c=conn(); cur=c.cursor()
        cur.execute("SELECT * FROM sales")
        rows=cur.fetchall()
        with open("sales_export.csv","w",newline="") as f:
            csv.writer(f).writerows(rows)
        c.close()
        messagebox.showinfo("Export","sales_export.csv created")

    def export_excel(self):
        try:
            from openpyxl import Workbook
        except ImportError:
            messagebox.showerror("Missing","pip install openpyxl")
            return

        c=conn(); cur=c.cursor()
        cur.execute("SELECT * FROM sales")
        wb=Workbook(); ws=wb.active
        for r in cur.fetchall():
            ws.append(r)
        wb.save("sales_export.xlsx")
        c.close()
        messagebox.showinfo("Export","sales_export.xlsx created")

    def export_pdf(self):
        try:
            from reportlab.platypus import SimpleDocTemplate, Paragraph
            from reportlab.lib.styles import getSampleStyleSheet
        except ImportError:
            messagebox.showerror("Missing","pip install reportlab")
            return

        pdf=SimpleDocTemplate("sales_export.pdf")
        pdf.build([Paragraph("Sales Report", getSampleStyleSheet()["Heading1"])])
        messagebox.showinfo("Export","sales_export.pdf created")

if __name__=="__main__":
    init_db()
    POS().mainloop()

