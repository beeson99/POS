"""
Cart logic for the POS system.
Handles cart state, totals calculation, tax, and change calculation.
Independent of any UI framework.
"""
from config import TAX_RATE


class Cart:
    """Manages the current transaction's items and totals."""

    def __init__(self):
        self.items = []
        self.subtotal = 0.0

    def add_item(self, sku, description, price, quantity=1):
        """Add an item to the cart and update the subtotal."""
        self.items.append({
            "sku": sku,
            "description": description,
            "price": price,
            "quantity": quantity,
        })
        self.subtotal += price * quantity

    def remove_item(self, index):
        """Remove an item by index and update the subtotal."""
        item = self.items[index]
        self.subtotal -= item["price"] * item["quantity"]
        del self.items[index]

    def clear(self):
        """Clear all items and reset subtotal."""
        self.items.clear()
        self.subtotal = 0.0

    def calculate_totals(self):
        """Return (subtotal, tax, total) rounded to 2 decimal places."""
        subtotal = round(self.subtotal, 2)
        tax = round(subtotal * TAX_RATE, 2)
        total = round(subtotal + tax, 2)
        return subtotal, tax, total

    @staticmethod
    def calculate_change(cash, total_due):
        """Calculate change, eliminating negative zero."""
        change = round(float(cash) - float(total_due), 2)
        if change == -0.0:
            change = 0.0
        return change

    def format_cart_line(self, index):
        """Format a cart line for display: ' QY SKU           Description          $   Price'"""
        item = self.items[index]
        qty = item["quantity"]
        sku = item["sku"][:14].ljust(14)
        desc = item["description"][:41].ljust(41)
        extended = item["price"] * qty
        return f"{qty:>2} {sku} {desc}   ${extended:8.2f}"
