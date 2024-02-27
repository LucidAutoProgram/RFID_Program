import socket

import PySimpleGUI as sg
import threading

from api import close_network_connection, start_reading_mode, stop_reading_mode, open_net_connection

global_net_conn = None  # Global variable to store the network connection
reading_active = False  # Global flag to keep track of reading mode.


def get_rfid_tag_info(response):
    """
        Function to extract the rfid reader tag info from the response returned from the rfid reader after sending the
        start reading command by the start_reading_mode function.
    """
    if not response or len(response) < 11:
        return None

    epc_len = response[10]  # EPC LEN at byte index 10
    epc_data_start_index = 11  # EPC data starts at index 11
    epc_data_end_index = epc_data_start_index + epc_len
    epc_data = response[epc_data_start_index:epc_data_end_index]  # The raw rfid tag info.
    epc_hex = ''.join(format(x, '02x') for x in epc_data)  # Convert to hexadecimal string
    return epc_hex


def read_continuous_rfid_res(window):
    """
        Function to read continuous response from the rfid reader each time a rfid tag is scanned.
        :param window: The terminal window of the gui to display the information.
    """
    global reading_active, global_net_conn
    if global_net_conn and reading_active:  # If the network connection is established and reading_active flag is true.
        # Initiate RFID reading mode once
        start_reading_mode(global_net_conn, 'network')  # Calling the start_reading_mode function to send the command to
        # the rfid reader to start reading.
        print('RFID reading initiated. Waiting for tags...')
        global_net_conn.settimeout(0.01)  # Set a timeout of 1 second

        while reading_active:
            try:
                response = global_net_conn.recv(1024)  # Receiving the response from the network connection established
                # with the rfid reader
                if response:
                    rfid_tag_data = get_rfid_tag_info(response)
                    if rfid_tag_data:
                        print('RFID TAG', rfid_tag_data)
                        window.write_event_value('-TAG_READ-', rfid_tag_data)  # Displaying the rfid tag on the gui
                        # window.
            except socket.timeout:
                continue  # Continue the loop if a timeout occurs
            except Exception as e:
                print(f"Error receiving RFID tag data: {e}")
                break  # Exit the loop on other errors


def start_reading(window):
    """
        Function to start the rfid reading, and it keeps on listening the response from rfid reader until stop command
        is sent.
        :param window: The terminal window of the gui to display the information.
    """
    global reading_active
    reading_active = True
    threading.Thread(target=read_continuous_rfid_res, args=(window,),  daemon=True).start()


def stop_reading():
    """
        Function to stop the rfid reading.
    """
    global reading_active, global_net_conn
    # First, signal the loop to stop by setting the flag to False
    reading_active = False

    # calling stop_reading_mode to send the command to the RFID reader
    if global_net_conn:
        stop_reading_mode(global_net_conn, 'network')
        print('Stopped')


def launch_gui():
    """
        Function to launch the gui panel
    """
    global global_net_conn  # Reference the global connection object

    sg.theme('DarkGrey13')

    layout = [
        [sg.Text('Select RFID:'), sg.OptionMenu(
            ('192.168.101.3', '192.168.102.3', '192.168.103.3', '192.168.104.3', '192.168.105.3', '192.168.106.3',
             '192.168.108.3', '192.168.11.3', '192.168.12.3', '192.168.13.3', '192.168.14.3', '192.168.15.3',
             '192.168.16.3', '192.168.18.3', '192.168.1.200'), key='IP_Selection', enable_events=True)],
        [sg.Button('Connect', key='Connection', disabled=False),
         sg.Button('Disconnect', key='Disconnection', disabled=False)],
        [sg.Button('Start', key='Start Reading', visible=False, disabled=False),
         sg.Button('Stop', key='Stop Reading', visible=False, disabled=False, pad=((26, 0), (3, 3)))],
        [sg.Multiline(default_text='', size=(100, 20), key='TERMINAL', autoscroll=True, background_color='black',
                      text_color='white')],
    ]

    window = sg.Window(title="RFID Reader Program", layout=layout, margins=(10, 10), resizable=True)

    while True:
        event, values = window.read()
        if event == sg.WINDOW_CLOSED:
            break
        elif event == 'Connection':
            if values['IP_Selection']:  # Check if an IP address is selected
                ip, port = values['IP_Selection'], 2022  # Assuming 2022 as fixed port
                global_net_conn = open_net_connection(ip, port)  # Open connection
                if global_net_conn:
                    window['TERMINAL'].update(f"Connected to {ip}:{port}\n", append=True)
                    window['Start Reading'].update(visible=True, disabled=False)
                    window['Stop Reading'].update(visible=True, disabled=False)
                    window['Connection'].update(disabled=True)
                    window['Disconnection'].update(disabled=False)
                else:
                    window['TERMINAL'].update(f"Failed to connect to {ip}:{port}\n", append=True)
            else:
                sg.popup("No IP address selected. Please select an IP address before connecting.")

        elif event == 'Disconnection':
            if global_net_conn:
                global reading_active
                close_network_connection(global_net_conn)  # Close connection
                reading_active = False
                window['TERMINAL'].update(f"Connection is successfully closed\n", append=True)
                window['Start Reading'].update(visible=False, disabled=True)
                window['Stop Reading'].update(visible=False, disabled=True)
                window['Disconnection'].update(disabled=True)
                window['Connection'].update(disabled=False)
                global_net_conn = None
            else:
                window['TERMINAL'].update("No active connection to close.\n", append=True)
                sg.popup("No Active connection to close.\n")

        elif event == 'Start Reading':
            if global_net_conn:
                start_reading(window)
                window['TERMINAL'].update("Started RFID reading...\n", append=True)
                window['Stop Reading'].update(disabled=False)
                window['Start Reading'].update(disabled=True)

        elif event == 'Stop Reading':
            if global_net_conn:
                stop_reading()
                window['TERMINAL'].update('Stopped RFID reading...\n', append=True)
                window['Stop Reading'].update(disabled=True)
                window['Start Reading'].update(disabled=False)

        elif event == '-TAG_READ-':  # For displaying the rfid information.
            rfid_tag_data = values[event]  # Extract the RFID tag data from the event values
            window['TERMINAL'].update(f"RFID Tag: {rfid_tag_data}\n", append=True)

    window.close()


if __name__ == '__main__':
    launch_gui()
