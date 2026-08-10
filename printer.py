"""
Thermal printer functions for the POS system.
Handles receipt printing, barcode generation, and report printing
via ESC/POS commands to a RONGTA USB printer.
"""
import barcode
from barcode.writer import ImageWriter
from PIL import Image
from escpos.printer import Usb
from escpos.exceptions import USBNotFoundError

from config import COMPANY_LOGO

# USB Vendor/Product IDs for the RONGTA thermal printer
USB_VENDOR = 0x0fe6
USB_PRODUCT = 0x811e


def _resize_logo(max_width=576):
    """Load and resize the company logo to fit the printer width."""
    logo = Image.open(COMPANY_LOGO)
    if logo.width > max_width:
        ratio = max_width / logo.width
        logo = logo.resize(
            (int(logo.width * ratio), int(logo.height * ratio)),
            Image.LANCZOS,
        )
    logo.save("logo_print.png")


def generate_barcode(barcodetext):
    """Generate a Code128 barcode PNG and save it as 'barcode.png'."""
    code128_class = barcode.get_barcode_class("code128")
    barcode_image = code128_class(barcodetext, writer=ImageWriter())
    barcode_image.save(
        "barcode",
        options={
            "module_width": 0.1,
            "module_height": 7,
            "quiet_zone": 1,
            "font_size": 0,
            "text_distance": 1,
        },
    )


def print_receipt(report_text, barcodetext):
    """
    Print a receipt with logo, text, and barcode to the thermal printer.
    Raises USBNotFoundError if the printer is offline.
    """
    generate_barcode(barcodetext)

    try:
        _resize_logo()
    except Exception as e:
        print(f"Logo Error: {e}")

    try:
        p = Usb(USB_VENDOR, USB_PRODUCT)
        p.set(align="left", width=1, height=1)

        try:
            p.image("logo_print.png")
        except Exception as e:
            print(f"Logo Error: {e}")

        p.text(report_text)
        p.image("barcode.png", center=True)
        p.text("\n\n\n")

        try:
            p.cut()
        except Exception:
            pass

    except USBNotFoundError:
        raise USBNotFoundError(
            "Receipt printer is not connected. "
            "The sale has been completed but the receipt could not be printed."
        )
    except Exception as e:
        raise
    finally:
        try:
            p.close()
        except Exception:
            pass


def print_report(report_text, barcodetext=None):
    """
    Print a receipt with optional barcode.
    Falls back gracefully when the printer is offline.
    """
    if barcodetext:
        generate_barcode(barcodetext)

    try:
        _resize_logo()
    except Exception as e:
        print(f"Logo Error: {e}")

    p = None
    try:
        p = Usb(USB_VENDOR, USB_PRODUCT)
        p.set(align="left", width=1, height=1)

        if barcodetext is not None:
            try:
                p.image("logo_print.png")
            except Exception as e:
                print(f"Logo Error: {e}")

        p.text(report_text)

        if barcodetext is not None:
            p.image("barcode.png", center=True)

        p.text("\n\n\n")

        try:
            p.cut()
        except Exception:
            pass

    except USBNotFoundError:
        print("Printer offline — report could not be printed.")
    except Exception as e:
        print(f"Printer Error: {e}")
    finally:
        if p:
            try:
                p.close()
            except Exception:
                pass


def print_x_report(report_text):
    """Print an X or Z report to the thermal printer (with paper cut)."""
    p = None
    try:
        p = Usb(USB_VENDOR, USB_PRODUCT, profile="simple")
        p.set(align="left", width=1, height=1)
        p.text(report_text)
        p.text("\n\n\n")
        p._raw(b"\x1d\x56\x41\x03")  # cut
    except Exception as e:
        print(f"Printer Error: {e}")
    finally:
        if p:
            try:
                p.close()
            except Exception:
                pass
