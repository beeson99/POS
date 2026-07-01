import tkinter as tk
from tkmacosx import Button
from tkmacosx import CircleButton
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
from PIL import Image
from escpos.exceptions import USBNotFoundError
import sys
from decimal import Decimal, ROUND_HALF_UP
import psycopg2
from psycopg2.extras import RealDictCursor

#------------------------------------------------------------------------
# Point of Sale System (POS)
# Developed by Patrick Beeson
# (C) 2026 Patrick Beeson
# Change Log:
# Date        Who          Reason
# 2026-06-23  Patrick B.   Initial Release
# 2026-06-23  Patrick B.   Added output to console.log
# 2026-06-25  Patrick B.   Updated complete() function to fix -0.00 error
# 2026-06-25. Patrick Be.  Fixed error with Cutter not working on X report
# 2026-06-25  Patrick B.   Added line to receipt if Transaction had been voided.
# 2026-06-26. Patrick B.   Fixed issue with voided items not logging correctly.
# 2026-06-28. Patrick Be.  Fixed issue with Receipt columns not lining up.
# 2026-07-01. Patrick B.   Fixed issue with Department not showing correctly on screen.
#------------------------------------------------------------------------

#sys.stdout = open("console.log", "a")
#sys.stderr = sys.stdout

# Set the following for your system.
DB_NAME = "pos.db"
COMPANY_NAME = "The Kitchen"
COMPANY_ADDRESS = "111 Main Street"
COMPANY_ADDRESS2 = "Yourtown, NY 01111"
SLOGAN="Thank You For eating with us!"
# Logo must be in the directory and be a .png file
COMPANY_LOGO="—Pngtree—kitchen store logo_21004253.png"
COMPANY_TELEPHONE="802-999-9999"
TAX_RATE = 0.06
# Set what the departments are for your buisness.
DEPT001="Food"
DEPT002="Office"
DEPT003="Printing"
DEPT004="Dept 004"
DEPT005="Dept 005"
DEPT006="Dept 006"
DEPT007="Dept 007"
DEPT008="Dept 008"

