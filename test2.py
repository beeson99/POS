from nicegui import ui

with ui.button_group().props('rounded'):
    ui.button('One')
    ui.button('Two')
    ui.button('Three')
with ui.button_group().props('push glossy'):
    ui.button('One', color='red').props('push')
    ui.button('Two', color='orange').props('push text-color=black')
    ui.button('Three', color='yellow').props('push text-color=black')
with ui.button_group().props('outline'):
    ui.button('One').props('outline')
    ui.button('Two').props('outline')
    ui.button('Three').props('outline')

ui.run()