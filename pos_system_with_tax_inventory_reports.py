import tkinter as tk
from tkmacosx import Button
from tkinter import messagebox
from tkinter import simpledialog
from functools import partial
import sqlite3
from datetime import datetime
from tkinter import simpledialog
import customtkinter as ctk
from CTkMessagebox import CTkMessagebox
from escpos.printer import Usb  
from barcode import Code128
from barcode.writer import ImageWriter

#------------------------------------------------------------------
# Point of Sale System (POS)
# Developed by Patrick Beeson
# (C) 2026 Patrick Beeson
# Change Log:
# Date        Who          Reason
# 2026-06-23  Patrick B.   Initial Release
#-------------------------------------------------------------------


# Set the following for your system.
DB_NAME = "pos.db"
COMPANY_NAME = "Test Company"
COMPANY_ADDRESS = "3420 Hwy 98"
COMPANY_ADDRESS2 = "Yourtown, NY 01111"
COMPANY_TELEPHONE="802-999-9999"
TAX_RATE = 0.06
DEPT001="Food"
DEPT002="Office"
DEPT003="Printing"
DEPT004="Dept 004"
DEPT005="Dept 005"
DEPT006="Dept 006"
DEPT007="Dept 007"
DEPT008="Dept 008"

ctk.set_appearance_mode("system") 
#ctk.set_default_color_theme("blue")  # Themes: "blue" (standard), "green", "dark-blue"

#Printer Code for RONGTA Thermal Printers
# Font A
FONTA="\x1b\x4d\x00"

# Font B (smaller)
FONTB="\x1b\x4d\x01"

# Bold on
BOLDON="\x1b\x45\x01"

# Bold off
BOLDOFF="\x1b\x45\x00"

# Double width
DOUBLEWIDTH="\x1d\x21\x10"

# Double height
DOUBLEHEIGHT="\x1d\x21\x01"

# Double width + height
DOUBLEWIDTHHEIGHT="\x1d\x21\x11"

# Underline
UNDERLINE="\x1b\x2d\x01"

# Normal
NORMAL="\x1d\x21\x00"

# Center
CENTER="\x1b\x61\x01"

