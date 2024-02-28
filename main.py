import concurrent
import io
from PIL import Image
from func import rfid_connectivity_checker, DatabaseOperations, server_connection_params
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


def create_rfid_layout(ip, status_color, location):
    """
    Generating layout for each RFID box with location instead of IP on the button.
    """
    return [
        [sg.Image(data=get_image_data(f'images/{status_color}.png', maxsize=(width, height)), background_color='black',
                  key=f'IMAGE_{ip}'),
         sg.Button(location, button_color=('white', 'black'), border_width=0, focus=False,
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


def launch_gui(ip_addresses, ip_addresses_with_location):
    """
    Function to launch the GUI panel
    """
    sg.theme('DarkGrey12')

    # Create two separate columns for boxmaker and productmaker with location labels
    boxmaker_column = [[sg.Frame(title='', layout=create_rfid_layout(ip, 'red', loc), border_width=2,
                                 title_color='white', relief=sg.RELIEF_SUNKEN, background_color='black')]
                       for ip, loc in ip_addresses_with_location if
                       'boxmaker' in loc.lower() or 'manualfeeding' in loc.lower()]

    productmaker_column = [[sg.Frame(title='', layout=create_rfid_layout(ip, 'red', loc), border_width=2,
                                     title_color='white', relief=sg.RELIEF_SUNKEN, background_color='black')]
                           for ip, loc in ip_addresses_with_location if 'productmaker' in loc.lower()]

    # Adding a black box to the layout
    # Updated details_box with keys for dynamic updates
    details_box = sg.Column([
        [sg.Text('Device IP:', background_color='black', text_color='white', key='DEVICE_IP')],
        [sg.Text('Device Port:', background_color='black', text_color='white', key='DEVICE_PORT')],
        [sg.Text('Device Location:', background_color='black', text_color='white', key='DEVICE_LOCATION')],
        [sg.Text('Reading Mode:', background_color='black', text_color='white', key='READING_MODE')],
    ], key='DETAILS_BOX', background_color='black', visible=False, pad=((0, 0), (0, 0)), expand_x=True, expand_y=True)

    terminal_box = sg.Column([
        [sg.Text('RFID TERMINAL', background_color='black', text_color='white')]],
        key='TERMINAL',
        background_color='black',
        visible=False,  # Initially hidden
        pad=((0, 0), (0, 0)),
        expand_x=True,
        expand_y=True
    )

    # Modify layout to include both columns
    layout = [
        [sg.Column(boxmaker_column, background_color='black'), sg.VSeparator(),
         sg.Column(productmaker_column, background_color='black')],
        [sg.Column([[terminal_box]], expand_x=True, expand_y=True, pad=((0, 10), (0, 0))),
         # Add right padding to details_box
         sg.Column([[details_box]], expand_x=True, expand_y=True, pad=((10, 0), (0, 0)))],
        # Add left padding to terminal_box
    ]

    window = sg.Window(title="RFID Reader Dashboard ", layout=layout, margins=(10, 10), size=(600, 600), resizable=True,
                       finalize=True)

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
                ip_address = event.split('_')[-1]  # Extracting the IP address from the event key

                # functions to get these details based on IP address

                device_port_result = server_connection_params.findDevicePortInRFIDDeviceDetailsUsingDeviceIP(ip_address)
                device_port = device_port_result[0][0] if device_port_result else 'Not available'

                device_location_result = server_connection_params.findDeviceLocationInRFIDDeviceDetailsUsingDeviceIP(
                    ip_address)
                device_location = device_location_result[0][0] if device_location_result else 'Not available'

                reading_mode_result = server_connection_params.findReadingModeInRFIDDeviceDetailsUsingDeviceIP(
                    ip_address)
                reading_mode = reading_mode_result[0][0] if reading_mode_result else 'Not available'

                # Update the details_box with the extracted and formatted information
                window['DEVICE_IP'].update(f'Device IP: {ip_address}')
                window['DEVICE_PORT'].update(f'Device Port: {device_port}')
                window['DEVICE_LOCATION'].update(f'Device Location: {device_location}')
                window['READING_MODE'].update(f'Reading Mode: {reading_mode}')

                if not new_visibility:
                    last_clicked = None  # Resetting last clicked if boxes are hidden
            else:
                # If a different button is clicked, always show the boxes
                window['TERMINAL'].update(visible=True)
                window['DETAILS_BOX'].update(visible=True)
                last_clicked = event  # Updating last clicked to the current button
                ip_address = event.split('_')[-1]  # Extracting the IP address from the event key

                # functions to get these details based on IP address

                device_port_result = server_connection_params.findDevicePortInRFIDDeviceDetailsUsingDeviceIP(ip_address)
                device_port = device_port_result[0][0] if device_port_result else 'Not available'

                device_location_result = server_connection_params.findDeviceLocationInRFIDDeviceDetailsUsingDeviceIP(
                    ip_address)
                device_location = device_location_result[0][0] if device_location_result else 'Not available'

                reading_mode_result = server_connection_params.findReadingModeInRFIDDeviceDetailsUsingDeviceIP(
                    ip_address)
                reading_mode = reading_mode_result[0][0] if reading_mode_result else 'Not available'

                # Update the details_box with the extracted and formatted information
                window['DEVICE_IP'].update(f'Device IP: {ip_address}')
                window['DEVICE_PORT'].update(f'Device Port: {device_port}')
                window['DEVICE_LOCATION'].update(f'Device Location: {device_location}')
                window['READING_MODE'].update(f'Reading Mode: {reading_mode}')
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

    ip_addresses_with_location = db_connection.findAllDeviceIPAndLocationInRFIDDeviceDetails()

    # Start the GUI
    launch_gui(device_ips, ip_addresses_with_location)
