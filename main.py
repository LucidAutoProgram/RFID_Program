import io
from PIL import Image

import PySimpleGUI as sg

# Setting the desired width and height of image
width = 15
height = 15


def get_image_data(file, maxsize=(width, height)):
    """
    Generating image data using PIL
    """
    img = Image.open(file)
    img.thumbnail(maxsize)
    with io.BytesIO() as output:
        img.save(output, format="PNG")
        data = output.getvalue()
    return data


def create_rfid_layout(rfid_reader_number):
    """
    Generating layout for each RFID box
    """

    return [
        [sg.Image(data=get_image_data(f'images/red.png', maxsize=(width, height)), background_color='black'),
         sg.Button(rfid_reader_number, button_color='black', border_width=0, focus=False,
                   key=f'BUTTON_{rfid_reader_number}')
         ],
    ]


def launch_gui():
    """
    Function to launch the GUI panel
    """
    sg.theme('DarkGrey12')

    # Generating RFID layouts for different RFID_READERS
    rfid_reader_numbers = ['INPAC#001', 'INPAC#002', 'INPAC#003']  # Add more INPAC numbers as needed
    rfid_boxes = [sg.Frame(title='', layout=create_rfid_layout(rfid_reader_number), border_width=2, title_color='white',
                           relief=sg.RELIEF_SUNKEN, background_color='black') for rfid_reader_number in rfid_reader_numbers]

    # Creating a row to display RFID boxes horizontally
    rfid_row = rfid_boxes

    layout = [
        rfid_row,  # Adding the row of RFID boxes to main layout
        [sg.Multiline(default_text='', size=(100, 20), key='TERMINAL', autoscroll=True, background_color='black',
                      text_color='white', visible=False)],  # Initially hidden
    ]

    window = sg.Window(title="RFID Reader Dashboard ", layout=layout, margins=(10, 10), resizable=True)

    last_clicked = None  # To keep track of the last clicked button
    terminal_visible = False  # To keep track of the terminal's visibility

    while True:
        event, values = window.read()
        if event == sg.WINDOW_CLOSED:
            break
        if event.startswith('BUTTON_'):
            # Checking if the clicked button is the same as the last clicked
            if last_clicked == event:
                # If yes, toggle the visibility off
                terminal_visible = not terminal_visible  # Toggle the visibility
                window['TERMINAL'].update(visible=terminal_visible)
                if not terminal_visible:
                    last_clicked = None  # Resetting last clicked if terminal is hidden
            else:
                # If a different button is clicked, always show the terminal
                terminal_visible = True
                window['TERMINAL'].update(visible=terminal_visible)
                last_clicked = event  # Updating last clicked to the current button

    window.close()


if __name__ == '__main__':
    launch_gui()
