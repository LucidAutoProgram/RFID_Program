import asyncio
from queue import Empty
import PySimpleGUI as sg

from db_operations import server_connection_params
from utils import create_rfid_layout, setup_async_updates, start_reading, active_connections, stop_reading, \
    get_global_asyncio_loop, getRFIDResponseQueue, async_start_listening_response, rfid_ip_reading_mode, \
    update_tooltip, update_summary

ip = None  # Ip address of the rfid reader.
device_location = None  # Location of the rfid reader
reading_mode = None  # Reading mode of the reader(On/Off)
device_port = None  # Port of the rfid reader
reading_mode_status = None  # Dictionary containing the ip as the key and its status i.e. reading mode(On/Off) as value
reading_mode_from_queue = None  # Reading mode(On/Off) received from the queue populated in the async_update_rfid_status function in utils.py
# Dictionary to store IP address mapped to its details layout
ip_details_layout_map = {}
ip_terminal_layout = {}
last_clicked_ip = None


def launch_gui(ip_addresses, ip_addresses_with_location):
    """
            Function to launch the GUI panel
            :param ip_addresses: List of ip addresses of the rfid reader.
            :param ip_addresses_with_location: Tuple containing the ip address with its location.
        """
    global ip, device_location, device_port, reading_mode, reading_mode_status, \
        reading_mode_from_queue, last_clicked_ip, clicked_ip
    sg.theme('DarkGrey12')
    # Create two separate columns for box_maker and product_maker with location labels
    box_maker_column = []
    product_maker_column = []
    # # Track the state (started/stopped) for each IP address
    # ip_state = {ip: False for ip, device_location in ip_addresses_with_location}

    # Fetching Port
    device_port_result = server_connection_params.findDevicePortInRFIDDeviceDetailsUsingDeviceIP(ip)
    device_port = device_port_result[0][0] if device_port_result else 'Not available'
    for ip, device_location in ip_addresses_with_location:
        # creating layout for rfid reader location
        layout = create_rfid_layout(ip, 'red', device_location, device_port)

        # Filtering box makers and manualFeeders rfid readers in one column and product maker rfid readers in one column
        if 'BoxMaker' in device_location or 'ManualFeeding' in device_location:
            box_maker_column.append([sg.Frame(title='', layout=layout, border_width=2,
                                              title_color='white', relief=sg.RELIEF_SUNKEN, background_color='black')])
        elif 'ProductMaker' in device_location:
            product_maker_column.append([sg.Frame(title='', layout=layout, border_width=2,
                                                  title_color='white', relief=sg.RELIEF_SUNKEN,
                                                  background_color='black')])

    # creating layout for displaying information of rfid readers
    column_layout = [
        [sg.Text('DEVICE DETAILS', background_color='black', text_color='white', )],
        [sg.Text(f'Device IP:', background_color='black', text_color='white'),
         sg.Text('', background_color='black', text_color='white', key='IP')],
        [sg.Text(f'Device Port:', background_color='black', text_color='white'),
         sg.Text('', background_color='black', text_color='white', key='PORT')],
        [sg.Text(f'Device Location:', background_color='black', text_color='white'),
         sg.Text('', background_color='black', text_color='white', key='LOCATION')],
        [sg.Text(f'Reading Mode:', background_color='black', text_color='white'),
         sg.Text('', background_color='black', text_color='white', key='READING')],
        [sg.Button('Start', key='START', visible=False), sg.Button('Stop', key='STOP', visible=False)]

    ]

    # Main Window Layout
    layout = [
        [sg.Column(box_maker_column, background_color='black'), sg.VSeparator(),
         sg.Column(product_maker_column, background_color='black', ), sg.VSeparator(),

         # Display the rfid readers connection status and reading mode
         sg.Multiline(default_text='', size=(40, 10), key='SUMMARY', autoscroll=True, expand_x=True, expand_y=True,
                      background_color='black')],

        [sg.Column(column_layout, key='DETAILS_COLUMN', background_color='black', size=(150, 100), visible=False,
                   expand_y=True, expand_x=True),

         # Displays the tag that are getting scanned if rfid reader is in reading mode
         sg.Multiline(default_text='', key='TERMINAL', background_color='black', size=(20, 10), visible=False,
                      expand_y=True, expand_x=True)]

    ]

    # Main Window
    window = sg.Window(title="RFID Reader Dashboard ", layout=layout, margins=(10, 10), size=(800, 600), resizable=True,
                       finalize=True)

    # After setting up the GUI, starting the async updates
    queue = setup_async_updates(ip_addresses)

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
            clicked_ip = event.split('_')[1]

            # Check if the clicked IP is the same as the last clicked IP
            if last_clicked_ip == clicked_ip:
                # Toggle the visibility of the DETAILS_COLUMN and TERMINAL_COLUMN
                window['DETAILS_COLUMN'].update(visible=not window['DETAILS_COLUMN'].visible)
                window['TERMINAL'].update(visible=not window['TERMINAL'].visible)
            else:
                # If a different button is clicked, ensure that the columns are visible
                window['DETAILS_COLUMN'].update(visible=True)
                window['TERMINAL'].update('')
                window['TERMINAL'].update(visible=True)

                # Fetch the device details for the new IP
                device_port_result = server_connection_params.findDevicePortInRFIDDeviceDetailsUsingDeviceIP(clicked_ip)
                port = device_port_result[0][0] if device_port_result else 'Not available'

                device_location_result = server_connection_params.findDeviceLocationInRFIDDeviceDetailsUsingDeviceIP(
                    clicked_ip)
                location = device_location_result[0][0] if device_location_result else 'Not available'

                reading_mode_status = rfid_ip_reading_mode.get(clicked_ip, 'Not Available')

                # Update the display elements with the new device details
                window['IP'].update(clicked_ip)
                window['LOCATION'].update(location)
                window['PORT'].update(port)
                window['READING'].update(reading_mode_status)

                # Update button visibility based on the reading mode status
                if reading_mode_status == 'On':
                    window['START'].update(visible=False)
                    window['STOP'].update(visible=True)
                elif reading_mode_status == 'Off':
                    window['START'].update(visible=True)
                    window['STOP'].update(visible=False)
                else:
                    window['START'].update(visible=False)
                    window['STOP'].update(visible=False)

            # Update the last clicked IP
            last_clicked_ip = clicked_ip

        elif event == 'START' and last_clicked_ip is not None:
            # Active connections are the rfid readers whose connection is successfully established
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

                    window[f'TERMINAL'].update(f'Sent RFID reading command for ip :{last_clicked_ip}\n', append=True)
                else:
                    print("Event loop not available for async operation.")
                    window[f'TERMINAL'].update(f'Unable to start RFID reading for ip :{last_clicked_ip}\n', append=True)
            else:
                print('last clicked Ip address', last_clicked_ip)
                print("Cannot Start reading. Connection not established or RFID reader offline.")
                window[f'TERMINAL'].update('Unable to start RFID reading. RFID reader not '
                                           f'available for ip :{last_clicked_ip}.\n', append=True)

        elif event == 'STOP' and last_clicked_ip is not None:
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

                    window[f'TERMINAL'].update(f'Stopped RFID reading for ip :{last_clicked_ip}\n', append=True)
                else:
                    print("Event loop not available for async operation.")
                    window[f'TERMINAL'].update(f'Unable to stop RFID reading for ip:{last_clicked_ip}\n', append=True)
            else:
                print("Cannot stop reading. Connection not established or RFID reader offline.")
                window[f'TERMINAL'].update(
                    f'Unable to stop RFID reading. RFID reader not available for ip :{last_clicked_ip}.\n', append=True)
                # Check for new RFID tag responses and update the GUI
        try:
            rfid_response_queue = getRFIDResponseQueue()
            while not rfid_response_queue.empty():
                rfid_response = rfid_response_queue.get_nowait()

                rfid_ip = None
                rfid_tag_response = None

                # Iterating through the set and identify the IP address and the RFID tag ID.
                for item in rfid_response:
                    # the first item is an IP address.
                    if '.' in item and len(item.split('.')) == 4:
                        rfid_ip = item
                    else:
                        # the . one is rfid tag
                        rfid_tag_response = item

                # Print the extracted IP address and RFID tag ID.
                print(f"IP Address: {rfid_ip}")
                print(f"RFID Tag ID: {rfid_tag_response}")

                # will only update the terminal with the rfid tags of the ip address/ rfid reader which is currently
                # opened
                if last_clicked_ip == rfid_ip:
                    window[f'TERMINAL'].update(value=f"RFID tag: {rfid_tag_response} \n", append=True)
        except Empty:
            print('Queue for rfid tag handling is empty.')
            pass  # Handle empty queue if necessary
        try:
            while not queue.empty():
                ip_address, image_data, reading_mode_from_queue, ip_status_color = queue.get_nowait()
                # it gone update the image if the reading mode is changed
                window[f'IMAGE_{ip_address}'].update(data=image_data)
                if ip_address == last_clicked_ip:
                    print(f'Reading mode for {ip_address} is {reading_mode_from_queue}')
                    print(f'Ip address in image updating {ip_address} and image data {image_data}')
                    window[f'READING'].update(f"{reading_mode_from_queue}")

                    # Handling the visibility of buttons depending upon the reading mode we are getting
                    if reading_mode_from_queue == 'On':
                        window['START'].update(visible=False)
                        window['STOP'].update(visible=True)
                        # if ip_state[last_clicked_ip]:
                        #  window['START'].update(visible=False)
                        #  window['STOP'].update(visible=True)
                    elif reading_mode_from_queue == 'Off':
                        window['START'].update(visible=True)
                        window['STOP'].update(visible=False)
                    else:
                        window['START'].update(visible=False)
                        window['STOP'].update(visible=False)

                device_port_result = server_connection_params.findDevicePortInRFIDDeviceDetailsUsingDeviceIP(ip_address)
                device_port = device_port_result[0][0] if device_port_result else 'Not available'

                device_location_result = server_connection_params.findDeviceLocationInRFIDDeviceDetailsUsingDeviceIP(
                    ip_address)
                device_location = device_location_result[0][0] if device_location_result else 'Not available'

                # Updating the tooltip on any updates received from queue
                update_tooltip(ip_address, window, device_location, device_port)
                # Updating the summary on any updates received from the queue
                update_summary(window, active_connections, ip_addresses_with_location, ip_status_color)

        except Empty:
            print('Queue for rfid light check handling is empty.')
            pass

    window.close()
