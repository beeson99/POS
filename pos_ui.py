"""
POS System — Tkinter UI layer.
Handles window construction and user interaction only.
All business logic is delegated to the other modules.
"""
import tkinter as tk
from tkmacosx import Button, CircleButton
from tkinter import messagebox, simpledialog
from functools import partial
from datetime import datetime

import customtkinter as ctk
from CTkMessagebox import CTkMessagebox

import config
from config import (
    REGISTER_ID, DEPT001, DEPT002, DEPT003, DEPT004,
    DEPT005, DEPT006, DEPT007, DEPT008, DEPARTMENTS,
)
from cart import Cart
import auth
import database
import reports
from receipts import build_receipt_text, build_void_receipt
from printer import print_receipt, print_report, print_x_report


def center_window(window, width=None, height=None):
    """Center a tkinter window on screen."""
    window.update_idletasks()
    if width is None:
        width = window.winfo_width()
    if height is None:
        height = window.winfo_height()
    screen_width = window.winfo_screenwidth()
    screen_height = window.winfo_screenheight()
    x = (screen_width // 2) - (width // 2)
    y = (screen_height // 2) - (height // 2)
    window.geometry(f"{width}x{height}+{x}+{y}")


# ── Login Window ─────────────────────────────────────────────────────

class LoginWindow:
    """Modal login dialog."""

    def __init__(self, root):
        self.root = root
        self.user = None
        self.quantity = 1

        self.win = tk.Toplevel(root)
        self.win.title("Login to Cash Register")
        center_window(self.win, 350, 200)
        self.win.grab_set()

        root.columnconfigure(0, weight=0)
        root.rowconfigure(0, weight=0)

        tk.Label(self.win, text="Username").pack(pady=5)
        self.username = tk.Entry(self.win)
        self.username.pack()

        tk.Label(self.win, text="Password").pack(pady=5)
        self.password = tk.Entry(self.win, show="*")
        self.password.pack()

        self.username.focus_set()

        self.win.bind("<Return>", lambda event: self.login())
        self.win.bind("<KP_Enter>", lambda event: self.login())

        tk.Button(self.win, text="Login", command=self.login).pack(pady=10)

    def login(self):
        username = self.username.get()
        password = self.password.get()
        self.user = auth.login(username, password)

        if self.user:
            self.win.destroy()
        else:
            messagebox.showerror("Login Failed", "Invalid username or password")


def start_login(root):
    """Show login, then launch POS if successful."""
    login = LoginWindow(root)
    root.wait_window(login.win)

    if login.user:
        root.deiconify()
        for widget in root.winfo_children():
            widget.destroy()
        POS(root, login.user)
    else:
        root.destroy()


# ── Main POS UI ──────────────────────────────────────────────────────

class POS:
    """Main POS interface — UI only, delegates logic to modules."""

    def __init__(self, root, user):
        self.user = user
        self.root = root
        self.root.title("POS System")
        center_window(self.root, 1200, 650)
        self.quantity = 1

        self.cart = Cart()
        self.sku_var = tk.StringVar()

        self.build_ui()
        self.root.after(100, lambda: self.sku_entry.focus_set())

        self.root.bind("<Return>", lambda event: self.add_item())
        self.root.bind("<KP_Enter>", lambda event: self.add_item())

    # ── Navigation ───────────────────────────────────────────────────

    def logout(self):
        if not messagebox.askyesno("Logout", f"Logout {self.user['username']}?"):
            return
        self.cart.clear()
        self.sku_var.set("")
        for widget in self.root.winfo_children():
            widget.destroy()
        start_login(self.root)

    # ── Totals & Cart Display ────────────────────────────────────────

    def update_totals(self):
        subtotal, tax, total = self.cart.calculate_totals()
        self.total_label.config(
            text=f"Subtotal: ${subtotal:.2f}  Tax: ${tax:.2f}  Total: ${total:.2f}"
        )

    # ── Void Transaction ─────────────────────────────────────────────

    def void_transaction_by_number(self):
        sale_id = simpledialog.askinteger("Void Transaction", "Enter Transaction Number:")
        if sale_id is None:
            self.sku_entry.focus_set()
            return

        password = simpledialog.askstring("Manager Authorization", "Enter manager password:", show="*")
        if not password:
            self.sku_entry.focus_set()
            return

        manager_name = auth.verify_manager(password)
        if not manager_name:
            messagebox.showerror("Access Denied", "Manager authorization required.")
            self.sku_entry.focus_set()
            return

        sale = database.get_sale(sale_id)
        if not sale:
            messagebox.showerror("Error", "Transaction not found.")
            self.sku_entry.focus_set()
            return

        if sale[12] == 1:  # voided column
            messagebox.showerror("Error", "Transaction already voided.")
            self.sku_entry.focus_set()
            return

        if not messagebox.askyesno("Confirm Void", f"Void transaction #{sale_id}?"):
            return

        database.void_sale(sale_id, manager_name)

        receipt = build_void_receipt(sale_id, manager_name)
        print_x_report(receipt)

        messagebox.showinfo("Transaction Voided", f"Transaction #{sale_id} has been voided.")
        self.sku_entry.focus_set()

    # ── Void Item ────────────────────────────────────────────────────

    def void_item(self):
        selection = self.cart_list.curselection()
        if not selection:
            messagebox.showwarning("Void", "Select an item first.")
            self.sku_entry.focus_set()
            return

        index = selection[0]
        item = self.cart.items[index]

        if not messagebox.askyesno("Void Item", f"Void {item['description']}?"):
            return

        self.cart.remove_item(index)
        self.cart_list.delete(index)
        self.update_totals()
        self.sku_entry.focus_set()

    # ── Quantity ─────────────────────────────────────────────────────

    def set_quantity(self):
        try:
            qty = int(self.sku_var.get())
            if qty <= 0:
                raise ValueError
            self.quantity = qty
            self.sku_var.set("")
            self.total_label.config(text=f"Quantity Mode: {qty}")
            self.sku_entry.focus_set()
        except ValueError:
            messagebox.showerror("Quantity", "Enter a valid quantity first.")
            self.quantity = 1
            self.sku_entry.focus_set()

    # ── Add Item ─────────────────────────────────────────────────────

    def key_press(self, key):
        if key == "C":
            self.sku_var.set("")
        elif key == "Enter":
            self.add_item()
        elif key == "@":
            self.set_quantity()
        else:
            self.sku_var.set(self.sku_var.get() + key)

    def add_item(self):
        sku = self.sku_var.get().strip()
        product = database.get_product(sku)

        if not product:
            messagebox.showerror("Error", "SKU not found")
            return

        qty = self.quantity
        self.cart.add_item(
            sku=product[1],        # sku
            description=product[2], # description
            price=product[4],       # price
            quantity=qty,
        )

        self.cart_list.insert(tk.END, self.cart.format_cart_line(len(self.cart.items) - 1))
        self.update_totals()
        self.sku_var.set("")
        self.sku_entry.focus_set()
        self.quantity = 1

    # ── Department Sales ─────────────────────────────────────────────

    def department(self, dept_code):
        """Add a department sale (price entered on keypad, no SKU lookup)."""
        try:
            price = float(self.sku_var.get())
        except ValueError:
            messagebox.showerror("Error", "Enter a valid price first.")
            return

        qty = self.quantity
        dept_name = DEPARTMENTS.get(dept_code, dept_code)

        self.cart.add_item(
            sku=dept_code,
            description=dept_name,
            price=price,
            quantity=qty,
        )

        self.cart_list.insert(tk.END, self.cart.format_cart_line(len(self.cart.items) - 1))
        self.subtotal_update()
        self.sku_var.set("")
        self.quantity = 1

    def subtotal_update(self):
        """Wrapper for update_totals after department add."""
        self.update_totals()

    # ── Reprint Receipt ──────────────────────────────────────────────

    def reprint_receipt(self):
        sale_id = simpledialog.askinteger("Reprint Receipt", "Enter Transaction Number:")
        if sale_id is None:
            return

        sale = database.get_sale(sale_id)
        if not sale:
            messagebox.showerror("Error", "Transaction not found.")
            return

        voided = database.is_sale_voided(sale_id)
        items = database.get_sale_items(sale_id)

        receipt_text = build_receipt_text(
            sale_id=sale[0],    # sale_id
            items=items,
            subtotal=sale[2],   # subtotal
            tax=sale[3],        # tax
            total_due=sale[4],  # total
            cash=sale[5],       # cash_received
            change=sale[6],     # change_given
            cashier_name=sale[7], # cashier
            payment_type=sale[8], # payment_type
            check_number=sale[9],  # check_number
            card_last4=sale[10],  # card_last4
            duplicate=True,
            voided=voided,
        )

        try:
            print_report(receipt_text, f"{sale_id:08d}")
        except Exception as e:
            messagebox.showwarning("Printer Offline", str(e))

        messagebox.showinfo("Reprint", "Receipt reprinted.")

    # ── Reports ─────────────────────────────────────────────────────

    def show_x_report(self):
        CTkMessagebox(
            title="X Report",
            message=reports.x_report(),
            font=("Courier New", 14),
            icon=None,
            width=750,
        )

    def show_z_report(self):
        password = simpledialog.askstring("Manager Authorization", "Enter admin password:", show="*")
        if password is None:
            return

        if not auth.verify_admin(password):
            messagebox.showerror("Access Denied", "Invalid administrator password.")
            return

        if not messagebox.askyesno("Z Report", "This will close out all unreported sales.\n\nContinue?"):
            return

        report = reports.z_report()
        messagebox.showinfo("Z Report Complete", report)

    # ── User Management ─────────────────────────────────────────────

    def manage_users(self):
        if not auth.is_manager(self.user):
            messagebox.showerror("Access Denied", "Manager access required.")
            return

        win = tk.Toplevel(self.root)
        win.title("User Maintenance")
        center_window(win, 500, 500)

        tk.Label(win, text="Current Users", font=("Arial", 14, "bold")).pack()

        user_list = tk.Listbox(win, width=40, height=10)
        user_list.pack(pady=10)

        def load_users():
            user_list.delete(0, tk.END)
            for username, name, role in auth.get_all_users():
                user_list.insert(tk.END, f"{username} {name} ({role})")

        load_users()

        tk.Label(win, text="Username").pack()
        username_var = tk.StringVar()
        tk.Entry(win, textvariable=username_var).pack()

        tk.Label(win, text="Name").pack()
        name_var = tk.StringVar()
        tk.Entry(win, textvariable=name_var).pack()

        tk.Label(win, text="Password").pack()
        password_var = tk.StringVar()
        tk.Entry(win, textvariable=password_var, show="*").pack()

        tk.Label(win, text="Role").pack()
        role_var = tk.StringVar(value="cashier")
        tk.OptionMenu(win, role_var, "cashier", "manager").pack()

        def add_user():
            username = username_var.get().strip()
            password = password_var.get().strip()
            name = name_var.get().strip()
            role = role_var.get()

            if not username or not password:
                messagebox.showerror("Error", "Username and password required.")
                return

            try:
                auth.create_user(username, password, name, role)
                username_var.set("")
                password_var.set("")
                load_users()
            except Exception:
                messagebox.showerror("Error", "User already exists.")

        def delete_user():
            selection = user_list.curselection()
            if not selection:
                return

            username = user_list.get(selection[0]).split(" ")[0]

            if username == "admin":
                messagebox.showerror("Error", "Cannot delete admin.")
                return

            if not messagebox.askyesno("Delete User", f"Delete {username}?"):
                return

            auth.remove_user(username)
            load_users()

        tk.Button(win, text="Add User", command=add_user,
                  bg="#FFFFFF", fg="#50C878").pack(pady=5)
        tk.Button(win, text="Delete User", command=delete_user,
                  bg="#FFFFFF", fg="#8B0000").pack(pady=5)

    # ── Checkout ─────────────────────────────────────────────────────

    def checkout(self):
        subtotal, tax, total_due = self.cart.calculate_totals()

        win = tk.Toplevel(self.root)
        win.title("Checkout")
        center_window(win, 400, 450)

        tk.Label(win, text=f"Subtotal: ${subtotal:.2f}").pack()
        tk.Label(win, text=f"Tax: ${tax:.2f}").pack()
        tk.Label(win, text=f"Total Due: ${total_due:.2f}", font=("Arial", 16, "bold")).pack(pady=10)

        payment_type = tk.StringVar(value="Cash")
        tk.Label(win, text="Payment Method", font=("Arial", 12, "bold")).pack()
        tk.Radiobutton(win, text="Cash", variable=payment_type, value="Cash").pack(anchor="w")
        tk.Radiobutton(win, text="Check", variable=payment_type, value="Check").pack(anchor="w")
        tk.Radiobutton(win, text="Credit Card", variable=payment_type, value="Credit Card").pack(anchor="w")

        tk.Label(win, text="Check Number").pack()
        check_var = tk.StringVar()
        tk.Entry(win, textvariable=check_var).pack()

        tk.Label(win, text="Card Last 4 Digits").pack()
        card_var = tk.StringVar()
        tk.Entry(win, textvariable=card_var).pack()

        tk.Label(win, text="Cash Tendered").pack()
        cash_var = tk.StringVar()
        tk.Entry(win, textvariable=cash_var, font=("Arial", 18)).pack(pady=5)

        change_lbl = tk.Label(win, text="Change: $0.00")
        change_lbl.pack()

        def calc():
            try:
                cash = float(cash_var.get())
                change = Cart.calculate_change(cash, total_due)
                change_lbl.config(text=f"Change: ${change:.2f}")
            except ValueError:
                change_lbl.config(text="Change: $0.00")

        def complete():
            pay_type = payment_type.get()
            sname = auth.get_display_name(self.user["username"])
            user = self.user["username"]

            cash = 0
            change = 0
            check_number = None
            card_last4 = None

            if pay_type == "Cash":
                try:
                    cash = round(float(cash_var.get()), 2)
                except ValueError:
                    messagebox.showerror("Error", "Enter amount tendered.")
                    return

                if cash < total_due:
                    messagebox.showerror("Error", "Insufficient cash.")
                    return

                change = Cart.calculate_change(cash, total_due)
                if abs(change) < 0.005:
                    change = 0.00

            elif pay_type == "Check":
                check_number = check_var.get().strip()
                if not check_number:
                    messagebox.showerror("Error", "Enter a check number.")
                    return
                cash = total_due

            elif pay_type == "Credit Card":
                card_last4 = card_var.get().strip()
                if len(card_last4) != 4:
                    messagebox.showerror("Error", "Enter last 4 digits.")
                    return
                cash = total_due

            # Insert the sale
            sale_id = database.insert_sale(
                subtotal, tax, total_due, cash, change,
                user, pay_type, check_number, card_last4, REGISTER_ID
            )

            # Insert sale items, decrement inventory, write department records
            for item in self.cart.items:
                database.insert_sale_item(
                    sale_id, item["sku"], item["description"],
                    item["quantity"], item["price"], user
                )

                if not item["sku"].startswith("DEPT"):
                    database.decrement_inventory(item["sku"], item["quantity"])

                    # Look up the product's department
                    dept = database.get_product_department(item["sku"])
                else:
                    dept = item["sku"]

                database.insert_department(sale_id, dept, item["price"], item["quantity"], REGISTER_ID)

            # Print receipt
            receipt_text = build_receipt_text(
                sale_id=sale_id,
                items=self.cart.items,
                subtotal=subtotal,
                tax=tax,
                total_due=total_due,
                cash=cash,
                change=change,
                cashier_name=sname,
                payment_type=pay_type,
                check_number=check_number,
                card_last4=card_last4,
            )

            try:
                print_receipt(receipt_text, f"{sale_id:08d}")
            except Exception as e:
                messagebox.showwarning("Printer Offline", str(e))

            messagebox.showinfo("Sale Complete", f"Sale #{sale_id}\nPayment Type: {pay_type}")

            self.cart.clear()
            self.cart_list.delete(0, tk.END)
            self.update_totals()
            self.root.after(100, lambda: self.sku_entry.focus_set())
            win.destroy()

        win.bind("<Return>", lambda event: complete())
        win.bind("<KP_Enter>", lambda event: complete())

        tk.Button(win, text="Calculate Change", command=calc).pack(pady=5)
        tk.Button(win, text="Complete Sale", command=complete).pack(pady=5)

    # ── UI Construction ──────────────────────────────────────────────

    def build_ui(self):
        sname = auth.get_display_name(self.user["username"])

        tk.Label(
            self.root,
            text=f"User: {sname}        Register: {REGISTER_ID}",
            font=("Arial", 16),
        ).grid(row=0, column=6)

        tk.Label(self.root, text="SKU/Price Entry", font=("Arial", 16)).grid(row=0, column=2)

        self.sku_entry = tk.Entry(self.root, textvariable=self.sku_var, font=("Arial", 20))
        self.sku_entry.grid(row=1, column=1, columnspan=4, sticky="ew")
        self.sku_entry.focus_set()

        self.cart_list = tk.Listbox(self.root, width=80, height=15, font=("Courier", 12))
        self.cart_list.grid(row=2, column=1, columnspan=4)

        self.total_label = tk.Label(
            self.root,
            text="Subtotal: $0.00  Tax: $0.00  Total: $0.00",
            font=("Arial", 18, "bold"),
        )
        self.total_label.grid(row=3, column=1, columnspan=4)

        # Keypad
        keypad = [
            ["7", "8", "9"],
            ["4", "5", "6"],
            ["1", "2", "3", "@"],
            ["0", ".", "C", "Enter"],
        ]
        self.root.grid_columnconfigure(0, minsize=50)

        keypad_frame = tk.Frame(self.root)
        keypad_frame.grid(row=4, column=0, rowspan=4, columnspan=3, padx=(90, 0), pady=10)

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
                    command=lambda k=key: self.key_press(k),
                ).grid(row=r + 4, column=c + 1, padx=3, pady=3)

        # Action buttons
        keyboard_frame = tk.Frame(self.root)
        keyboard_frame.grid(row=4, column=4, rowspan=4, columnspan=6, padx=(10, 0), pady=10)

        Button(keyboard_frame, text="Checkout", command=self.checkout,
               bg="#7393B3", fg="#FFFFFF", bordercolor="#333333",
               width=150, height=60).grid(row=4, column=3)

        Button(keyboard_frame, text="VOID", command=self.void_item,
               bg="#8B0000", fg="#FFFFFF", bordercolor="#333333",
               width=150, height=60).grid(row=5, column=3)

        Button(keyboard_frame, text="VOID TXN", command=self.void_transaction_by_number,
               bg="#8B0000", fg="#FFFFFF", bordercolor="#333333",
               width=150, height=60).grid(row=6, column=3)

        Button(keyboard_frame, text="Reprint Transaction", command=self.reprint_receipt,
               bg="#4682B4", fg="#FFFFFF", bordercolor="#333333",
               width=150, height=60).grid(row=7, column=3)

        Button(keyboard_frame, text="X Report", command=self.show_x_report,
               bg="#FFEA00", fg="#000000", bordercolor="#333333",
               width=150, height=60).grid(row=5, column=7)

        Button(keyboard_frame, text="Z Report", command=self.show_z_report,
               bg="#8B0000", fg="#FFFFFF", bordercolor="#333333",
               width=150, height=60).grid(row=6, column=7)

        Button(keyboard_frame, text="Users", command=self.manage_users,
               bg="#800080", fg="#FFFFFF", bordercolor="#333333",
               width=150, height=60).grid(row=4, column=7)

        # Department buttons
        dept_layout = [
            (DEPT001, "DEPT001", 4, 4),
            (DEPT002, "DEPT002", 5, 4),
            (DEPT003, "DEPT003", 6, 4),
            (DEPT004, "DEPT004", 7, 4),
            (DEPT005, "DEPT005", 4, 6),
            (DEPT006, "DEPT006", 5, 6),
            (DEPT007, "DEPT007", 6, 6),
            (DEPT008, "DEPT008", 7, 6),
        ]
        for label, dept_code, r, c in dept_layout:
            Button(
                keyboard_frame,
                text=label,
                command=partial(self.department, dept_code),
                bg="#50C878",
                fg="#000000",
                bordercolor="#333333",
                width=150,
                height=60,
            ).grid(row=r, column=c, sticky="w")

        Button(keyboard_frame, text="Logout", command=self.logout,
               bg="#FFA500", fg="#000000", bordercolor="#333333",
               width=150, height=60).grid(row=7, column=7)

        self.sku_entry.focus_set()
