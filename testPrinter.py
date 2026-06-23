import asyncio
from bleak import BleakClient

# Replace with your printer's BLE MAC address
PRINTER_MAC_ADDRESS = "DC:0D:51:9B:6E:D7"

# Standard ESC/POS commands
INIT_PRINTER = b'\x1b\x40'
TEXT_ALIGN_CENTER = b'\x1b\x61\x01'
TEXT_ALIGN_LEFT = b'\x1b\x61\x00'
FONT_NORMAL = b'\x1d\x21\x00'
FONT_LARGE = b'\x1d\x21\x11'
CUT_PAPER = b'\x1d\x56\x41'

async def print_receipt():
    print("Connecting to printer...")
    async with BleakClient(PRINTER_MAC_ADDRESS) as client:
        if client.is_connected:
            print("Connected!")
            
            # 1. Initialize printer
            await client.write_gatt_char(1, INIT_PRINTER)
            
            # 2. Print large centered text
            await client.write_gatt_char(1, TEXT_ALIGN_CENTER + FONT_LARGE)
            await client.write_gatt_char(1, b"Hello, Python!\n\n")
            
            # 3. Print smaller left-aligned text
            await client.write_gatt_char(1, TEXT_ALIGN_LEFT + FONT_NORMAL)
            await client.write_gatt_char(1, b"This receipt was printed\nvia Bluetooth on a Mac!\n\n")
            
            # 4. Feed and cut paper
            await client.write_gatt_char(1, b'\x0c' + CUT_PAPER)
            
            print("Print job sent.")

# Run the async loop
if __name__ == "__main__":
    asyncio.run(print_receipt())