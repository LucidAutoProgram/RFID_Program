import asyncio
from queue import Empty
import PySimpleGUI as sg

from db_operations import server_connection_params
from utils import create_rfid_layout, setup_async_updates, start_reading, active_connections, stop_reading, \
    global_asyncio_loop


def launch_gui(ip_addresses, ip_addresses_with_location):
    """
        Function to launch the GUI panel
    """
    sg.theme('DarkGrey12')

    # Create two separate columns for box_maker and product_maker with location labels
    box_maker_column = [[sg.Frame(title='', layout=create_rfid_layout(ip, 'red', loc), border_width=2,
                                  title_color='white', relief=sg.RELIEF_SUNKEN, background_color='black')]
                        for ip, loc in ip_addresses_with_location if
                        'BoxMaker' in loc or 'ManualFeeding' in loc]

    product_maker_column = [[sg.Frame(title='', layout=create_rfid_layout(ip, 'red', loc), border_width=2,
                                      title_color='white', relief=sg.RELIEF_SUNKEN, background_color='black')]
                            for ip, loc in ip_addresses_with_location if 'ProductMaker' in loc]

    details_box = sg.Column([
        [sg.Text('DEVICE DETAILS', background_color='black', text_color='white', font=('Cambria', 17),
                 justification='center')],
        [sg.Text('Device IP:', background_color='black', text_color='white', key='DEVICE_IP')],
        [sg.Text('Device Port:', background_color='black', text_color='white', key='DEVICE_PORT')],
        [sg.Text('Device Location:', background_color='black', text_color='white', key='DEVICE_LOCATION')],
        [sg.Text('Reading Mode:', background_color='black', text_color='white', key='READING_MODE')],
        [sg.Button('Start', key='START'), sg.Button('Stop', key='STOP')]
    ], key='DETAILS_BOX', background_color='black', visible=False, pad=((0, 0), (0, 0)), expand_x=True, expand_y=True)

    terminal_output = sg.Multiline(default_text='', size=(30, 5), key='TERMINAL', autoscroll=True, disabled=True,
                                   visible=False, expand_x=True, expand_y=True, background_color='black')

    layout = [
        [sg.Column(box_maker_column, background_color='black'), sg.VSeparator(),
         sg.Column(product_maker_column, background_color='black')],
        [sg.Column([[terminal_output]], expand_x=True, expand_y=True, pad=((0, 10), (0, 0))),
         sg.Column([[details_box]], expand_x=True, expand_y=True, pad=((10, 0), (0, 0)))],
    ]

    window = sg.Window(title="RFID Reader Dashboard ", layout=layout, margins=(10, 10), size=(600, 600), resizable=True,
                       finalize=True)

    # After setting up the GUI and starting the async updates
    queue = setup_async_updates(ip_addresses)
    last_clicked_ip = None
    last_clicked = None  # To keep track of the last clicked button

    while True:
        event, values = window.read(timeout=100)
        if event == sg.WINDOW_CLOSED:
            break

        elif event.startswith('BUTTON_'):
            # Checking if the clicked button is the same as the last clicked
            if last_clicked == event:
                # If yes, toggle the visibility off/on
                new_visibility = not window['TERMINAL'].visible  # Use the current visibility of terminal_box to
                # toggle both
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
                last_clicked_ip = ip_address

        elif event == 'START':
            if last_clicked_ip in active_connections:
                print('Global asyncio loop in gui', global_asyncio_loop)
                if global_asyncio_loop is not None:  # Ensure the loop is available
                    asyncio.run_coroutine_threadsafe(start_reading(last_clicked_ip), global_asyncio_loop)
                else:
                    print("Event loop not available for async operation.")

                # asyncio.run(start_reading(last_clicked_ip))
                # Schedule the start_reading coroutine to be run
                # schedule_async_task(start_reading, last_clicked_ip)

                # # Retrieve the event loop from the background thread
                # loop = asyncio.get_event_loop()
                #
                # # When scheduling the task
                # schedule_async_task(start_reading(last_clicked_ip), loop)

            else:
                print('last clicked Ip address', last_clicked_ip)
                print("Cannot Start reading. Connection not established or RFID reader offline.")

        elif event == 'STOP':
            if last_clicked_ip in active_connections:
                if global_asyncio_loop is not None:  # Ensure the loop is available
                    asyncio.run_coroutine_threadsafe(stop_reading(last_clicked_ip), global_asyncio_loop)
                else:
                    print("Event loop not available for async operation.")

                # asyncio.run(stop_reading(last_clicked_ip))

                # Schedule the stop_reading coroutine to be run
                # schedule_async_task(stop_reading, last_clicked_ip)

                # # Retrieve the event loop from the background thread
                # loop = asyncio.get_event_loop()
                #
                # # When scheduling the task
                # schedule_async_task(stop_reading(last_clicked_ip), loop)
            else:
                print("Cannot stop reading. Connection not established or RFID reader offline.")

        # Check if there are updates from the async task
        try:
            while not queue.empty():
                ip_address, image_data = queue.get_nowait()
                print(f'Ip address {ip_address} and image data is {image_data}')
                window[f'IMAGE_{ip_address}'].update(data=image_data)
        except Empty:
            print('Queue is empty')
            pass

    window.close()
