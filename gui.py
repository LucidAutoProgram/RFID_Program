import asyncio
from queue import Empty
import PySimpleGUI as sg

from db_operations import server_connection_params
from utils import create_rfid_layout, setup_async_updates, start_reading, active_connections, stop_reading, \
    get_global_asyncio_loop, getRFIDResponseQueue, async_start_listening_response, rfid_ip_reading_mode, \
    update_tooltip, update_summary

# --------------------- Global Variables ---------------------------------

terminal_output = {}
details_box = {}
ip = None
device_location = None
reading_mode = None
device_port = None
reading_mode_status = None  # Dictionary containing the ip as the key and its status i.e. reading mode(On/Off) as value
reading_mode_from_queue = None


def get_device_details(ip):
    device_port_result = server_connection_params.findDevicePortInRFIDDeviceDetailsUsingDeviceIP(ip)
    port = device_port_result[0][0] if device_port_result else 'Not available'

    device_location_result = server_connection_params.findDeviceLocationInRFIDDeviceDetailsUsingDeviceIP(ip)
    location = device_location_result[0][0] if device_location_result else 'Not available'

    return {
        'port': port,
        'location': location
    }


def launch_gui(ip_addresses, ip_addresses_with_location):
    """
        Function to launch the GUI panel
        :param ip_addresses: List of ip addresses of the rfid reader.
        :param ip_addresses_with_location: Tuple containing the ip address with its location.
    """
    global terminal_output, details_box, ip, device_location, device_port, reading_mode, reading_mode_status, \
        reading_mode_from_queue
    sg.theme('DarkGrey12')

    # Create two separate columns for box_maker and product_maker with location labels
    box_maker_column = []
    product_maker_column = []

    for ip, device_location in ip_addresses_with_location:
        # Fetch port and reading mode for each IP address

        device_port_result = server_connection_params.findDevicePortInRFIDDeviceDetailsUsingDeviceIP(ip)
        device_port = device_port_result[0][0] if device_port_result else 'Not available'

        layout = create_rfid_layout(ip, 'red', device_location, device_port)
        # Use the create_detail_box function to create the details box

        if 'BoxMaker' in device_location or 'ManualFeeding' in device_location:
            box_maker_column.append([sg.Frame(title='', layout=layout, border_width=2,
                                              title_color='white', relief=sg.RELIEF_SUNKEN, background_color='black')])
        elif 'ProductMaker' in device_location:
            product_maker_column.append([sg.Frame(title='', layout=layout, border_width=2,
                                                  title_color='white', relief=sg.RELIEF_SUNKEN,
                                                  background_color='black')])

    details_box_layout = [
        [sg.Text('DEVICE DETAILS', background_color='black', text_color='white', font=('Cambria', 17),
                 justification='center')],
        [sg.Text('Device IP:', background_color='black', text_color='white', key='DEVICE_IP')],
        [sg.Text('Device Port:', background_color='black', text_color='white', key='DEVICE_PORT')],
        [sg.Text('Device Location:', background_color='black', text_color='white', key='DEVICE_LOCATION')],
        [sg.Text('Reading Mode:', background_color='black', text_color='white', key='READING_MODE')],
        [sg.Button('Start', key='START', visible=False), sg.Button('Stop', key='STOP', visible=False)],
    ]

    terminal_layout = [
        [sg.Multiline(default_text='', size=(30, 5), key=f'TERMINAL', autoscroll=True, disabled=True, expand_x=True,
                      expand_y=True, background_color='black')]
    ]
    layout = [
        [sg.Column(box_maker_column, background_color='black'), sg.VSeparator(),
         sg.Column(product_maker_column, background_color='black'), sg.VSeparator(),
         sg.Multiline(default_text='', size=(40, 10), key='SUMMARY', autoscroll=True, expand_x=True, expand_y=True,
                      background_color='black')],
        [sg.Column(details_box_layout, key='DETAILS_COLUMN', background_color='black', pad=((0, 0), (0, 0)),
                   expand_x=True, expand_y=True, visible=False),
         sg.Column(terminal_layout, key='TERMINAL_COLUMN', expand_x=True, expand_y=True, background_color='black',
                   visible=False)],

    ]

    window = sg.Window(title="RFID Reader Dashboard ", layout=layout, margins=(10, 10), size=(800, 600), resizable=True,
                       finalize=True)

    # After setting up the GUI and starting the async updates
    queue = setup_async_updates(ip_addresses)
    # print(f'Queue for rfid status {queue}')
    last_clicked_ip = None
    last_clicked = None  # To keep track of the last clicked button

    while True:
        event, values = window.read(timeout=10)

        # Pump the asyncio event loop to ensure it runs concurrently
        loop = asyncio.get_event_loop()
        if not loop.is_running():
            # If the loop isn't running, we need to handle tasks manually
            loop.run_until_complete(asyncio.sleep(0))  # Short sleep to pump the loop

        # Check if we need to start listening to RFID responses
        if not hasattr(window, 'listening_started') or not window.listening_started:  # If not listening started
            asyncio.run_coroutine_threadsafe(async_start_listening_response(ip_addresses), loop)
            window.listening_started = True  # Prevents re-starting the listener

        if event == sg.WINDOW_CLOSED:
            break

        # Assume last_clicked_ip is defined at a broader scope, initialized to None
        elif event.startswith('BUTTON_'):
            clicked_ip = event.split('_')[1]  # Extract the IP address from the event key

            # Check if the same button is clicked again
            if last_clicked_ip == clicked_ip:
                # Toggle visibility
                details_visible = not window[f"DETAILS_COLUMN"].visible
                terminal_visible = not window[f"TERMINAL_COLUMN"].visible
                window[f"DETAILS_COLUMN"].update(visible=details_visible)
                window[f"TERMINAL_COLUMN"].update(visible=terminal_visible)
            else:
                # Fetch details for the clicked IP address
                device_port_result = server_connection_params.findDevicePortInRFIDDeviceDetailsUsingDeviceIP(clicked_ip)
                device_port = device_port_result[0][0] if device_port_result else 'Not available'

                reading_mode_status = rfid_ip_reading_mode.get(clicked_ip, 'Not Available')

                device_location = next((loc for ip, loc in ip_addresses_with_location if ip == clicked_ip),
                                       "Not Available")

                # Hide the last clicked button's elements
                if last_clicked_ip is not None:
                    window[f"DETAILS_COLUMN"].update(visible=False)
                    window[f"TERMINAL_COLUMN"].update(visible=False)

                # Update the visible details box and terminal with the fetched data for the current clicked IP
                window[f"DETAILS_COLUMN"].update(visible=True)
                window[f"TERMINAL_COLUMN"].update(visible=True)

                # Fetch the details for the clicked IP address
                device_details = get_device_details(clicked_ip)
                print(f'RFID Ip reading mode for {clicked_ip} is {reading_mode_status}')

                # Update the GUI elements with the fetched details
                window['DEVICE_IP'].update(f"Device IP: {clicked_ip}")
                window['DEVICE_PORT'].update(f"Device Port: {device_details['port']}")
                window['DEVICE_LOCATION'].update(f"Device Location: {device_details['location']}")
                window['READING_MODE'].update(f"Reading Mode: {reading_mode_status}")

            # Update the last_clicked_ip for the next event
            last_clicked_ip = clicked_ip

        elif event == 'START':
            update_tooltip(last_clicked_ip, window, device_location, device_port)
            window[f'START'].update(visible=False)
            window[f'STOP'].update(visible=True)
            if last_clicked_ip in active_connections:
                loop = get_global_asyncio_loop()
                if loop is not None:
                    print(f'Last clicked ip in gui start event {last_clicked_ip}')
                    asyncio.run_coroutine_threadsafe(start_reading(last_clicked_ip), loop)

                    try:
                        # Updating the reading mode as 'On' in the database whenever clicked on the start button
                        server_connection_params.updateReadingModeStatusInRFIDDeviceDetails('On', last_clicked_ip)
                    except Exception as e:
                        print(f'Unable to update the reading mode status in the rfid device details for '
                              f'{last_clicked_ip} as got error : {e}')

                    window[f'TERMINAL'].update('Started RFID reading\n', append=True)
                else:
                    print("Event loop not available for async operation.")
                    window[f'TERMINAL'].update('Unable to start RFID reading\n', append=True)

            else:
                print('last clicked Ip address', last_clicked_ip)
                print("Cannot Start reading. Connection not established or RFID reader offline.")
                window[f'TERMINAL'].update('Unable to start RFID reading. RFID reader not '
                                           'available.\n', append=True)

        elif event == 'STOP':
            update_tooltip(last_clicked_ip, window, device_location, device_port)
            window[f'START'].update(visible=True)
            window[f'STOP'].update(visible=False)
            if last_clicked_ip in active_connections:
                loop = get_global_asyncio_loop()
                if loop is not None:
                    asyncio.run_coroutine_threadsafe(stop_reading(last_clicked_ip), loop)

                    try:
                        # Updating the reading mode as 'Off' in the database whenever clicked on the start button
                        server_connection_params.updateReadingModeStatusInRFIDDeviceDetails('Off', last_clicked_ip)
                    except Exception as e:
                        print(f'Unable to update the reading mode status in the rfid device details for '
                              f'{last_clicked_ip} as got error : {e}')

                    window[f'TERMINAL'].update('Stopped RFID reading\n', append=True)
                else:
                    print("Event loop not available for async operation.")
                    window[f'TERMINAL'].update('Unable to stop RFID reading\n', append=True)
            else:
                print("Cannot stop reading. Connection not established or RFID reader offline.")
                window[f'TERMINAL'].update(
                    'Unable to stop RFID reading. RFID reader not available.\n', append=True)
                # Check for new RFID tag responses and update the GUI
        try:
            rfid_response_queue = getRFIDResponseQueue()
            while not rfid_response_queue.empty():
                rfid_response = rfid_response_queue.get_nowait()
                if last_clicked_ip:
                    window['TERMINAL'].update(value=rfid_response + '\n', append=True)


        except Empty:
            print('Queue for rfid tag handling is empty.')
            pass  # Handle empty queue if necessary
        try:
            while not queue.empty():
                ip_address, image_data, reading_mode_from_queue, ip_status_color = queue.get_nowait()
                window[f'IMAGE_{ip_address}'].update(data=image_data)
                if ip_address == last_clicked_ip:
                    print(f'Reading mode for {ip_address} is {reading_mode_from_queue}')
                    print(f'Ip address in image updating {ip_address} and image data {image_data}')
                    window[f'READING_MODE'].update(f"Reading Mode: {reading_mode_from_queue}")

                    if reading_mode_from_queue == 'On':
                        window[f'START'].update(visible=False)
                        window[f'STOP'].update(visible=True)
                    elif reading_mode_from_queue == 'Off':
                        window[f'START'].update(visible=True)
                        window[f'STOP'].update(visible=False)
                    else:
                        window[f'START'].update(visible=False)
                        window[f'STOP'].update(visible=False)

                device_port_result = server_connection_params.findDevicePortInRFIDDeviceDetailsUsingDeviceIP(ip_address)
                device_port = device_port_result[0][0] if device_port_result else 'Not available'

                device_location_result = server_connection_params.findDeviceLocationInRFIDDeviceDetailsUsingDeviceIP(
                    ip_address)
                device_location = device_location_result[0][0] if device_location_result else 'Not available'

                update_tooltip(ip_address, window, device_location, device_port)

                update_summary(window, active_connections, ip_addresses_with_location, ip_status_color)


        except Empty:
            print('Queue for rfid light check handling is empty.')
            pass
    window.refresh()
    window.close()
