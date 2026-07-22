from nicegui import ui

cart = []

subtotal_label = None
cart_table = None

def update_totals():
    subtotal = sum(
        item['qty'] * item['price']
        for item in cart
    )

    tax = subtotal * 0.06
    total = subtotal + tax

    subtotal_label.set_text(
        f'Subtotal: ${subtotal:.2f}   '
        f'Tax: ${tax:.2f}   '
        f'Total: ${total:.2f}'
    )

def add_item():

    sku = sku_input.value

    # Replace with PostgreSQL lookup
    cart.append({
        'sku': sku,
        'description': 'Coffee',
        'qty': 1,
        'price': 2.50
    })

    cart_table.rows = cart
    cart_table.update()

    sku_input.value = ''

    update_totals()

def keypad_press(key):

    if key == 'C':
        sku_input.value = ''

    elif key == 'Enter':
        add_item()

    else:
        sku_input.value += key


ui.page_title('POS System')

with ui.column().classes('w-full'):

    ui.label(
        'The Kitchen POS'
    ).classes(
        'text-3xl font-bold'
    )

    with ui.row().classes('w-full'):

        sku_input = ui.input(
            label='SKU / Price Entry'
        ).classes('w-96')

        ui.button(
            'Add Item',
            on_click=add_item
        )

    cart_table = ui.table(
        columns=[
            {
                'name':'sku',
                'label':'SKU',
                'field':'sku'
            },
            {
                'name':'description',
                'label':'Description',
                'field':'description'
            },
            {
                'name':'qty',
                'label':'Qty',
                'field':'qty'
            },
            {
                'name':'price',
                'label':'Price',
                'field':'price'
            }
        ],
        rows=[]
    ).classes('w-full')

    subtotal_label = ui.label(
        'Subtotal: $0.00  Tax: $0.00  Total: $0.00'
    ).classes(
        'text-xl font-bold'
    )

    with ui.row():

        # Keypad
        with ui.card():

            ui.label('Keypad')

            with ui.grid(columns=4):

                for key in [
                    '7','8','9',' ',
                    '4','5','6',' ',
                    '1','2','3','@'
                    '0','.','C','Enter'
                ]:

                    ui.button(
                        key,
                        on_click=lambda k=key:
                        keypad_press(k)
                    ).classes(
                        'w-20 h-20 text-xl'
                    )

        # Departments
        with ui.card():

            ui.label('Departments')

            departments = [
                'Food',
                'Office',
                'Printing',
                'Dept004',
                'Dept005',
                'Dept006',
                'Dept007',
                'Dept008'
            ]

            for dept in departments:

                ui.button(
                    dept
                ).classes(
                    'w-48'
                )

        # Actions
        with ui.card():

            ui.label('Actions')

            ui.button(
                'Checkout',
                color='positive'
            ).classes('w-48')

            ui.button(
                'Void Item',
                color='negative'
            ).classes('w-48')

            ui.button(
                'Void Transaction',
                color='negative'
            ).classes('w-48')

            ui.button(
                'Reprint Receipt'
            ).classes('w-48')

            ui.button(
                'X Report'
            ).classes('w-48')

            ui.button(
                'Z Report'
            ).classes('w-48')

            ui.button(
                'Users'
            ).classes('w-48')

            ui.button(
                'Logout',
                color='warning'
            ).classes('w-48')

ui.run(
    title='POS System',
    reload=False
)