#Printer Codes for RONGTA Thermal Printers
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
    conn = psycopg2.connect(
            "host=localhost port=5432 dbname=posdb user=pos"
        )
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
        z_id INTEGER,
        voided INTEGER DEFAULT 0,
        void_date TIMESTAMP,
        voided_by TEXT
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
    CREATE TABLE IF NOT EXISTS voided_items (
        sale_item_id INTEGER PRIMARY KEY AUTOINCREMENT,
        sku TEXT,
        description TEXT,
        quantity INTEGER,
        price REAL,
        cashier TEXT
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

    conn = psycopg2.connect(
            "host=localhost port=5432 dbname=posdb user=pos"
        )
    cur = conn.cursor()

    cur.execute("""
    SELECT role
    FROM users
    WHERE username = %s
      AND password = %s
    """, (username, password))

    row = cur.fetchone()

    conn.close()

    return row

def get_product(sku):
    conn = psycopg2.connect(
            "host=localhost port=5432 dbname=posdb user=pos"
        )
    #conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM products WHERE sku=%s AND active=1", (sku,))
    row = cur.fetchone()
    conn.close()
    return row

def print_report(report_text,barcodetext):

    barcode = Code128(
        barcodetext,
        writer=ImageWriter()
        )

    barcode.save(
        "barcode",
        options={
            "module_width": 0.1,   # default ~0.2
            "module_height": 7,    # default ~15
            "quiet_zone": 1,
            "font_size": 0,        # remove text under barcode
            "text_distance": 1
        }
        )
    try:
        p = Usb(0x0fe6, 0x811e)
        p.set(align='left', width=1, height=1)

        # Image to top
        logo = Image.open(COMPANY_LOGO)

        max_width = 576

        if logo.width > max_width:
            ratio = max_width / logo.width

        logo = logo.resize(
            (
                int(logo.width * ratio),
                int(logo.height * ratio)
            ),
            Image.LANCZOS
        )

        logo.save("logo_print.png")
        
        # Replace with your Rongta USB Vendor ID and Product ID
        print (barcodetext)
        if barcodetext is not None:
            try:
                #p._raw(b'\x1b\x61\x01')   # center
                p.image("logo_print.png")
                #p._raw(b'\x1b\x61\x00')   # left
            except Exception as e:
                print(f"Logo Error: {e}")
            p.text(report_text)
            #p._raw(b'\x1b\x61\x01')
            p.image("barcode.png",center=True)
            p.text("\n\n\n")

            try:
                p.cut()
            except:
                pass

    except USBNotFoundError:
        messagebox.showwarning(
        "Printer Offline",
        "Receipt printer is not connected.\n"
        "The sale has been completed but the receipt could not be printed."
    )

    except Exception as e:
        messagebox.showerror(
        "Printer Error",
            str(e)
        )
    p.close()

def print_x_report(report_text):

    p = Usb(0x0fe6, 0x811e, profile="simple")
    p.set(align='left', width=1, height=1)
    p.text(report_text)
    p.text("\n\n\n")
    
    p._raw(b"\x1d\x56\x41\x03") 

    p.close()

def x_report():

    now = datetime.now()
    formatted_now = now.strftime("%m/%d/%Y %H:%M")

    conn = psycopg2.connect(
            "host=localhost port=5432 dbname=posdb user=pos"
        )
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
        and voided = 0
        and Department = 'DEPT001'
        """)
    dept01Count, dept01Total = cur.fetchone()

    cur.execute("""
        SElECT
            COUNT(*),
            COALESCE(SUM(price),0)
        FROM department
        WHERE z_id is NULL
        and voided = 0
        and Department = 'DEPT002'
        """)
    dept02Count, dept02Total = cur.fetchone()

    cur.execute("""
        SElECT
            COUNT(*),
            COALESCE(SUM(price),0)
        FROM department
        WHERE z_id is NULL
        and voided = 0
        and Department = 'DEPT003'
        """)
    dept03Count, dept03Total = cur.fetchone()

    cur.execute("""
        SElECT
            COUNT(*),
            COALESCE(SUM(price),0)
        FROM department
        WHERE z_id is NULL
        and voided = 0
        and Department = 'DEPT004'
        """)
    dept04Count, dept04Total = cur.fetchone()

    cur.execute("""
        SElECT
            COUNT(*),
            COALESCE(SUM(price),0)
        FROM department
        WHERE z_id is NULL
        and voided = 0
        and Department = 'DEPT005'
        """)
    dept05Count, dept05Total = cur.fetchone()

    cur.execute("""
        SElECT
            COUNT(*),
            COALESCE(SUM(price),0)
        FROM department
        WHERE z_id is NULL
        and voided = 0
        and Department = 'DEPT006'
        """)
    dept06Count, dept06Total = cur.fetchone()

    cur.execute("""
        SElECT
            COUNT(*),
            COALESCE(SUM(price),0)
        FROM department
        WHERE z_id is NULL
        and voided = 0
        and Department = 'DEPT007'
        """)
    dept07Count, dept07Total = cur.fetchone()

    cur.execute("""
        SElECT
            COUNT(*),
            COALESCE(SUM(price),0)
        FROM department
        WHERE z_id is NULL
        and voided = 0
        and Department = 'DEPT008'
        """)
    dept08Count, dept08Total = cur.fetchone()

    cur.execute("""
        SElECT
            COUNT(*),
            COALESCE(SUM(price),0)
        FROM department
        WHERE z_id is NULL
        and voided > 0
        and Department = 'DEPT001'
        """)
    dept01VoidCount, dept01VoidTotal = cur.fetchone()

    cur.execute("""
        SElECT
            COUNT(*),
            COALESCE(SUM(price),0)
        FROM department
        WHERE z_id is NULL
        and voided > 0
        and Department = 'DEPT002'
        """)
    dept02VoidCount, dept02VoidTotal = cur.fetchone()

    cur.execute("""
        SElECT
            COUNT(*),
            COALESCE(SUM(price),0)
        FROM department
        WHERE z_id is NULL
        and voided > 0
        and Department = 'DEPT003'
        """)
    dept03VoidCount, dept03VoidTotal = cur.fetchone()

    cur.execute("""
        SElECT
            COUNT(*),
            COALESCE(SUM(price),0)
        FROM department
        WHERE z_id is NULL
        and voided > 0
        and Department = 'DEPT004'
        """)
    dept04VoidCount, dept04VoidTotal = cur.fetchone()

    cur.execute("""
        SElECT
            COUNT(*),
            COALESCE(SUM(price),0)
        FROM department
        WHERE z_id is NULL
        and voided > 0
        and Department = 'DEPT005'
        """)
    dept05VoidCount, dept05VoidTotal = cur.fetchone()

    cur.execute("""
        SElECT
            COUNT(*),
            COALESCE(SUM(price),0)
        FROM department
        WHERE z_id is NULL
        and voided > 0
        and Department = 'DEPT006'
        """)
    dept06VoidCount, dept06VoidTotal = cur.fetchone()

    cur.execute("""
        SElECT
            COUNT(*),
            COALESCE(SUM(price),0)
        FROM department
        WHERE z_id is NULL
        and voided > 0
        and Department = 'DEPT007'
        """)
    dept07VoidCount, dept07VoidTotal = cur.fetchone()

    cur.execute("""
        SElECT
            COUNT(*),
            COALESCE(SUM(price),0)
        FROM department
        WHERE z_id is NULL
        and voided > 0
        and Department = 'DEPT008'
        """)
    dept08VoidCount, dept08VoidTotal = cur.fetchone()



    deptTotal = dept08Total+dept07Total+dept06Total+dept05Total+dept04Total+dept03Total+dept02Total+dept01Total
    deptCountTotal = dept08Count+dept07Count+dept06Count+dept05Count+dept04Count+dept03Count+dept02Count+dept01Count
    deptVoidedTotal = dept08VoidTotal+dept07VoidTotal+dept06VoidTotal+dept05VoidTotal+dept04VoidTotal+dept03VoidTotal+dept02VoidTotal+dept01VoidTotal
    deptVoidCountTotal = dept08VoidCount+dept07VoidCount+dept06VoidCount+dept05VoidCount+dept04VoidCount+dept03VoidCount+dept02VoidCount+dept01VoidCount

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
    report.append("Voids by Department".center(42))
    report.append("-" * 42)
    report.append(f"     Department             Count    Amount   ")
    report.append(f"DEPT001 ({DEPT001:^11}): ({dept01VoidCount:4}) ${dept01VoidTotal:8.2f}".rjust(42))
    report.append(f"DEPT002 ({DEPT002:^11}): ({dept02VoidCount:4}) ${dept02VoidTotal:8.2f}".rjust(42))
    report.append(f"DEPT003 ({DEPT003:^11}): ({dept03VoidCount:4}) ${dept03VoidTotal:8.2f}".rjust(42))
    report.append(f"DEPT004 ({DEPT004:^11}): ({dept04VoidCount:4}) ${dept04VoidTotal:8.2f}".rjust(42))
    report.append(f"DEPT005 ({DEPT005:^11}): ({dept05VoidCount:4}) ${dept05VoidTotal:8.2f}".rjust(42))
    report.append(f"DEPT006 ({DEPT006:^11}): ({dept06VoidCount:4}) ${dept06VoidTotal:8.2f}".rjust(42))
    report.append(f"DEPT007 ({DEPT007:^11}): ({dept07VoidCount:4}) ${dept07VoidTotal:8.2f}".rjust(42))
    report.append(f"DEPT008 ({DEPT008:^11}): ({dept08VoidCount:4}) ${dept08VoidTotal:8.2f}".rjust(42))
    report.append(f"Department Totals ({deptVoidCountTotal:4}) ${deptVoidedTotal:8.2f}".rjust(42))
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

    conn = psycopg2.connect(
            "host=localhost port=5432 dbname=posdb user=pos"
        )
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
        and Department = 'DEPT001'
        """)
    dept01Count, dept01Total = cur.fetchone()

    cur.execute("""
        SElECT
            COUNT(*),
            COALESCE(SUM(price),0)
        FROM department
        WHERE z_id is NULL
        and Department = 'DEPT002'
        """)
    dept02Count, dept02Total = cur.fetchone()

    cur.execute("""
        SElECT
            COUNT(*),
            COALESCE(SUM(price),0)
        FROM department
        WHERE z_id is NULL
        and Department = 'DEPT003'
        """)
    dept03Count, dept03Total = cur.fetchone()

    cur.execute("""
        SElECT
            COUNT(*),
            COALESCE(SUM(price),0)
        FROM department
        WHERE z_id is NULL
        and Department = 'DEPT004'
        """)
    dept04Count, dept04Total = cur.fetchone()

    cur.execute("""
        SElECT
            COUNT(*),
            COALESCE(SUM(price),0)
        FROM department
        WHERE z_id is NULL
        and Department = 'DEPT005'
        """)
    dept05Count, dept05Total = cur.fetchone()

    cur.execute("""
        SElECT
            COUNT(*),
            COALESCE(SUM(price),0)
        FROM department
        WHERE z_id is NULL
        and Department = 'DEPT006'
        """)
    dept06Count, dept06Total = cur.fetchone()

    cur.execute("""
        SElECT
            COUNT(*),
            COALESCE(SUM(price),0)
        FROM department
        WHERE z_id is NULL
        and Department = 'DEPT007'
        """)
    dept07Count, dept07Total = cur.fetchone()

    cur.execute("""
        SElECT
            COUNT(*),
            COALESCE(SUM(price),0)
        FROM department
        WHERE z_id is NULL
        and Department = 'DEPT008'
        """)
    dept08Count, dept08Total = cur.fetchone()

    cur.execute("""
        SElECT
            COUNT(*),
            COALESCE(SUM(price),0)
        FROM department
        WHERE z_id is NULL
        and voided > 0
        and Department = 'DEPT001'
        """)
    dept01VoidCount, dept01VoidTotal = cur.fetchone()

    cur.execute("""
        SElECT
            COUNT(*),
            COALESCE(SUM(price),0)
        FROM department
        WHERE z_id is NULL
        and voided > 0
        and Department = 'DEPT002'
        """)
    dept02VoidCount, dept02VoidTotal = cur.fetchone()

    cur.execute("""
        SElECT
            COUNT(*),
            COALESCE(SUM(price),0)
        FROM department
        WHERE z_id is NULL
        and voided > 0
        and Department = 'DEPT003'
        """)
    dept03VoidCount, dept03VoidTotal = cur.fetchone()

    cur.execute("""
        SElECT
            COUNT(*),
            COALESCE(SUM(price),0)
        FROM department
        WHERE z_id is NULL
        and voided > 0
        and Department = 'DEPT004'
        """)
    dept04VoidCount, dept04VoidTotal = cur.fetchone()

    cur.execute("""
        SElECT
            COUNT(*),
            COALESCE(SUM(price),0)
        FROM department
        WHERE z_id is NULL
        and voided > 0
        and Department = 'DEPT005'
        """)
    dept05VoidCount, dept05VoidTotal = cur.fetchone()

    cur.execute("""
        SElECT
            COUNT(*),
            COALESCE(SUM(price),0)
        FROM department
        WHERE z_id is NULL
        and voided > 0
        and Department = 'DEPT006'
        """)
    dept06VoidCount, dept06VoidTotal = cur.fetchone()

    cur.execute("""
        SElECT
            COUNT(*),
            COALESCE(SUM(price),0)
        FROM department
        WHERE z_id is NULL
        and voided > 0
        and Department = 'DEPT007'
        """)
    dept07VoidCount, dept07VoidTotal = cur.fetchone()

    cur.execute("""
        SElECT
            COUNT(*),
            COALESCE(SUM(price),0)
        FROM department
        WHERE z_id is NULL
        and voided > 0
        and Department = 'DEPT008'
        """)
    dept08VoidCount, dept08VoidTotal = cur.fetchone()


    deptTotal = dept08Total+dept07Total+dept06Total+dept05Total+dept04Total+dept03Total+dept02Total+dept01Total
    deptCountTotal = dept08Count+dept07Count+dept06Count+dept05Count+dept04Count+dept03Count+dept02Count+dept01Count
    deptVoidedTotal = dept08VoidTotal+dept07VoidTotal+dept06VoidTotal+dept05VoidTotal+dept04VoidTotal+dept03VoidTotal+dept02VoidTotal+dept01VoidTotal
    deptVoidCountTotal = dept08VoidCount+dept07VoidCount+dept06VoidCount+dept05VoidCount+dept04VoidCount+dept03VoidCount+dept02VoidCount+dept01VoidCount

    cur.execute("""
    INSERT INTO z_reports
    (
        transaction_count,
        sales_total,
        tax_total
    )
    VALUES (%s,%s,%s)
    RETURNING z_id
    """,
    (
        txns,
        total,
        tax
    ))

    z_id = cur.fetchone()[0]

    cur.execute("""
        UPDATE sales
        SET z_id = %s
        WHERE z_id IS NULL
    """,(z_id,))

    conn.commit()

    cur.execute("""
        UPDATE department
        SET z_id = %s
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
    report.append("Voids by Department".center(42))
    report.append("-" * 42)
    report.append(f"     Department             Count    Amount   ")
    report.append(f"DEPT001 ({DEPT001:^11}): ({dept01VoidCount:4}) ${dept01VoidTotal:8.2f}".rjust(42))
    report.append(f"DEPT002 ({DEPT002:^11}): ({dept02VoidCount:4}) ${dept02VoidTotal:8.2f}".rjust(42))
    report.append(f"DEPT003 ({DEPT003:^11}): ({dept03VoidCount:4}) ${dept03VoidTotal:8.2f}".rjust(42))
    report.append(f"DEPT004 ({DEPT004:^11}): ({dept04VoidCount:4}) ${dept04VoidTotal:8.2f}".rjust(42))
    report.append(f"DEPT005 ({DEPT005:^11}): ({dept05VoidCount:4}) ${dept05VoidTotal:8.2f}".rjust(42))
    report.append(f"DEPT006 ({DEPT006:^11}): ({dept06VoidCount:4}) ${dept06VoidTotal:8.2f}".rjust(42))
    report.append(f"DEPT007 ({DEPT007:^11}): ({dept07VoidCount:4}) ${dept07VoidTotal:8.2f}".rjust(42))
    report.append(f"DEPT008 ({DEPT008:^11}): ({dept08VoidCount:4}) ${dept08VoidTotal:8.2f}".rjust(42))
    report.append(f"Department Totals ({deptVoidCountTotal:4}) ${deptVoidedTotal:8.2f}".rjust(42))
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

    def calculate_change(self, cash, total_due):
        change = round(float(cash) - float(total_due), 2)

        # Remove negative zero
        if change == -0.0:
            change = 0.0

        return change

    def build_receipt_text(
        self,
        sale_id,
        items,
        subtotal,
        tax,
        total_due,
        cash,
        change,
        cashier_name,
        payment_type,
        check_number=None,
        card_last4=None,
        duplicate=False,
        voided=False
    ):

        current_date = datetime.now()
        formatted_date = current_date.strftime("%m/%d/%Y %H:%M")

        receipt = []

        receipt.append(f"{CENTER}{BOLDON}{DOUBLEHEIGHT}{COMPANY_NAME}")
        receipt.append(COMPANY_ADDRESS)
        receipt.append(COMPANY_ADDRESS2)
        receipt.append(f"{COMPANY_TELEPHONE}{NORMAL}")
        receipt.append(formatted_date.center(42))
        receipt.append("")

        if duplicate:
            receipt.append("*** DUPLICATE RECEIPT ***")
            receipt.append("")

        for item in items:

            sku = item["sku"]
            desc = item["description"]
            price = item["price"]

            receipt.append(
                f"{sku:13} {desc:<20}   ${price:8.2f}"
            )

        #receipt.append("")
        receipt.append("                              -----------------")
        receipt.append("{:>37} ${:8.2f}".format("Subtotal:", subtotal))
        receipt.append("{:>37} ${:8.2f}".format("Tax:", tax))
        receipt.append("{:>37} ${:8.2f}".format("Total Due:", total_due))

        receipt.append("")
        receipt.append(f"Payment Type: {payment_type}")

        if payment_type == "Cash":
            receipt.append(
                "{:>37} ${:8.2f}".format(
                    "Cash Tendered:",
                    cash
                )
            )

        elif payment_type == "Check":
            receipt.append(
                f"Check Number: {check_number}"
            )

        elif payment_type == "Credit Card":
            receipt.append(
                f"Card Ending: ****{card_last4}"
            )

        receipt.append(
            "{:>37} ${:8.2f}".format(
                "Change:",
                change
            )
        )
        
        if voided:
            receipt.append("")
            receipt.append("*** TRANSACTION WAS VOIDED ***")
            receipt.append("")
        
        receipt.append("")
        receipt.append(
            f"Sale Id #{sale_id:08d} cashier: {cashier_name}"
        )

        receipt.append("")
        receipt.append(SLOGAN)
        receipt.append("")

        return "\n".join(receipt)
 

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

            conn = psycopg2.connect(
                "host=localhost port=5432 dbname=posdb user=pos"
            )
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

                conn = psycopg2.connect(
                    "host=localhost port=5432 dbname=posdb user=pos"
                )
                cur = conn.cursor()

                cur.execute("""
                INSERT INTO users
                (
                    username,
                    password,
                    name,
                    role
                )
                VALUES (%s,%s,%s,%s)
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

            conn = psycopg2.connect(
                "host=localhost port=5432 dbname=posdb user=pos"
            )
            cur = conn.cursor()

            cur.execute("""
                DELETE FROM users
                WHERE username = %s
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

    def update_totals(self):

        subtotal, tax, total = self.calculate_totals()

        self.total_label.config(
            text=f"Subtotal: ${subtotal:.2f}  Tax: ${tax:.2f}  Total: ${total:.2f}"
        )

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

        conn = psycopg2.connect(
            "host=localhost port=5432 dbname=posdb user=pos"
        )
        cur = conn.cursor()

        cur.execute("""
        SELECT username
            FROM users
            WHERE password = %s
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
        WHERE sale_id = %s
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
        WHERE sale_id = %s
        """, (sale_id,))

        items = cur.fetchall()

        for sku, qty in items:

            if not sku.startswith("DEPT"):

                cur.execute("""
                UPDATE products
                SET quantity_on_hand =
                    quantity_on_hand + %s
                WHERE sku = %s
                """, (qty, sku))

        cur.execute("""
        UPDATE sales
        SET voided = 1,
            void_date = CURRENT_TIMESTAMP,
            voided_by = %s
        WHERE sale_id = %s
        """,
        (
            manager_name,
            sale_id
        ))

        # Void in Departments
        cur.execute("""
        UPDATE department
        SET voided = 1,
            void_date = CURRENT_TIMESTAMP,
            voided_by = %s
        WHERE sale_id = %s
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

        conn = psycopg2.connect(
            "host=localhost port=5432 dbname=posdb user=pos"
        )
        cur = conn.cursor()

        cur.execute("""
            SELECT name
            FROM users
            WHERE username = %s
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
        self.total_label.grid(row=3,column=1,columnspan=4)

        keypad = [
            ["7","8","9"],
            ["4","5","6"],
            ["1","2","3"],
            ["0",".","C","Enter"]
        ]
        self.root.grid_columnconfigure(0, minsize=50)

        # Seperate Fram for the Keypad.  Done to make the round buttons look better.
        keypad_frame = tk.Frame(self.root)
        keypad_frame.grid(
            row=4,
            column=0,
            rowspan=4,
            columnspan=3,
            padx=(90,0),
            pady=10,
            
            )

        for r, row in enumerate(keypad):
            for c, key in enumerate(row):
                CircleButton(
                    keypad_frame,
                    text=key,
                    width=60,
                    height=60,
                    bg="#1434A4",
                    fg="#FFFFFF",
                    bordercolor="#333333",
                    radius=30,
                    command=lambda k=key: self.key_press(k)
                ).grid(
                    row=r+4,
                    column=c+1,
                    padx=3,
                    pady=3
                )
        
        #seperate keyboard from root so things will display correctly.
        keyboard_frame = tk.Frame(self.root)
        keyboard_frame.grid(
            row=4,
            column=4,
            rowspan=4,
            columnspan=6,
            padx=(10,0),
            pady=10
            )

        Button(
            keyboard_frame,
            text="Checkout",
            command=self.checkout,
            bg="#7393B3",
            fg="#FFFFFF",
            bordercolor="#333333",
            width=150,
            height=60
        ).grid(row=4,column=3)

        Button(
            keyboard_frame,
            text="VOID",
            command=self.void_item,
            bg="#8B0000",
            fg="#FFFFFF",
            bordercolor="#333333",
            width=150,
            height=60
            ).grid(row=5, column=3)
        
        Button(
            keyboard_frame,
            text="VOID TXN",
            command=self.void_transaction_by_number,
            bg="#8B0000",
            fg="#FFFFFF",
            bordercolor="#333333",
            width=150,
            height=60
        ).grid(row=6, column=3)

        Button(
            keyboard_frame,
            text="Reprint Transaction",
            command=self.reprint_receipt,
            bg="#4682B4",
            fg="#FFFFFF",
            bordercolor="#333333",
            width=150,
            height=60
        ).grid(row=7, column=3)

        Button(
            keyboard_frame,
            text="X Report",
            width=150,
            height=60,
            bg="#FFEA00",
            fg="#000000",
            bordercolor="#333333",
            command=self.show_x_report
        ).grid(row=5,column=7)

        Button(
            keyboard_frame,
            text="Z Report",
            width=150,
            height=60,
            bg="#8B0000",
            fg="#FFFFFF",
            bordercolor="#333333",
            command=self.show_z_report
        ).grid(row=6,column=7)

        Button(
            keyboard_frame,
            text="Users",
            command=self.manage_users,
            bg="#800080",
            fg="#FFFFFF",
            bordercolor="#333333",
            width=150,
            height=60
        ).grid(row=4, column=7)

        Button(     #Department 001
            keyboard_frame,
            text=DEPT001,
            command=partial(self.department,"DEPT001"),
            bg="#50C878",
            fg="#000000",
            bordercolor="#333333",
            width=150,
            height=60
        ).grid(row=4, column=4, sticky="w")
    
        Button(     #Department2
            keyboard_frame,
            text=DEPT002,
            command=partial(self.department,"DEPT002"),
            bg="#50C878",
            fg="#000000",
            bordercolor="#333333",
            width=150,
            height=60
        ).grid(row=5, column=4, sticky="w")

        Button(
            keyboard_frame,
            text=DEPT003,
            command=partial(self.department,"DEPT003"),
            bg="#50C878",
            fg="#000000",
            bordercolor="#333333",
            width=150,
            height=60
        ).grid(row=6, column=4, sticky="w")

        Button(
            keyboard_frame,
            text=DEPT004,
            command=partial(self.department,"DEPT004"),
            bg="#50C878",
            fg="#000000",
            bordercolor="#333333",
            width=150,
            height=60
        ).grid(row=7, column=4, sticky="w")

        Button(
            keyboard_frame,
            text=DEPT005,
            command=partial(self.department,"DEPT005"),
            bg="#50C878",
            fg="#000000",
            bordercolor="#333333",
            width=150,
            height=60
        ).grid(row=4, column=6, sticky="w")

        Button(
            keyboard_frame,
            text=DEPT006,
            command=partial(self.department,"DEPT006"),
            bg="#50C878",
            fg="#000000",
            bordercolor="#333333",
            width=150,
            height=60
        ).grid(row=5, column=6, sticky="w")

        Button(
            keyboard_frame,
            text=DEPT007,
            command=partial(self.department,"DEPT007"),
            bg="#50C878",
            fg="#000000",
            bordercolor="#333333",
            width=150,
            height=60
        ).grid(row=6, column=6, sticky="w")

        Button(
            keyboard_frame,
            text=DEPT008,
            command=partial(self.department,"DEPT008"),
            bg="#50C878",
            fg="#000000",
            bordercolor="#333333",
            width=150,
            height=60
        ).grid(row=7, column=6, sticky="w")

        Button(
            keyboard_frame,
            text="Logout",
            command=self.logout,
            bg="#FFA500",
            fg="#000000",
            bordercolor="#333333",
            width=150,
            height=60
        ).grid(row=7, column=7)

        # Set focus to sku_entry
        self.sku_entry.focus_set()

    def calculate_totals(self):
        """
        Calculate subtotal, tax, and total.
        All values are rounded to two decimal places.
        """

        subtotal = round(self.subtotal, 2)
        tax = round(subtotal * TAX_RATE, 2)
        total = round(subtotal + tax, 2)

        return subtotal, tax, total

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
            "sku": product[1],
            "description": product[2],
            "price": product[4],
            "department": product[3],
            "quantity": 1
        })

        #self.writeDepartment(product[3],product[4]) #department, price
        # Moving this to checkOUt

        fSku = product[1].ljust(13) #sku
        fDescription = product[2].ljust(15) #description
        self.cart_list.insert(
            tk.END,
           # f"{fSku} {fDescription} ${product[4]:8.2f}" #price
            f"{fSku:13} {fDescription:<20}   ${product[4]:8.2f}"
        )

        self.subtotal += product[4] #price
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

        conn = psycopg2.connect(
            "host=localhost port=5432 dbname=posdb user=pos"
        )
        cur = conn.cursor()

        cur.execute("""
        SELECT role
        FROM users
        WHERE username = 'admin'
        AND password = %s
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

    def writeDepartment(self,dept,price,sale_id):
        conn = psycopg2.connect(
            "host=localhost port=5432 dbname=posdb user=pos"
        )
        cur = conn.cursor()

        
        cur.execute("""
        INSERT INTO department
        (
            sale_id,
            Department,
            price,
            z_id
        )
        VALUES (%s,%s,%s,%s)
        """,
        (
            sale_id,
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
                #self.writeDepartment(cSku,price)
                fname=cname.ljust(15)
                fSku=cSku.ljust(13)
                self.cart_list.insert(
                tk.END,
                #f"{fSku} {fname} ${price:8.2f}"
                f"{fSku:13} {fname:<20}   ${price:8.2f}"
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
                #self.writeDepartment(cSku,price)
                fname=cname.ljust(15)
                fSku=cSku.ljust(13)
                self.cart_list.insert(
                tk.END,
                #f"{fSku} {fname} ${price:8.2f}"
                f"{fSku:13} {fname:<20}   ${price:8.2f}"
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
                #self.writeDepartment(cSku,price)
                fname=cname.ljust(15)
                fSku=cSku.ljust(13)
                self.cart_list.insert(
                tk.END,
                #f"{fSku} {fname} ${price:8.2f}"
                f"{fSku:13} {fname:<20}   ${price:8.2f}"
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
                #self.writeDepartment(cSku,price)
                fname=cname.ljust(15)
                fSku=cSku.ljust(13)
                self.cart_list.insert(
                tk.END,
                #f"{fSku} {fname} ${price:8.2f}"
                f"{fSku:13} {fname:<20}   ${price:8.2f}"
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
                #self.writeDepartment(cSku,price)
                fname=cname.ljust(15)
                fSku=cSku.ljust(13)
                self.cart_list.insert(
                tk.END,
                #f"{fSku} {fname} ${price:8.2f}"
                f"{fSku:13} {fname:<20}   ${price:8.2f}"
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
                #self.writeDepartment(cSku,price)
                fname=cname.ljust(15)
                fSku=cSku.ljust(13)
                self.cart_list.insert(
                tk.END,
                #f"{fSku} {fname} ${price:8.2f}"
                f"{fSku:13} {fname:<20}   ${price:8.2f}"
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
                #self.writeDepartment(cSku,price)
                fname=cname.ljust(15)
                fSku=cSku.ljust(13)
                self.cart_list.insert(
                tk.END,
                #f"{fSku} {fname} ${price:8.2f}"
                f"{fSku:13} {fname:<20}   ${price:8.2f}"
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
                fname=cname.ljust(15)
                fSku=cSku.ljust(13)
                self.cart_list.insert(
                tk.END,
                #f"{fSku} {fname} ${price:8.2f}"
                f"{fSku:13} {fname:<20}   ${price:8.2f}"
                )

                self.sku_entry.focus_set()

        #self.cart_list.insert(
        #    tk.END,
        #    f"DEPT001 Small Pot ${price:.2f}"
        #)

        self.subtotal += price
        self.update_totals()

        self.sku_var.set("")
        
    def reprint_receipt(self):

        sale_id = simpledialog.askinteger(
            "Reprint Receipt",
            "Enter Transaction Number:"
        )

        if sale_id is None:
            return

        conn = psycopg2.connect(
            "host=localhost port=5432 dbname=posdb user=pos"
        )
        #conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        cur.execute("""
            SELECT *
            FROM sales
            WHERE sale_id = %s
        """, (sale_id,))

        sale = cur.fetchone()

        if not sale:
            conn.close()

            messagebox.showerror(
                "Error",
                "Transaction not found."
            )

            return

        cur.execute("""
            SELECT *
            FROM sales
            WHERE sale_id = %s
        """, (sale_id,))
        voidedSale=cur.fetchone()

        cur.execute("""
            SELECT *
            FROM sale_items
            WHERE sale_id = %s
            ORDER BY sale_item_id
        """, (sale_id,))

        items = []

        for row in cur.fetchall():

            items.append({
                "sku": row["sku"],
                "description": row["description"],
                "price": row["price"],
                "quantity": row["quantity"]
            })

        conn.close()

        receipt_text = self.build_receipt_text(
            sale_id=sale["sale_id"],
            items=items,
            subtotal=sale["subtotal"],
            tax=sale["tax"],
            total_due=sale["total"],
            cash=sale["cash_received"],
            change=sale["change_given"],
            cashier_name=sale["cashier"],
            payment_type=sale["payment_type"],
            check_number=sale["check_number"],
            card_last4=sale["card_last4"],
            duplicate=True,
            voided=voidedSale
        )

        print_report(
            receipt_text,
            f"{sale_id:08d}"
        )

        messagebox.showinfo(
            "Receipt Reprinted",
            f"Transaction #{sale_id}"
        )
    
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

        receipt_text = self.build_receipt_text(
            sale_id=sale_id,
            items=self.cart,
            subtotal=subtotal,
            tax=tax,
            total_due=total_due,
            cash=cash,
            change=change,
            cashier_name=name,
            payment_type=payment_type,
            check_number=check_number,
            card_last4=card_last4
        )

        print_report(
            receipt_text,
            f"{sale_id:08d}"
        )

    def checkout(self):

        if not self.cart:
            return

        subtotal, tax, total_due = self.calculate_totals()

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

                change = self.calculate_change(cash, total_due)

                change_lbl.config(
                    text=f"Change: ${change:.2f}"
                )

            except ValueError:
                change_lbl.config(
                    text="Change: $0.00"
                )

        def complete():

            pay_type = payment_type.get()

            conn = psycopg2.connect(
            "host=localhost port=5432 dbname=posdb user=pos"
        )
            cur = conn.cursor()

            cur.execute("""
                SELECT name
                FROM users
                WHERE username = %s
            """, (self.user["username"],))

            row = cur.fetchone()

            if row:
                sname = row[0]
            else:
                sname = self.user["username"]

            cash = 0
            change = 0
            check_number = None
            card_last4 = None

            if pay_type == "Cash":

                try:
                    cash = round(float(cash_var.get()), 2)

                except ValueError:
                    messagebox.showerror(
                        "Error",
                        "Enter amount tendered."
                    )
                    return
                
                #print(f"Subtotal={self.subtotal}")
                #print(f"Tax={tax}")
                #print(f"Total={total_due}")
                #print(f"Cash={cash}")

                if cash < total_due:
                    messagebox.showerror(
                        "Error",
                        "Insufficient cash."
                    )
                    return
                
                change = self.calculate_change(cash, total_due)

                # Prevent displaying -0.00
                if abs(change) < 0.005:
                    change = 0.00

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

            conn = psycopg2.connect(
            "host=localhost port=5432 dbname=posdb user=pos"
        )
            cur = conn.cursor()
            user = self.user["username"]

            try:
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
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                RETURNING sale_id
                """,
                (
                    subtotal,
                    tax,
                    total_due,
                    cash,
                    change,
                    user,
                    pay_type,
                    check_number,
                    card_last4
                ))

                sale_id = cur.fetchone()[0]
                #print("SALE ID =", sale_id)

            except Exception as e:
                print("SALES INSERT ERROR:", e)
                raise

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
                VALUES (%s,%s,%s,%s,%s,%s)
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
                        quantity_on_hand - %s
                    WHERE sku = %s
                    """,
                    (
                        item["quantity"],
                        item["sku"]
                    ))


                dept = item["sku"]
                if not item["sku"].startswith("DEPT"):
                    cur.execute("""
                    SELECT department
                    FROM products
                    WHERE sku = %s
                    """, (item["sku"],))
                    dept = cur.fetchone()[0]
                #print("Dept==",dept,sale_id)
                self.writeDepartment(dept, item["price"], sale_id)

            conn.commit()
            conn.close()

            self.printReceipt(
                sale_id,
                subtotal,
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

    #initialize_database()

    root = ctk.CTk()
    root.withdraw()

    start_login(root)

    root.mainloop()