"""
Receipt text building for the POS system.
Constructs the formatted text string that gets sent to the thermal printer.
"""
from datetime import datetime

from config import (
    COMPANY_NAME, COMPANY_ADDRESS, COMPANY_ADDRESS2,
    COMPANY_TELEPHONE, SLOGAN, REGISTER_NAME,
    BOLDON, BOLDOFF, DOUBLEHEIGHT, NORMAL, CENTER,
)


def build_receipt_text(sale_id, items, subtotal, tax, total_due,
                       cash, change, cashier_name, payment_type,
                       check_number=None, card_last4=None,
                       duplicate=False, voided=False):
    """
    Build a receipt as a formatted text string.
    Returns the full receipt text ready for the printer.
    """
    current_date = datetime.now()
    formatted_date = current_date.strftime("%m/%d/%Y %H:%M")

    receipt = []

    # Header
    receipt.append(f"{CENTER}{BOLDON}{DOUBLEHEIGHT}{COMPANY_NAME}")
    receipt.append(COMPANY_ADDRESS)
    receipt.append(COMPANY_ADDRESS2)
    receipt.append(f"{COMPANY_TELEPHONE}{NORMAL}")
    receipt.append(formatted_date.center(42))
    receipt.append("")

    if duplicate:
        receipt.append("*** DUPLICATE RECEIPT ***")
        receipt.append("")

    # Items
    receipt.append(f"{' QY':>2} {'SKU':14} {'Name':20} {'Price':8}")
    receipt.append("-" * 48)
    for item in items:
        sku = item["sku"]
        desc = item["description"]
        qty = int(item["quantity"])
        price = float(item["price"])
        extended = qty * price
        receipt.append(
            f"{qty:>2} {sku[:14]:14} {desc[:19]:19} ${extended:7.2f}"
        )

    # Totals
    receipt.append("                              -----------------")
    receipt.append("{:>37} ${:8.2f}".format("Subtotal:", subtotal))
    receipt.append("{:>37} ${:8.2f}".format("Tax:", tax))
    receipt.append("{:>37} ${:8.2f}".format("Total Due:", total_due))

    # Payment
    receipt.append("")
    receipt.append(f"Payment Type: {payment_type}")

    if payment_type == "Cash":
        receipt.append("{:>37} ${:8.2f}".format("Cash Tendered:", cash))
    elif payment_type == "Check":
        receipt.append(f"Check Number: {check_number}")
    elif payment_type == "Credit Card":
        receipt.append(f"Card Ending: ****{card_last4}")

    receipt.append("{:>37} ${:8.2f}".format("Change:", change))

    if voided:
        receipt.append("")
        receipt.append("*** TRANSACTION WAS VOIDED ***")
        receipt.append("")

    # Footer
    receipt.append("")
    receipt.append(f"{REGISTER_NAME} Sale Id #{sale_id:08d} cashier: {cashier_name}")
    receipt.append("")
    receipt.append("")
    receipt.append(SLOGAN)
    receipt.append("")

    return "\n".join(receipt)


def build_void_receipt(sale_id, manager_name):
    """Build a void receipt text string."""
    return f"""
    ******* VOID RECEIPT ********

        Transaction #: {sale_id}

        Voided By: {manager_name}

        Date: {datetime.now():%m/%d/%Y %H:%M}

    *****************************
    """
