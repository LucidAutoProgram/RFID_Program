import asyncio
from queue import Empty
import PySimpleGUI as sg

from db_operations import server_connection_params
from utils import create_rfid_layout, setup_async_updates, start_reading, active_connections, stop_reading, \
    get_global_asyncio_loop, getRFIDResponseQueue, async_start_listening_response, rfid_ip_reading_mode, \
    update_tooltip, update_summary, create_detail_box, terminal_window

# --------------------- Global Variables ---------------------------------

terminal_output = {}
details_box = {}
ip = None
device_location = None
reading_mode = None
device_port = None
reading_mode_status = None  # Dictionary containing the ip as the key and its status i.e. reading mode(On/Off) as value 


def launch_gui(ip_addresses, ip_addresses_with_location):
    """
        Function to launch the GUI panel
        :param ip_addresses: List of ip addresses of the rfid reader.
        :param ip_addresses_with_location: Tuple containing the ip address with its location.
    """
    global terminal_output, details_box, ip, device_location, device_port, reading_mode, reading_mode_status
    sg.theme('DarkGrey12')

    # Create two separate columns for box_maker and product_maker with location labels
    box_maker_column = []
    product_maker_column = []
    details_columns = []
    terminal_columns = []

    for ip, device_location in ip_addresses_with_location:
        # Fetch port and reading mode for each IP address
        device_port_result = server_connection_params.findDevicePortInRFIDDeviceDetailsUsingDeviceIP(ip)
        device_port = device_port_result[0][0] if device_port_result else 'Not available'
        layout = create_rfid_layout(ip, 'red', device_location, device_port)
        # Use the create_detail_box function to create the details box

        create_detail_box(ip, details_box)
        terminal_window(ip, terminal_output)

        if 'BoxMaker' in device_location or 'ManualFeeding' in device_location:
            box_maker_column.append([sg.Frame(title='', layout=layout, border_width=2,
                                              title_color='white', relief=sg.RELIEF_SUNKEN, background_color='black')])
        elif 'ProductMaker' in device_location:
            product_maker_column.append([sg.Frame(title='', layout=layout, border_width=2,
                                                  title_color='white', relief=sg.RELIEF_SUNKEN,
                                                  background_color='black')])

        # Creating the columns for details and terminal and add them to the respective lists
        details_columns.append(
            sg.Column([[details_box[ip]]], expand_x=True, expand_y=True, pad=((10, 0), (0, 0))))
        terminal_columns.append(sg.Column([[terminal_output[ip]]], expand_x=True, expand_y=True, pad=((0, 10), (0, 0))))

    layout = [
        [sg.Column(box_maker_column, background_color='black'), sg.VSeparator(),
         sg.Column(product_maker_column, background_color='black'), sg.VSeparator(),
         sg.Multiline(default_text='', size=(40, 10), key='SUMMARY', autoscroll=True, expand_x=True, expand_y=True,
                      background_color='black')],
        terminal_columns + details_columns,
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

            # Fetch details for the clicked IP address
            device_port_result = server_connection_params.findDevicePortInRFIDDeviceDetailsUsingDeviceIP(clicked_ip)
            device_port = device_port_result[0][0] if device_port_result else 'Not available'

            reading_mode_status = rfid_ip_reading_mode.get(clicked_ip, 'Unknown')

            device_location = next((loc for ip, loc in ip_addresses_with_location if ip == clicked_ip), "Unknown")

            # Update the visible details box and terminal with the fetched data
            window[f"DETAILS_BOX_{clicked_ip}"].update(visible=True)
            window[f"TERMINAL_{clicked_ip}"].update(visible=True)

            # Update the text elements with the fetched data
            window[f"DEVICE_IP_{clicked_ip}"].update(f"Device IP: {clicked_ip}")
            window[f"DEVICE_PORT_{clicked_ip}"].update(f"Device Port: {device_port}")
            window[f"DEVICE_LOCATION_{clicked_ip}"].update(f"Device Location: {device_location}")
            window[f"READING_MODE_{clicked_ip}"].update(f"Reading Mode: {reading_mode_status}")

            # Set the last_clicked_ip to the current one
            last_clicked_ip = clicked_ip

        elif event.startswith('START_'):
            update_tooltip(last_clicked_ip, window, device_location, device_port)
            rfid_ip_reading_mode[last_clicked_ip] = 'On'
            window[f'START_{last_clicked_ip}'].update(visible=False)
            window[f'STOP_{last_clicked_ip}'].update(visible=True)
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

                    window[f'TERMINAL_{last_clicked_ip}'].update('Started RFID reading\n', append=True)
                else:
                    print("Event loop not available for async operation.")
                    window[f'TERMINAL_{last_clicked_ip}'].update('Unable to start RFID reading\n', append=True)

            else:
                print('last clicked Ip address', last_clicked_ip)
                print("Cannot Start reading. Connection not established or RFID reader offline.")
                window[f'TERMINAL_{last_clicked_ip}'].update('Unable to start RFID reading. RFID reader not '
                                                             'available.\n', append=True)

        elif event.startswith('STOP_'):
            update_tooltip(last_clicked_ip, window, device_location, device_port)
            rfid_ip_reading_mode[last_clicked_ip] = 'Off'
            window[f'START_{last_clicked_ip}'].update(visible=True)
            window[f'STOP_{last_clicked_ip}'].update(visible=False)
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

                    window[f'TERMINAL_{last_clicked_ip}'].update('Stopped RFID reading\n', append=True)
                else:
                    print("Event loop not available for async operation.")
                    window[f'TERMINAL_{last_clicked}'].update('Unable to stop RFID reading\n', append=True)
            else:
                print("Cannot stop reading. Connection not established or RFID reader offline.")
                window[f'TERMINAL_{last_clicked_ip}'].update(
                    'Unable to stop RFID reading. RFID reader not available.\n', append=True)
                # Check for new RFID tag responses and update the GUI
        try:
            rfid_response_queue = getRFIDResponseQueue()
            while not rfid_response_queue.empty():
                rfid_response = rfid_response_queue.get_nowait()
                if last_clicked_ip:
                    window[f'TERMINAL_{last_clicked_ip}'].update(value=rfid_response + '\n', append=True)

        except Empty:
            print('Queue for rfid tag handling is empty.')
            pass  # Handle empty queue if necessary
        try:
            while not queue.empty():
                ip_address, image_data, reading_mode_from_queue, ip_status_color = queue.get_nowait()
                print(f'Ip address in image updating {ip_address} and image data {image_data}')
                window[f'IMAGE_{ip_address}'].update(data=image_data)
                window[f'READING_MODE_{ip_address}'].update(f"Reading Mode: {reading_mode_from_queue}")

                if reading_mode_from_queue == 'On':
                    window[f'START_{ip_address}'].update(visible=False)
                    window[f'STOP_{ip_address}'].update(visible=True)
                else:
                    window[f'START_{ip_address}'].update(visible=True)
                    window[f'STOP_{ip_address}'].update(visible=False)

                update_summary(window, active_connections, ip_addresses_with_location, ip_status_color)
                update_tooltip(ip_address, window, device_location, device_port)

        except Empty:
            print('Queue for rfid light check handling is empty.')
            pass
    window.refresh()
    window.close()
