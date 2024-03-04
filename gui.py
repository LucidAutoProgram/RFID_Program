import asyncio
from queue import Empty
import PySimpleGUI as sg

from db_operations import server_connection_params
from utils import create_rfid_layout, setup_async_updates, start_reading, active_connections, stop_reading, \
    get_global_asyncio_loop, getRFIDResponseQueue,  async_start_listening_response


def launch_gui(ip_addresses, ip_addresses_with_location):
    """
        Function to launch the GUI panel
    """
    sg.theme('DarkGrey12')

    # Create two separate columns for box_maker and product_maker with location labels
    box_maker_column = []
    product_maker_column = []

    for ip, loc in ip_addresses_with_location:
        # Fetch port and reading mode for each IP address
        device_port_result = server_connection_params.findDevicePortInRFIDDeviceDetailsUsingDeviceIP(ip)
        device_port = device_port_result[0][0] if device_port_result else 'Not available'

        reading_mode_result = server_connection_params.findReadingModeInRFIDDeviceDetailsUsingDeviceIP(ip)
        reading_mode = reading_mode_result[0][0] if reading_mode_result else 'Not available'

        layout = create_rfid_layout(ip, 'red', loc, device_port, reading_mode)

        if 'BoxMaker' in loc or 'ManualFeeding' in loc:
            box_maker_column.append([sg.Frame(title='', layout=layout, border_width=2,
                                              title_color='white', relief=sg.RELIEF_SUNKEN, background_color='black')])
        elif 'ProductMaker' in loc:
            product_maker_column.append([sg.Frame(title='', layout=layout, border_width=2,
                                                  title_color='white', relief=sg.RELIEF_SUNKEN,
                                                  background_color='black')])

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
         sg.Column(product_maker_column, background_color='black'), sg.VSeparator(),
         sg.Multiline(default_text='', size=(40, 10), key='SUMMARY', autoscroll=True, expand_x=True, expand_y=True,
                      background_color='black')],
        [sg.Column([[terminal_output]], expand_x=True, expand_y=True, pad=((0, 10), (0, 0))),
         sg.Column([[details_box]], expand_x=True, expand_y=True, pad=((10, 0), (0, 0)))],
    ]

    window = sg.Window(title="RFID Reader Dashboard ", layout=layout, margins=(10, 10), size=(800, 600), resizable=True,
                       finalize=True)

    # After setting up the GUI and starting the async updates
    queue = setup_async_updates(ip_addresses)
    # print(f'Queue for rfid status {queue}')
    last_clicked_ip = None
    last_clicked = None  # To keep track of the last clicked button
    summarized_ips = set()

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
                last_clicked_ip = ip_address

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
            window['START'].update(disabled=True)
            window['STOP'].update(disabled=False)
            if last_clicked_ip in active_connections:
                loop = get_global_asyncio_loop()
                print('Global asyncio loop in gui', loop)
                if loop is not None:
                    print(f'Last clicked ip in gui start event {last_clicked_ip}')
                    asyncio.run_coroutine_threadsafe(start_reading(last_clicked_ip), loop)

                    try:
                        # Updating the reading mode as 'On' in the database whenever clicked on the start button
                        server_connection_params.updateReadingModeStatusInRFIDDeviceDetails('On', last_clicked_ip)
                    except Exception as e:
                        print(f'Unable to update the reading mode status in the rfid device details for '
                              f'{last_clicked_ip} as got error : {e}')

                    window['TERMINAL'].update('Started RFID reading\n', append=True)
                else:
                    print("Event loop not available for async operation.")
                    window['TERMINAL'].update('Unable to start RFID reading\n', append=True)

            else:
                print('last clicked Ip address', last_clicked_ip)
                print("Cannot Start reading. Connection not established or RFID reader offline.")
                window['TERMINAL'].update('Unable to start RFID reading. RFID reader not available.\n', append=True)

        elif event == 'STOP':
            window['START'].update(disabled=False)
            window['STOP'].update(disabled=True)
            if last_clicked_ip in active_connections:
                loop = get_global_asyncio_loop()
                print('Global asyncio loop in gui', loop)
                if loop is not None:
                    asyncio.run_coroutine_threadsafe(stop_reading(last_clicked_ip), loop)

                    try:
                        # Updating the reading mode as 'Off' in the database whenever clicked on the start button
                        server_connection_params.updateReadingModeStatusInRFIDDeviceDetails('Off', last_clicked_ip)
                    except Exception as e:
                        print(f'Unable to update the reading mode status in the rfid device details for '
                              f'{last_clicked_ip} as got error : {e}')

                    window['TERMINAL'].update('Stopped RFID reading\n', append=True)
                else:
                    print("Event loop not available for async operation.")
                    window['TERMINAL'].update('Unable to stop RFID reading\n', append=True)
            else:
                print("Cannot stop reading. Connection not established or RFID reader offline.")
                window['TERMINAL'].update('Unable to stop RFID reading. RFID reader not available.\n', append=True)
                # Check for new RFID tag responses and update the GUI
        try:
            rfid_response_queue = getRFIDResponseQueue()
            while not rfid_response_queue.empty():
                rfid_response = rfid_response_queue.get_nowait()
                window['TERMINAL'].update(value=rfid_response + '\n', append=True)

        except Empty:
            print('Queue for rfid tag handling is empty.')
            pass  # Handle empty queue if necessary
        # Check if there are updates from the async task
        try:
            online_summary_text = ""
            offline_summary_text = ""
            # print(f'Queue at top while loop {queue}')
            # if queue.empty():
            #     print('if Queue is empty')
            # else:
            #     print('if Queue is not empty')
            # print(f'Queue size in the gui {queue.qsize()}')
            while not queue.empty():
                # print("Queue not empty")
                ip_address, image_data = queue.get_nowait()
                print(f'Ip address in image updating {ip_address} and image data {image_data}')
                window[f'IMAGE_{ip_address}'].update(data=image_data)

                # Separate the online and offline IP addresses
                if ip_address in active_connections:
                    if ip_address not in summarized_ips:
                        location = next((loc for ip, loc in ip_addresses_with_location if ip == ip_address), "Unknown")
                        online_summary_text += f"{location} (IP: {ip_address}) connection established\n"
                        summarized_ips.add(ip_address)  # Add the IP address to the set
                else:
                    if ip_address not in summarized_ips:
                        location = next((loc for ip, loc in ip_addresses_with_location if ip == ip_address), "Unknown")
                        offline_summary_text += f"{location} (IP: {ip_address}) connection not established\n"
                        summarized_ips.add(ip_address)  # Add the IP address to the set

            # Update the summary terminal with online IPs at the top and offline IPs at the bottom
            final_summary_text = online_summary_text + '\n' + offline_summary_text
            if final_summary_text.strip():
                window['SUMMARY'].update(value=final_summary_text.strip() + '\n', append=True)

        except Empty:
            print('Queue for rfid light check handling is empty.')
            pass

    window.close()
