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
                           relief=sg.RELIEF_SUNKEN, background_color='black') for rfid_reader_number in
                  rfid_reader_numbers]

    # Adding a black box to the layout
    details_box = sg.Column([
        [sg.Text('Additional Information', background_color='black', text_color='white', size=(20, 1))]],
        key='DETAILS_BOX',
        background_color='black',
        visible=False,  # Initially hidden
        pad=(0, 0),
        expand_x=True,
        expand_y=True
    )

    terminal_box = sg.Column([
        [sg.Text('RFID TERMINAL', background_color='black', text_color='white', size=(20, 1))]],
        key='TERMINAL',
        background_color='black',
        visible=False,  # Initially hidden
        pad=((0, 20), (0, 0)),
        expand_x=True,
        expand_y=True
    )

    # Creating a row to display RFID boxes horizontally
    rfid_row = rfid_boxes

    layout = [
        rfid_row,  # Adding the row of RFID boxes to main layout
        [terminal_box, details_box],
    ]

    window = sg.Window(title="RFID Reader Dashboard ", layout=layout, margins=(10, 10), resizable=True)

    last_clicked = None  # To keep track of the last clicked button

    while True:
        event, values = window.read()
        if event == sg.WINDOW_CLOSED:
            break

        elif event.startswith('BUTTON_'):
            # Checking if the clicked button is the same as the last clicked
            if last_clicked == event:
                # If yes, toggle the visibility off/on
                new_visibility = not window[
                    'TERMINAL'].visible  # Use the current visibility of terminal_box to toggle both
                window['TERMINAL'].update(visible=new_visibility)
                window['DETAILS_BOX'].update(visible=new_visibility)
                if not new_visibility:
                    last_clicked = None  # Resetting last clicked if boxes are hidden
            else:
                # If a different button is clicked, always show the boxes
                window['TERMINAL'].update(visible=True)
                window['DETAILS_BOX'].update(visible=True)
                last_clicked = event  # Updating last clicked to the current button

    window.close()


if __name__ == '__main__':
    launch_gui()
