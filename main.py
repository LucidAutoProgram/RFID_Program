import concurrent
import io
from PIL import Image
from func import rfid_connectivity_checker, DatabaseOperations
import PySimpleGUI as sg
import eventlet
from concurrent.futures import ThreadPoolExecutor

eventlet.monkey_patch()

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


def create_rfid_layout(ip, status_color):
    """
        Generating layout for each RFID box
    """
    return [
        [sg.Image(data=get_image_data(f'images/{status_color}.png', maxsize=(width, height)), background_color='black',
                  key=f'IMAGE_{ip}'),
         sg.Button(ip, button_color='black', border_width=0, focus=False,
                   key=f'BUTTON_{ip}')
         ],
    ]


def update_rfid_status(window, ip_addresses):
    """
    Function to update the RFID status for all IP addresses at once using ThreadPoolExecutor.
    """

    def check_and_update(ip_address):
        is_online = rfid_connectivity_checker(ip_address)
        print(f'Status of IP address {ip_address} is {"online" if is_online else "offline"}')
        status_color = 'green' if is_online else 'red'
        return ip_address, get_image_data(f'images/{status_color}.png', maxsize=(width, height))

    with ThreadPoolExecutor() as executor:
        future_to_ip = {executor.submit(check_and_update, ip): ip for ip in ip_addresses}
        for future in concurrent.futures.as_completed(future_to_ip):
            ip_address, image_data = future.result()
            window[f'IMAGE_{ip_address}'].update(data=image_data)

    # while True:
    #     for ip in ip_addresses:
    #         eventlet.spawn_n(check_and_update, ip)
    #     eventlet.sleep(10)  # Use eventlet's sleep for non-blocking wait

def launch_gui(ip_addresses):
    """
    Function to launch the GUI panel
    """
    sg.theme('DarkGrey12')

    # # Generating RFID layouts for different RFID_READERS
    # rfid_reader_numbers = ['INPAC#001', 'INPAC#002', 'INPAC#003']  # Add more INPAC numbers as needed
    # rfid_boxes = [sg.Frame(title='', layout=create_rfid_layout(rfid_reader_number), border_width=2, title_color='white',
    #                        relief=sg.RELIEF_SUNKEN, background_color='black') for rfid_reader_number in
    #               rfid_reader_numbers]
    ip_add = ip_addresses
    # Instead of creating a horizontal row for RFID boxes, create a vertical column layout
    rfid_boxes = [[sg.Frame(title='', layout=create_rfid_layout(ip, 'red'), border_width=2,
                            title_color='white', relief=sg.RELIEF_SUNKEN, background_color='black')] for
                  ip in ip_add]

    # Adding a black box to the layout
    details_box = sg.Column([
        [sg.Text('Device Details', background_color='black', text_color='white', size=(20, 1))]],
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
        rfid_row,  # Adding the row of RFID boxes to main layout0
        [terminal_box, details_box],
    ]

    window = sg.Window(title="RFID Reader Dashboard ", layout=layout, margins=(10, 10), resizable=True, finalize=True)

    # Update the RFID statuses immediately after window creation
    update_rfid_status(window, ip_addresses)

    last_clicked = None  # To keep track of the last clicked button

    while True:
        event, values = window.read()
        print(f"Event: {event}, Values: {values}")  # Log all events and values
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

        elif event.startswith('UPDATE_STATUS_'):
            ip = event.split('_')[-1]  # Extracting the IP from the event key
            is_online = values[event]
            print(f"Received update event for {ip}: {is_online}")  # Debug print before updating
            status_color = 'green' if is_online else 'red'  # Corrected color mapping
            print(f"Updating {ip} to {'online' if is_online else 'offline'} (color: {status_color})")  # Debug print
            window[f'IMAGE_{ip}'].update(data=get_image_data(f'images/{status_color}.png', maxsize=(width, height)))

    window.close()


if __name__ == '__main__':
    # Initialize database operations and fetch device IPs
    db_connection = DatabaseOperations(
        host_ip='192.168.10.1', host_username='LucidAuto', db_password='Lucid@390',
        db_name='LucidAutoDB', db_ip='192.168.10.1', db_port=3306, db_pool_name='server_db_pool', db_pool_size=5
    )
    device_ips = [ip[0] for ip in db_connection.findAllDeviceIPInRFIDDeviceDetails()]  # This will contain the list of
    # ip addresses stored in it.

    # Start the GUI
    launch_gui(device_ips)