def initialize_database():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        username TEXT PRIMARY KEY,
        password TEXT NOT NULL,
        Name TEXT NOT NULL,
        role TEXT DEFAULT 'cashier'
    )
    """)

    cur.execute("""
    INSERT OR IGNORE INTO users
        (username,password,name,role)
        VALUES
    ('admin','admin123','Administrator','manager')
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sku TEXT UNIQUE,
        description TEXT NOT NULL,
        department TEXT,
        price REAL NOT NULL,
        quantity_on_hand INTEGER DEFAULT 0,
        active INTEGER DEFAULT 1
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS department (
        sale_id integer primary key autoincrement,
        sale_date TIMESTAMP default current_timestamp,
        Department TEXT,
        price REAL NOT NULL,
        z_id INTEGER 
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS sales (
        sale_id INTEGER PRIMARY KEY AUTOINCREMENT,
        sale_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        subtotal REAL,
        tax REAL,
        total REAL,
        cash_received REAL,
        change_given REAL,
        cashier TEXT,
        payment_type TEXT,
        check_number TEXT,
        card_last4 TEXT,
        z_id INTEGER,
        voided INTEGER DEFAULT 0,
        void_date TIMESTAMP,
        voided_by TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS sale_items (
        sale_item_id INTEGER PRIMARY KEY AUTOINCREMENT,
        sale_id INTEGER,
        sku TEXT,
        description TEXT,
        quantity INTEGER,
        price REAL,
        cashier TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS z_reports (
        z_id INTEGER PRIMARY KEY AUTOINCREMENT,
        report_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        transaction_count INTEGER,
        sales_total REAL,
        tax_total REAL
    )
    """)

    products = [
        ("1001", "Coffee", "DEPT001", 2.50, 100),
        ("1002", "Bagel", "DEPT001", 1.75, 50),
        ("1003", "Sandwich", "DEPT001", 5.99, 25),
        ("2001", "Notebook", "DEPT002", 4.99, 100),
        ("2002", "Pen", "DEPT002", 1.25, 250),
        ("3001", "B&W Print", "DEPT003", 0.10, 10000),
        ("3002", "Color Print", "DEPT003", 0.50, 5000)
    ]

    for p in products:
        cur.execute("""
        INSERT OR IGNORE INTO products
        (sku,description,department,price,quantity_on_hand)
        VALUES (?,?,?,?,?)
        """, p)

    conn.commit()
    conn.close()

def validate_login(username, password):

    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    cur.execute("""
    SELECT role
    FROM users
    WHERE username = ?
      AND password = ?
    """, (username, password))

    row = cur.fetchone()

    conn.close()

    return row

def get_product(sku):
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM products WHERE sku=? AND active=1", (sku,))
    row = cur.fetchone()
    conn.close()
    return row

def print_report(report_text,barcodetext):

    barcode = Code128(barcodetext, writer=ImageWriter())
    barcode.save("barcode")

    p = Usb(0x0fe6, 0x811e)
    p.set(align='left', width=1, height=1)
    
    # Replace with your Rongta USB Vendor ID and Product ID
    print (barcodetext)
    if barcodetext is not None:
        p.text(report_text)
        p.set(align='center')
        p.image("barcode.png")
        p.text("\n\n\n")

    try:
        p.cut()
    except:
        pass

    p.close()

def print_x_report(report_text):

    p = Usb(0x0fe6, 0x811e)
    p.set(align='left', width=1, height=1)
    p.text(report_text)
    p.text("\n\n\n")

    try:
        p.cut()
    except:
        pass

    p.close()

def x_report():

    now = datetime.now()
    formatted_now = now.strftime("%m/%d/%Y %H:%M")

    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    cur.execute("""
    SELECT
        COUNT(*),
        COALESCE(SUM(subtotal),0),
        COALESCE(SUM(tax),0),
        COALESCE(SUM(total),0)
    FROM sales
    WHERE z_id IS NULL
        AND COALESCE(voided,0)=0
    """)

    txns, subtotal, tax, total = cur.fetchone()
    
    cur.execute("""
    SElECT
        COUNT(*),
        COALESCE(SUM(subtotal),0),
        COALESCE(SUM(tax),0),
        COALESCE(SUM(total),0)
    FROM sales
    WHERE CHECK_NUMBER is NOT NULL
    AND z_id IS NULL
        AND COALESCE(voided,0)=0
    """)

    checkTns, checkSubtotal, checkTax, checkTotal = cur.fetchone()

    cur.execute("""
    SElECT
        COUNT(*),
        COALESCE(SUM(subtotal),0),
        COALESCE(SUM(tax),0),
        COALESCE(SUM(total),0)
    FROM sales
    WHERE CARD_LAST4 is NOT NULL
    AND z_id IS NULL
        AND COALESCE(voided,0)=0
    """)

    cardTns, cardSubtotal, cardTax, cardTotal = cur.fetchone()

    cur.execute("""
    SElECT
        COUNT(*),
        COALESCE(SUM(subtotal),0),
        COALESCE(SUM(tax),0),
        COALESCE(SUM(total),0)
    FROM sales
    WHERE CARD_LAST4 is NULL
    AND CHECK_NUMBER is NULL
    AND z_id IS NULL
        AND COALESCE(voided,0)=0
    """)
    cashTns, cashSubtotal, cashTax, cashTotal   = cur.fetchone()
    
    cur.execute("""
        SElECT
            COUNT(*),
            COALESCE(SUM(price),0)
        FROM department
        WHERE z_id is NULL
        and Department = "DEPT001"
        """)
    dept01Count, dept01Total = cur.fetchone()

    cur.execute("""
        SElECT
            COUNT(*),
            COALESCE(SUM(price),0)
        FROM department
        WHERE z_id is NULL
        and Department = "DEPT002"
        """)
    dept02Count, dept02Total = cur.fetchone()

    cur.execute("""
        SElECT
            COUNT(*),
            COALESCE(SUM(price),0)
        FROM department
        WHERE z_id is NULL
        and Department = "DEPT003"
        """)
    dept03Count, dept03Total = cur.fetchone()

    cur.execute("""
        SElECT
            COUNT(*),
            COALESCE(SUM(price),0)
        FROM department
        WHERE z_id is NULL
        and Department = "DEPT004"
        """)
    dept04Count, dept04Total = cur.fetchone()

    cur.execute("""
        SElECT
            COUNT(*),
            COALESCE(SUM(price),0)
        FROM department
        WHERE z_id is NULL
        and Department = "DEPT005"
        """)
    dept05Count, dept05Total = cur.fetchone()

    cur.execute("""
        SElECT
            COUNT(*),
            COALESCE(SUM(price),0)
        FROM department
        WHERE z_id is NULL
        and Department = "DEPT006"
        """)
    dept06Count, dept06Total = cur.fetchone()

    cur.execute("""
        SElECT
            COUNT(*),
            COALESCE(SUM(price),0)
        FROM department
        WHERE z_id is NULL
        and Department = "DEPT007"
        """)
    dept07Count, dept07Total = cur.fetchone()

    cur.execute("""
        SElECT
            COUNT(*),
            COALESCE(SUM(price),0)
        FROM department
        WHERE z_id is NULL
        and Department = "DEPT008"
        """)
    dept08Count, dept08Total = cur.fetchone()

    deptTotal = dept08Total+dept07Total+dept06Total+dept05Total+dept04Total+dept03Total+dept02Total+dept01Total
    deptCountTotal = dept08Count+dept07Count+dept06Count+dept05Count+dept04Count+dept03Count+dept02Count+dept01Count

    report = []
    report.append(f"{DOUBLEWIDTHHEIGHT}")
    report.append(f"{CENTER}") 
    report.append(f"X REPORT") 
    report.append(f"{NORMAL}") 
    report.append(f"{formatted_now}")
    report.append("-" * 42)
    report.append(f"{CENTER}Sales and Taxes Summary{NORMAL}")
    report.append("-" * 42)
    report.append(f"Total Net Sales: ${subtotal:8.2f}".rjust(42))
    report.append(f"Tax:             ${tax:8.2f}".rjust(42))
    report.append(f"Total Sales:     ${total:8.2f}".rjust(42))
    report.append(f"Transactions :    {txns}".rjust(42))
    
    report.append("")
    report.append("-" * 42)
    report.append("Departments".center(42))
    report.append("-" * 42)
    report.append(f"     Department             Count    Amount   ")
    report.append(f"DEPT001 ({DEPT001:^11}): ({dept01Count:4}) ${dept01Total:8.2f}".rjust(42))
    report.append(f"DEPT002 ({DEPT002:^11}): ({dept02Count:4}) ${dept02Total:8.2f}".rjust(42))
    report.append(f"DEPT003 ({DEPT003:^11}): ({dept03Count:4}) ${dept03Total:8.2f}".rjust(42))
    report.append(f"DEPT004 ({DEPT004:^11}): ({dept04Count:4}) ${dept04Total:8.2f}".rjust(42))
    report.append(f"DEPT005 ({DEPT005:^11}): ({dept05Count:4}) ${dept05Total:8.2f}".rjust(42))
    report.append(f"DEPT006 ({DEPT006:^11}): ({dept06Count:4}) ${dept06Total:8.2f}".rjust(42))
    report.append(f"DEPT007 ({DEPT007:^11}): ({dept07Count:4}) ${dept07Total:8.2f}".rjust(42))
    report.append(f"DEPT008 ({DEPT008:^11}): ({dept08Count:4}) ${dept08Total:8.2f}".rjust(42))
    report.append(f"Department Totals ({deptCountTotal:4}) ${deptTotal:8.2f}".rjust(42))
    report.append("")
    report.append("-" * 42)
    report.append("Payment Details".center(42))
    report.append("-" * 42)
    report.append(f"{'Cash':<15}{cashTns:>5} ${cashTotal:>10.2f}".rjust(42))
    report.append(f"{'Credit':<15}{cardTns:>5} ${cardTotal:>10.2f}".rjust(42))
    report.append(f"{'Checks':<15}{checkTns:>5} ${checkTotal:>10.2f}".rjust(42))
    report.append("")
    report.append("")

    conn.close()
    
    #Print the report
    report_text = "\n".join(report)

    try:
        print_x_report(report_text)
    except Exception as e:
        print(f"Printer Error: {e}")

    return report_text


def z_report():

    now = datetime.now()
    formatted_now = now.strftime("%m/%d/%Y %H:%M")

    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    cur.execute("""
        SELECT
            COUNT(*),
            COALESCE(SUM(subtotal),0),
            COALESCE(SUM(total),0),
            COALESCE(SUM(tax),0)
        FROM sales
        WHERE z_id IS NULL
            AND COALESCE(voided,0)=0
    """)

    txns, subtotal, total, tax = cur.fetchone()

    cur.execute("""
    SElECT
        COUNT(*),
        COALESCE(SUM(subtotal),0),
        COALESCE(SUM(tax),0),
        COALESCE(SUM(total),0)
    FROM sales
    WHERE CHECK_NUMBER is NOT NULL
    AND z_id IS NULL
        AND COALESCE(voided,0)=0
    """)

    checkTns, checkSubtotal, checkTax, checkTotal = cur.fetchone()

    cur.execute("""
    SElECT
        COUNT(*),
        COALESCE(SUM(subtotal),0),
        COALESCE(SUM(tax),0),
        COALESCE(SUM(total),0)
    FROM sales
    WHERE CARD_LAST4 is NOT NULL
    AND z_id IS NULL
        AND COALESCE(voided,0)=0
    """)

    cardTns, cardSubtotal, cardTax, cardTotal = cur.fetchone()

    cur.execute("""
    SElECT
        COUNT(*),
        COALESCE(SUM(subtotal),0),
        COALESCE(SUM(tax),0),
        COALESCE(SUM(total),0)
    FROM sales
    WHERE CARD_LAST4 is NULL
    AND CHECK_NUMBER is NULL
    AND z_id IS NULL
        AND COALESCE(voided,0)=0
    """)

    cashTns, cashSubtotal, cashTax, cashTotal = cur.fetchone()

    

    cur.execute("""
        SElECT
            COUNT(*),
            COALESCE(SUM(price),0)
        FROM department
        WHERE z_id is NULL
        and Department = "DEPT001"
        """)
    dept01Count, dept01Total = cur.fetchone()

    cur.execute("""
        SElECT
            COUNT(*),
            COALESCE(SUM(price),0)
        FROM department
        WHERE z_id is NULL
        and Department = "DEPT002"
        """)
    dept02Count, dept02Total = cur.fetchone()

    cur.execute("""
        SElECT
            COUNT(*),
            COALESCE(SUM(price),0)
        FROM department
        WHERE z_id is NULL
        and Department = "DEPT003"
        """)
    dept03Count, dept03Total = cur.fetchone()

    cur.execute("""
        SElECT
            COUNT(*),
            COALESCE(SUM(price),0)
        FROM department
        WHERE z_id is NULL
        and Department = "DEPT004"
        """)
    dept04Count, dept04Total = cur.fetchone()

    cur.execute("""
        SElECT
            COUNT(*),
            COALESCE(SUM(price),0)
        FROM department
        WHERE z_id is NULL
        and Department = "DEPT005"
        """)
    dept05Count, dept05Total = cur.fetchone()

    cur.execute("""
        SElECT
            COUNT(*),
            COALESCE(SUM(price),0)
        FROM department
        WHERE z_id is NULL
        and Department = "DEPT006"
        """)
    dept06Count, dept06Total = cur.fetchone()

    cur.execute("""
        SElECT
            COUNT(*),
            COALESCE(SUM(price),0)
        FROM department
        WHERE z_id is NULL
        and Department = "DEPT007"
        """)
    dept07Count, dept07Total = cur.fetchone()

    cur.execute("""
        SElECT
            COUNT(*),
            COALESCE(SUM(price),0)
        FROM department
        WHERE z_id is NULL
        and Department = "DEPT008"
        """)
    dept08Count, dept08Total = cur.fetchone()

    deptTotal = dept08Total+dept07Total+dept06Total+dept05Total+dept04Total+dept03Total+dept02Total+dept01Total
    deptCountTotal = dept08Count+dept07Count+dept06Count+dept05Count+dept04Count+dept03Count+dept02Count+dept01Count

    cur.execute("""
    INSERT INTO z_reports
    (
        transaction_count,
        sales_total,
        tax_total
    )
    VALUES (?,?,?)
    """,
    (
        txns,
        total,
        tax
    ))

    z_id = cur.lastrowid

    cur.execute("""
        UPDATE sales
        SET z_id = ?
        WHERE z_id IS NULL
    """,(z_id,))

    conn.commit()

    cur.execute("""
        UPDATE department
        SET z_id = ?
        WHERE z_id IS NULL
    """,(z_id,))
    
    
    conn.commit()

    report = []
    report.append(f"{DOUBLEWIDTHHEIGHT}")
    report.append(f"{CENTER}") 
    report.append(f"Z REPORT") 
    report.append(f"{NORMAL}") 
    report.append(f"{formatted_now}")
    report.append("-" * 42)
    report.append(f"{CENTER}Sales and Taxes Summary{NORMAL}")
    report.append("-" * 42)
    report.append(f"Total Net Sales: ${subtotal:8.2f}".rjust(42))
    report.append(f"Tax:             ${tax:8.2f}".rjust(42))
    report.append(f"Total Sales:     ${total:8.2f}".rjust(42))
    report.append(f"Transactions :    {txns}".rjust(42))
    
    report.append("")
    report.append("-" * 42)
    report.append("Departments".center(42))
    report.append("-" * 42)
    report.append(f"     Department             Count    Amount   ")
    report.append(f"DEPT001 ({DEPT001:^11}): ({dept01Count:4}) ${dept01Total:8.2f}".rjust(42))
    report.append(f"DEPT002 ({DEPT002:^11}): ({dept02Count:4}) ${dept02Total:8.2f}".rjust(42))
    report.append(f"DEPT003 ({DEPT003:^11}): ({dept03Count:4}) ${dept03Total:8.2f}".rjust(42))
    report.append(f"DEPT004 ({DEPT004:^11}): ({dept04Count:4}) ${dept04Total:8.2f}".rjust(42))
    report.append(f"DEPT005 ({DEPT005:^11}): ({dept05Count:4}) ${dept05Total:8.2f}".rjust(42))
    report.append(f"DEPT006 ({DEPT006:^11}): ({dept06Count:4}) ${dept06Total:8.2f}".rjust(42))
    report.append(f"DEPT007 ({DEPT007:^11}): ({dept07Count:4}) ${dept07Total:8.2f}".rjust(42))
    report.append(f"DEPT008 ({DEPT008:^11}): ({dept08Count:4}) ${dept08Total:8.2f}".rjust(42))
    report.append(f"Department Totals ({deptCountTotal:4}) ${deptTotal:8.2f}".rjust(42))
    report.append("")
    report.append("-" * 42)
    report.append("Payment Details".center(42))
    report.append("-" * 42)
    report.append(f"{'Cash':<15}{cashTns:>5} ${cashTotal:>10.2f}".rjust(42))
    report.append(f"{'Credit':<15}{cardTns:>5} ${cardTotal:>10.2f}".rjust(42))
    report.append(f"{'Checks':<15}{checkTns:>5} ${checkTotal:>10.2f}".rjust(42))
    report.append("")
    report.append("")
    conn.close()

    report_text = "\n".join(report)

    try:
        print_x_report(report_text)
    except Exception as e:
        print(f"Printer Error: {e}")

    return report_text   



#------------------------------------------------------
# set up ecspos printer settings
#------------------------------------------------------
#p = Serial(
#    devfile='COM5',
#    baudrate=9600,
#    bytesize=8,
#    parity='N',
#    stopbits=1,
#    timeout=1
#)

class LoginWindow:

    def __init__(self, root):

        self.root = root
        self.user = None

        self.win = tk.Toplevel(root)
        self.win.title("Login to Cash Register")
        self.win.geometry("350x200")
        self.win.grab_set()

        root.columnconfigure(0, weight=0)
        root.rowconfigure(0, weight=0)

        tk.Label(
            self.win,
            text="Username"
        ).pack(pady=5)

        self.username = tk.Entry(self.win)
        self.username.pack()

        tk.Label(
            self.win,
            text="Password"
        ).pack(pady=5)

        self.password = tk.Entry(
            self.win,
            show="*"
        )
        self.password.pack()

        # Put cursor in username field
        self.username.focus_set()

        # Enter key support
        self.win.bind(
            '<Return>',
            lambda event: self.login()
        )

        self.win.bind(
            '<KP_Enter>',
            lambda event: self.login()
        )

        tk.Button(
            self.win,
            text="Login",
            command=self.login
        ).pack(pady=10)

    def login(self):

        username = self.username.get()
        password = self.password.get()

        result = validate_login(
            username,
            password
        )

        if result:
            self.user = {
                "username": username,
                "role": result[0]
            }

            self.win.destroy()

        else:
            messagebox.showerror(
                "Login Failed",
                "Invalid username or password"
            )

def start_login(root):

    login = LoginWindow(root)

    root.wait_window(login.win)

    #print(login.user)

    if login.user:

        root.deiconify()

        for widget in root.winfo_children():
            widget.destroy()

        POS(root, login.user)

    else:
        root.destroy()


class POS:

    def __init__(self, root, user):
        self.user = user
        self.root = root
        self.root.title("POS System")
        self.root.geometry("1200x650")

        self.cart = []
        self.subtotal = 0.0
        self.sku_var = tk.StringVar()

        self.build_ui()
        self.root.after(
            100,
            lambda: self.sku_entry.focus_set()
        )

        # Physical Enter key and Enter on keyboard
        self.root.bind('<Return>', lambda event: self.add_item())
        self.root.bind('<KP_Enter>', lambda event: self.add_item())

    def logout(self):

        if not messagebox.askyesno(
            "Logout",
            f"Logout {self.user['username']}?"
        ):
            return

        self.cart.clear()
        self.subtotal = 0
        self.sku_var.set("")

        for widget in self.root.winfo_children():
            widget.destroy()

        start_login(self.root)
 

    def manage_users(self):

        if self.user["role"] != "manager":
            messagebox.showerror(
                "Access Denied",
                "Manager access required."
            )
            return

        win = tk.Toplevel(self.root)
        win.title("User Maintenance")
        win.geometry("500x500")

        # User List

        tk.Label(
            win,
            text="Current Users",
            font=("Arial",14,"bold")
        ).pack()

        user_list = tk.Listbox(
            win,
            width=40,
            height=10
        )

        user_list.pack(pady=10)

        def load_users():

            user_list.delete(0, tk.END)

            conn = sqlite3.connect(DB_NAME)
            cur = conn.cursor()

            cur.execute("""
            SELECT username, name, role
            FROM users
            ORDER BY username
            """)

            for username, name, role in cur.fetchall():
                user_list.insert(
                    tk.END,
                    f"{username} {name} ({role})"
                )

            conn.close()

        load_users()

        # Username

        tk.Label(win, text="Username").pack()

        username_var = tk.StringVar()

        tk.Entry(
            win,
            textvariable=username_var
        ).pack()

        # Name
        tk.Label(win, text="Name").pack()

        name_var = tk.StringVar()

        tk.Entry(
            win,
            textvariable=name_var
        ).pack()

        # Password

        tk.Label(win, text="Password").pack()

        password_var = tk.StringVar()

        tk.Entry(
            win,
            textvariable=password_var,
            show="*"
        ).pack()

        # Role

        tk.Label(win, text="Role").pack()

        role_var = tk.StringVar(value="cashier")

        tk.OptionMenu(
            win,
            role_var,
            "cashier",
            "manager"
        ).pack()

        # Add User

        def add_user():

            username = username_var.get().strip()
            password = password_var.get().strip()
            name = name_var.get().strip()
            role = role_var.get()

            if not username or not password:
                messagebox.showerror(
                    "Error",
                    "Username and password required."
                )
                return

            try:

                conn = sqlite3.connect(DB_NAME)
                cur = conn.cursor()

                cur.execute("""
                INSERT INTO users
                (
                    username,
                    password,
                    name,
                    role
                )
                VALUES (?,?,?,?)
                """,
                (
                    username,
                    password,
                    name,
                    role
                ))

                conn.commit()
                conn.close()

                username_var.set("")
                password_var.set("")

                load_users()

            except sqlite3.IntegrityError:

                messagebox.showerror(
                    "Error",
                    "User already exists."
                )

        # Delete User

        def delete_user():

            selection = user_list.curselection()

            if not selection:
                return

            username = (
                user_list.get(selection[0])
                .split(" (")[0]
            )

            if username == "admin":

                messagebox.showerror(
                    "Error",
                    "Cannot delete admin."
                )

                return

            if not messagebox.askyesno(
                "Delete User",
                f"Delete {username}?"
            ):
                return

            conn = sqlite3.connect(DB_NAME)
            cur = conn.cursor()

            cur.execute("""
                DELETE FROM users
                WHERE username = ?
            """, (username,))

            conn.commit()
            conn.close()

            load_users()

        # Buttons

        tk.Button(
            win,
            text="Add User",
            command=add_user,
            bg="#FFFFFF",
            fg="#50C878"
        ).pack(pady=5)

        tk.Button(
            win,
            text="Delete User",
            command=delete_user,
            bg="#FFFFFF",
            fg="#8B0000"
        ).pack(pady=5)

    def return_key(self, event):
        self.add_item()

    def void_transaction_by_number(self):

        sale_id = simpledialog.askinteger(
            "Void Transaction",
            "Enter Transaction Number:"
        )

        if sale_id is None:
            return

        password = simpledialog.askstring(
            "Manager Authorization",
            "Enter manager password:",
            show="*"
        )

        if not password:
            return

        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()

        cur.execute("""
        SELECT username
            FROM users
            WHERE password = ?
            AND role = 'manager'
        """, (password,))

        manager = cur.fetchone()

        if not manager:
            conn.close()
            messagebox.showerror(
                "Access Denied",
                "Manager authorization required."
            )
            return

        manager_name = manager[0]

        cur.execute("""
        SELECT total, voided
        FROM sales
        WHERE sale_id = ?
        """, (sale_id,))

        sale = cur.fetchone()

        if not sale:
            conn.close()
            messagebox.showerror(
                "Error",
                "Transaction not found."
            )
            return

        if sale[1] == 1:
            conn.close()
            messagebox.showerror(
                "Error",
                "Transaction already voided."
            )
            return

        if not messagebox.askyesno(
            "Confirm Void",
            f"Void transaction #{sale_id}?"
        ):
            conn.close()
            return
        


        # Restore inventory
        cur.execute("""
        SELECT sku, quantity
        FROM sale_items
        WHERE sale_id = ?
        """, (sale_id,))

        items = cur.fetchall()

        for sku, qty in items:

            if not sku.startswith("DEPT"):

                cur.execute("""
                UPDATE products
                SET quantity_on_hand =
                    quantity_on_hand + ?
                WHERE sku = ?
                """, (qty, sku))

        cur.execute("""
        UPDATE sales
        SET voided = 1,
            void_date = CURRENT_TIMESTAMP,
            voided_by = ?
        WHERE sale_id = ?
        """,
        (
            manager_name,
            sale_id
        ))

        conn.commit()
        conn.close()

        receipt = f"""
        *** VOID RECEIPT ***

        Transaction #: {sale_id}

        Voided By: {manager_name}

        Date: {datetime.now():%m/%d/%Y %H:%M}

        ************************
        """

        print_x_report(receipt)

        messagebox.showinfo(
            "Transaction Voided",
            f"Transaction #{sale_id} has been voided."
        )

    def void_item(self):

        selection = self.cart_list.curselection()

        if not selection:
            messagebox.showwarning(
                "Void",
                "Select an item first."
            )
            return

        index = selection[0]

        item = self.cart[index]

        if not messagebox.askyesno(
            "Void Item",
            f"Void {item['description']}?"
        ):
            return

        self.subtotal -= item["price"]

        del self.cart[index]

        self.cart_list.delete(index)

        self.update_totals()

        self.sku_entry.focus_set()    

    def build_ui(self):

        username = self.user['username']

        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()

        cur.execute("""
            SELECT name
            FROM users
            WHERE username = ?
        """, (username,))

        row = cur.fetchone()

        if row:
            sname = row[0]
        else:
            sname = username

        conn.close()

        tk.Label(
            self.root,
            text=f"User: {sname}"
        ).grid(row=0,column=6)

        tk.Label(self.root, text="SKU/Price Entry",
                 font=("Arial",16)).grid(row=0,column=2)
        
        
        self.sku_entry = tk.Entry(
            self.root,
            textvariable=self.sku_var,
            font=("Arial",20)
        )

        self.sku_entry.grid(
            row=1,
            column=1,
            columnspan=4,
            sticky="ew"
        )

        self.sku_entry.focus_set()

        self.cart_list = tk.Listbox(
            self.root,
            width=80,
            height=15,
            font=("Courier",12)
        )
        self.cart_list.grid(row=2,column=1,columnspan=4)

        self.total_label = tk.Label(
            self.root,
            text="Subtotal: $0.00  Tax: $0.00  Total: $0.00",
            font=("Arial",18,"bold")
        )
        self.total_label.grid(row=3,column=0,columnspan=4)

        keypad = [
            ["7","8","9"],
            ["4","5","6"],
            ["1","2","3"],
            ["0",".","C","Enter"]
        ]

        for r,row in enumerate(keypad):
            for c,key in enumerate(row):
                Button(
                self.root,
                text=key,
                width=150,
                height=60,
                bg="#1434A4",
                fg="#FFFFFF",
                bd=0,
                highlightthickness=2,
                relief="raised",
                command=lambda k=key: self.key_press(k)
                ).grid(row=r+4,column=c)

        Button(
            self.root,
            text="Checkout",
            command=self.checkout,
            bg="#7393B3",
            fg="#FFFFFF",
            width=150,
            height=60,
            padx=0, pady=0,
            highlightthickness=2,
            relief="raised",
        ).grid(row=4,column=3)

        Button(
            self.root,
            text="VOID",
            command=self.void_item,
            bg="#8B0000",
            fg="#FFFFFF",
            highlightthickness=2,
            relief="raised",
            width=150,
            height=60
            ).grid(row=5, column=3)
        
        Button(
            self.root,
            text="VOID TXN",
            command=self.void_transaction_by_number,
            bg="#8B0000",
            fg="#FFFFFF",
            width=150,
            height=60
        ).grid(row=6, column=3)

        Button(
            self.root,
            text="X Report",
            width=150,
            height=60,
            bg="#FFEA00",
            fg="#000000",
            padx=0, pady=0,
            highlightthickness=2,
            relief="raised",
            command=self.show_x_report
        ).grid(row=5,column=7)

        Button(
            self.root,
            text="Z Report",
            width=150,
            height=60,
            bg="#8B0000",
            fg="#FFFFFF",
            padx=0, pady=0,
            highlightthickness=2,
            relief="raised",
            command=self.show_z_report
        ).grid(row=6,column=7)

        Button(
            self.root,
            text="Users",
            command=self.manage_users,
            bg="#800080",
            fg="#FFFFFF",
            highlightthickness=2,
            relief="raised",
            width=150,
            height=60,
            padx=0, pady=0
        ).grid(row=4, column=7)

        Button(     #Department 001
            self.root,
            text=DEPT001,
            command=partial(self.department,"DEPT001"),
            bg="#50C878",
            fg="#FFFFFF",
            highlightthickness=2,
            relief="raised",
            padx=0, pady=0,
            width=150,
            height=60
        ).grid(row=4, column=4, sticky="w")
    
        Button(     #Department2
            self.root,
            text=DEPT002,
            command=partial(self.department,"DEPT002"),
            bg="#50C878",
            fg="#FFFFFF",
            highlightthickness=2,
            relief="raised",
            padx=0, pady=0,
            width=150,
            height=60
        ).grid(row=5, column=4, sticky="w")

        Button(
            self.root,
            text=DEPT003,
            command=partial(self.department,"DEPT003"),
            bg="#50C878",
            fg="#FFFFFF",
            padx=0, pady=0,
            highlightthickness=2,
            relief="raised",
            width=150,
            height=60
        ).grid(row=6, column=4, sticky="w")

        Button(
            self.root,
            text=DEPT004,
            command=partial(self.department,"DEPT004"),
            bg="#50C878",
            fg="#FFFFFF",
            padx=0, pady=0,
            highlightthickness=2,
            relief="raised",
            width=150,
            height=60
        ).grid(row=7, column=4, sticky="w")

        Button(
            self.root,
            text=DEPT005,
            command=partial(self.department,"DEPT005"),
            bg="#50C878",
            fg="#FFFFFF",
            padx=0, pady=0,
            highlightthickness=2,
            relief="raised",
            width=150,
            height=60
        ).grid(row=4, column=6, sticky="w")

        Button(
            self.root,
            text=DEPT006,
            command=partial(self.department,"DEPT006"),
            bg="#50C878",
            fg="#FFFFFF",
            padx=0, pady=0,
            highlightthickness=2,
            relief="raised",
            width=150,
            height=60
        ).grid(row=5, column=6, sticky="w")

        Button(
            self.root,
            text=DEPT007,
            command=partial(self.department,"DEPT007"),
            bg="#50C878",
            fg="#FFFFFF",
            padx=0, pady=0,
            highlightthickness=2,
            relief="raised",
            width=150,
            height=60
        ).grid(row=6, column=6, sticky="w")

        Button(
            self.root,
            text=DEPT008,
            command=partial(self.department,"DEPT008"),
            bg="#50C878",
            fg="#FFFFFF",
            padx=0, pady=0,
            highlightthickness=2,
            relief="raised",
            width=150,
            height=60
        ).grid(row=7, column=6, sticky="w")

        Button(
            self.root,
            text="Logout",
            command=self.logout,
            bg="#FFA500",
            fg="#000000",
            highlightthickness=2,
            relief="raised",
            width=150,
            height=60
        ).grid(row=7, column=7)

        # Set focus to sku_entry
        self.sku_entry.focus_set()

    def update_totals(self):
        tax = self.subtotal * TAX_RATE
        total = self.subtotal + tax
        self.total_label.config(
            text=f"Subtotal: ${self.subtotal:.2f}  Tax: ${tax:.2f}  Total: ${total:.2f}"
        )

    def key_press(self,key):
        if key == "C":
            self.sku_var.set("")
        elif key == "Enter":
            self.add_item()
        else:
            self.sku_var.set(self.sku_var.get()+key)

    def add_item(self):
        sku = self.sku_var.get().strip()
        product = get_product(sku)

        if not product:
            messagebox.showerror("Error","SKU not found")
            return

        #if product["quantity_on_hand"] <= 0:
        #    messagebox.showerror("Out of Stock","No inventory available")
        #    return

        self.cart.append({
            "sku": product["sku"],
            "description": product["description"],
            "price": product["price"],
            "department": product["department"],
            "quantity": 1
        })

        self.writeDepartment(product["department"],product["price"])

        fSku = product['sku'].ljust(13)
        fDescription = product['description'].ljust(15)
        self.cart_list.insert(
            tk.END,
            f"{fSku} {fDescription} ${product['price']:8.2f}"
        )

        self.subtotal += product["price"]
        self.update_totals()
        self.sku_var.set("")
        self.sku_entry.focus_set()

    def show_x_report(self):

        CTkMessagebox(
            title="X Report",
            message=x_report(),
            font=("Courier New", 14),
            icon=None,
            width=750
        )
       

    def show_z_report(self):

        password = simpledialog.askstring(
            "Manager Authorization",
            "Enter admin password:",
            show="*"
        )

        if password is None:
            return

        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()

        cur.execute("""
        SELECT role
        FROM users
        WHERE username = 'admin'
        AND password = ?
        """, (password,))

        row = cur.fetchone()

        conn.close()

        if not row:
            messagebox.showerror(
                "Access Denied",
                "Invalid administrator password."
            )
            return

        if not messagebox.askyesno(
            "Z Report",
            "This will close out all unreported sales.\n\nContinue?"
        ):
            return

        report = z_report()

        messagebox.showinfo(
            "Z Report Complete",
            report
        )

    def writeDepartment(self,dept,price):
        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()

        
        cur.execute("""
        INSERT INTO department
        (
            Department,
            price,
            z_id
        )
        VALUES (?,?,?)
        """,
        (
            dept,
            price,
            None
        )
        )

        conn.commit()
        conn.close()
    
    

    def department(self,itemType):   

        try:
            price = float(self.sku_var.get())
        except ValueError:
            messagebox.showerror(
                "Error",
                "Enter a valid price first."
            )
            return
        
        match itemType:
            case "DEPT001": 
                cname=DEPT001
                cSku="DEPT001"   
                self.cart.append({
                    "sku": cSku,
                    "description": cname,
                    "price": price,
                    "quantity": 1
                })
                self.writeDepartment(cSku,price)
                fname=cname.ljust(15)
                fSku=cSku.ljust(13)
                self.cart_list.insert(
                tk.END,
                f"{fSku} {fname} ${price:8.2f}"
                )
            case "DEPT002":
                cname=DEPT002
                cSku="DEPT002" 
                self.cart.append({
                    "sku": cSku,
                    "description": cname,
                    "price": price,
                    "quantity": 1
                })
                self.writeDepartment(cSku,price)
                fname=cname.ljust(15)
                fSku=cSku.ljust(13)
                self.cart_list.insert(
                tk.END,
                f"{fSku} {fname} ${price:8.2f}"
                )
            case "DEPT003":
                cname=DEPT003
                cSku="DEPT003" 
                self.cart.append({
                    "sku": cSku,
                    "description": cname,
                    "price": price,
                    "quantity": 1
                })
                self.writeDepartment(cSku,price)
                fname=cname.ljust(15)
                fSku=cSku.ljust(13)
                self.cart_list.insert(
                tk.END,
                f"{fSku} {fname} ${price:8.2f}"
                )
            case "DEPT004":
                cname=DEPT004
                cSku="DEPT004" 
                self.cart.append({
                    "sku": cSku,
                    "description": cname,
                    "price": price,
                    "quantity": 1
                })
                self.writeDepartment(cSku,price)
                fname=cname.ljust(15)
                fSku=cSku.ljust(13)
                self.cart_list.insert(
                tk.END,
                f"{fSku} {fname} ${price:8.2f}"
                )
            case "DEPT005":
                cname=DEPT005
                cSku="DEPT005" 
                self.cart.append({
                    "sku": cSku,
                    "description": cname,
                    "price": price,
                    "quantity": 1
                })
                self.writeDepartment(cSku,price)
                fname=cname.ljust(15)
                fSku=cSku.ljust(13)
                self.cart_list.insert(
                tk.END,
                f"{fSku} {fname} ${price:8.2f}"
                )
            case "DEPT006":
                cname=DEPT006
                cSku="DEPT006" 
                self.cart.append({
                    "sku": cSku,
                    "description": cname,
                    "price": price,
                    "quantity": 1
                })
                self.writeDepartment(cSku,price)
                fname=cname.ljust(15)
                fSku=cSku.ljust(13)
                self.cart_list.insert(
                tk.END,
                f"{fSku} {fname} ${price:8.2f}"
                )
            case "DEPT007":
                cname=DEPT007
                cSku="DEPT007" 
                self.cart.append({
                    "sku": cSku,
                    "description": cname,
                    "price": price,
                    "quantity": 1
                })
                self.writeDepartment(cSku,price)
                fname=cname.ljust(15)
                fSku=cSku.ljust(13)
                self.cart_list.insert(
                tk.END,
                f"{fSku} {fname} ${price:8.2f}"
                )
            case "DEPT008":
                cname=DEPT008
                cSku="DEPT008" 
                self.cart.append({
                    "sku": cSku,
                    "description": cname,
                    "price": price,
                    "quantity": 1
                })
                self.writeDepartment(cSku,price)
                fname=cname.ljust(15)
                fSku=cSku.ljust(13)
                self.cart_list.insert(
                tk.END,
                f"{fSku} {fname} ${price:8.2f}"
                )

                self.sku_entry.focus_set()

        #self.cart_list.insert(
        #    tk.END,
        #    f"DEPT001 Small Pot ${price:.2f}"
        #)

        self.subtotal += price
        self.update_totals()

        self.sku_var.set("")
    
    def printReceipt(
        self,
        sale_id,
        subtotal,
        tax,
        total_due,
        cash,
        change,
        name,
        payment_type,
        check_number=None,
        card_last4=None):

        if not self.cart:
            return
        
        current_date = datetime.now()
        formatted_date = current_date.strftime("%m/%d/%Y %H:%M")

        receipt_output=[]
        
        receipt_output.append(f"{CENTER}{BOLDON}{DOUBLEHEIGHT}{COMPANY_NAME}")
        receipt_output.append(f"{COMPANY_ADDRESS}")
        receipt_output.append(f"{COMPANY_ADDRESS2}{NORMAL}")
        receipt_output.append(formatted_date.center(42))
        receipt_output.append("")

      

        for item in self.cart:
            sku=item["sku"]
            lSku=sku.ljust(13)
            description=item["description"]
            lDescription=description.ljust(15)
            price=item["price"]
            printOutput=f"{lSku}  {lDescription}       ${price:8.2f}"
            receipt_output.append(printOutput)
            #p.text(printOutput)

        receipt_output.append("                              ----------------")
        receipt_output.append("{:>37} ${:8.2f}".format("Total:",subtotal))
        receipt_output.append("{:>37} ${:8.2f}".format("Tax:",tax))    
        receipt_output.append("{:>37} ${:8.2f}".format("Total Due:",total_due))

        receipt_output.append(f"---Payment Type: {payment_type}---")
        
        if payment_type == "Cash":
            receipt_output.append("{:>37} ${:8.2f}".format(
                "Cash Tendered:", cash))

        elif payment_type == "Check":
            receipt_output.append(f"Check Number: {check_number}")

        elif payment_type == "Credit Card":
            receipt_output.append(f"Card Ending: ****{card_last4}")

        receipt_output.append("{:>37} ${:8.2f}".format("Change:",change))
        receipt_output.append("")
        receipt_output.append(f"Sale Id #{sale_id:08d} cashier: {name}"  )
        receipt_output.append("")
        receipt_output.append("Thank You For Shopping!")
        receipt_output.append("")
        
        barcodetext = f"{sale_id:08d}"

        receipt_text = "\n".join(receipt_output)

        try:
            print_report(receipt_text,barcodetext)
        except Exception as e:
            print(f"Printer Error: {e}")

    def checkout(self):

        if not self.cart:
            return

        tax = self.subtotal * TAX_RATE
        total_due = self.subtotal + tax

        win = tk.Toplevel(self.root)
        win.title("Checkout")
        win.geometry("400x450")

        tk.Label(
            win,
            text=f"Subtotal: ${self.subtotal:.2f}"
        ).pack()

        tk.Label(
            win,
            text=f"Tax: ${tax:.2f}"
        ).pack()

        tk.Label(
            win,
            text=f"Total Due: ${total_due:.2f}",
            font=("Arial",16,"bold")
        ).pack(pady=10)

        # Payment Method

        payment_type = tk.StringVar(value="Cash")

        tk.Label(
            win,
            text="Payment Method",
            font=("Arial",12,"bold")
        ).pack()

        tk.Radiobutton(
            win,
            text="Cash",
            variable=payment_type,
            value="Cash"
        ).pack(anchor="w")

        tk.Radiobutton(
            win,
            text="Check",
            variable=payment_type,
            value="Check"
        ).pack(anchor="w")

        tk.Radiobutton(
            win,
            text="Credit Card",
            variable=payment_type,
            value="Credit Card"
        ).pack(anchor="w")

        # Check Number

        tk.Label(win, text="Check Number").pack()

        check_var = tk.StringVar()

        tk.Entry(
            win,
            textvariable=check_var
        ).pack()

        # Credit Card Last 4

        tk.Label(
            win,
            text="Card Last 4 Digits"
        ).pack()

        card_var = tk.StringVar()

        tk.Entry(
            win,
            textvariable=card_var
        ).pack()

        # Cash Tendered

        tk.Label(
            win,
            text="Cash Tendered"
        ).pack()

        cash_var = tk.StringVar()

        tk.Entry(
            win,
            textvariable=cash_var,
            font=("Arial",18)
        ).pack(pady=5)

        change_lbl = tk.Label(
            win,
            text="Change: $0.00"
        )

        change_lbl.pack()

        def calc():

            try:
                cash = float(cash_var.get())

                change_lbl.config(
                    text=f"Change: ${cash - total_due:.2f}"
                )

            except ValueError:
                pass

        def complete():

            pay_type = payment_type.get()

            conn = sqlite3.connect(DB_NAME)
            cur = conn.cursor()

            cur.execute("""
                SELECT name
                FROM users
                WHERE username = ?
            """, (self.user["username"],))

            row = cur.fetchone()

            if row:
                sname = row[0]
            else:
                sname = name

            cash = 0
            change = 0
            check_number = None
            card_last4 = None

            if pay_type == "Cash":

                try:
                    cash = float(cash_var.get())

                except ValueError:
                    messagebox.showerror(
                        "Error",
                        "Enter amount tendered."
                    )
                    return

                if cash < total_due:
                    messagebox.showerror(
                        "Error",
                        "Insufficient cash."
                    )
                    return

                change = cash - total_due

            elif pay_type == "Check":

                check_number = check_var.get().strip()

                if not check_number:
                    messagebox.showerror(
                        "Error",
                        "Enter a check number."
                    )
                    return

                cash = total_due

            elif pay_type == "Credit Card":

                card_last4 = card_var.get().strip()

                if len(card_last4) != 4:
                    messagebox.showerror(
                        "Error",
                        "Enter last 4 digits."
                    )
                    return

                cash = total_due

            conn = sqlite3.connect(DB_NAME)
            cur = conn.cursor()

            user = self.user["username"]

            cur.execute("""
            INSERT INTO sales
            (
                subtotal,
                tax,
                total,
                cash_received,
                change_given,
                cashier,
                payment_type,
                check_number,
                card_last4
            )
            VALUES (?,?,?,?,?,?,?,?,?)
            """,
            (
                self.subtotal,
                tax,
                total_due,
                cash,
                change,
                user,
                pay_type,
                check_number,
                card_last4
            ))

            sale_id = cur.lastrowid

            for item in self.cart:

                cur.execute("""
                INSERT INTO sale_items
                (
                    sale_id,
                    sku,
                    description,
                    quantity,
                    price,
                    cashier
                )
                VALUES (?,?,?,?,?,?)
                """,
                (
                    sale_id,
                    item["sku"],
                    item["description"],
                    item["quantity"],
                    item["price"],
                    user
                ))

                if not item["sku"].startswith("DEPT"):

                    cur.execute("""
                    UPDATE products
                    SET quantity_on_hand =
                        quantity_on_hand - ?
                    WHERE sku = ?
                    """,
                    (
                        item["quantity"],
                        item["sku"]
                    ))

            conn.commit()
            conn.close()

            self.printReceipt(
                sale_id,
                self.subtotal,
                tax,
                total_due,
                cash,
                change,
                sname,
                pay_type,
                check_number,
                card_last4
            )

            messagebox.showinfo(
                "Sale Complete",
                f"Sale #{sale_id}\nPayment Type: {pay_type}"
            )

            self.cart.clear()
            self.cart_list.delete(0, tk.END)
            self.subtotal = 0
            self.update_totals()

            self.root.after(
                100,
                lambda: self.sku_entry.focus_set()
            )

            win.destroy()

        # Enter key support

        win.bind(
            '<Return>',
            lambda event: complete()
        )

        win.bind(
            '<KP_Enter>',
            lambda event: complete()
        )

        tk.Button(
            win,
            text="Calculate Change",
            command=calc
        ).pack(pady=5)

        tk.Button(
            win,
            text="Complete Sale",
            command=complete
        ).pack(pady=5)

if __name__ == "__main__":

    initialize_database()

    root = ctk.CTk()
    root.withdraw()

    start_login(root)

    root.mainloop()