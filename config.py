"""
Configuration for the POS system.
Loads register-specific settings from config.json and exposes
company info, tax rate, department names, and printer escape codes.
"""
import json
import os

# ── Register config (per-register, loaded from config.json) ──────────
#_config_path = os.path.join(os.path.dirname(__file__), "config.json")

_config_path = os.path.join(os.getcwd(), "config.json")

print(_config_path)

with open(_config_path) as f:
    _config = json.load(f)

REGISTER_ID = _config["register_id"]
REGISTER_NAME = _config["register_name"]

# ── Company settings ─────────────────────────────────────────────────
COMPANY_NAME = "The Kitchen"
COMPANY_ADDRESS = "111 Main Street"
COMPANY_ADDRESS2 = "Yourtown, NY 01111"
SLOGAN = "Thank You for dining with us!"
COMPANY_TELEPHONE = "802-999-9999"
TAX_RATE = 0.06

# Logo must be in the project directory and be a .png file
COMPANY_LOGO = os.path.join(os.path.dirname(__file__), "..", "—Pngtree—kitchen store logo_21004253.png")

# ── Departments ───────────────────────────────────────────────────────
DEPT001 = "Food"
DEPT002 = "Office"
DEPT003 = "Printing"
DEPT004 = "Dept 004"
DEPT005 = "Dept 005"
DEPT006 = "Dept 006"
DEPT007 = "Dept 007"
DEPT008 = "Dept 008"

# Department lookup for convenience
DEPARTMENTS = {
    "DEPT001": DEPT001,
    "DEPT002": DEPT002,
    "DEPT003": DEPT003,
    "DEPT004": DEPT004,
    "DEPT005": DEPT005,
    "DEPT006": DEPT006,
    "DEPT007": DEPT007,
    "DEPT008": DEPT008,
}

# ── Database ──────────────────────────────────────────────────────────
DB_HOST = "localhost"
DB_PORT = 5432
DB_NAME = "posdb"
DB_USER = "pos"

# ── Printer escape codes (RONGTA Thermal Printer) ────────────────────
FONTA = "\x1b\x4d\x00"
FONTB = "\x1b\x4d\x01"
BOLDON = "\x1b\x45\x01"
BOLDOFF = "\x1b\x45\x00"
DOUBLEWIDTH = "\x1d\x21\x10"
DOUBLEHEIGHT = "\x1d\x21\x01"
DOUBLEWIDTHHEIGHT = "\x1d\x21\x11"
UNDERLINE = "\x1b\x2d\x01"
NORMAL = "\x1d\x21\x00"
CENTER = "\x1b\x61\x01"
