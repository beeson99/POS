"""
POS System — Entry point.
Run this file to start the POS application.
"""
import customtkinter as ctk

from pos_ui import start_login


def main():
    root = ctk.CTk()
    root.withdraw()
    start_login(root)
    root.mainloop()


if __name__ == "__main__":
    main()
