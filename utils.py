from datetime import datetime, timedelta
import asyncio
import tkinter as tk
from PIL import Image, ImageTk
from db_operations import server_connection_params
from rfid_api import open_net_connection

# -------------------- Global Variables declarations ------------------

reading_active = {}  # This dictionary keeps track of the ip addresses of the rfid readers which are in reading mode.
active_connections = {}  # Global storage for active connections


def update_message_label(message_labels, location, new_message,color):
    """
    Update the text of the message label for a specific location.

    :param message_labels: Dictionary of message label references keyed by location.
    :param location: Location of the RFID reader.
    :param new_message: New message text to display.
    """
    if location in message_labels:
        message_label, location_label = message_labels[location]
        message_label.config(text=new_message, bg=color)
        location_label.config(bg=color)  # Assuming you also want to change the location label's background
    else:
        print(f"No message label for location: {location}")


def get_rfid_tag_info(response):
    """
        Function to extract the rfid reader tag info from the response returned from the rfid reader after sending the
        start reading command by the start_reading_mode function.
        :param response: It is the response returned by the reader.
        :return: Hexadecimal formatted rfid tag.
    """
    if not response or len(response) < 11:
        return None

    epc_len = response[10]  # EPC LEN at byte index 10
    epc_data_start_index = 11  # EPC data starts at index 11
    epc_data_end_index = epc_data_start_index + epc_len
    epc_data = response[epc_data_start_index:epc_data_end_index]  # The raw rfid tag info.
    epc_hex = ''.join(format(x, '02x') for x in epc_data)  # Convert to hexadecimal string
    return epc_hex


async def manage_rfid_readers(reader_ips, reader_locations, app, message_labels):
    """
        Function to listen response of all the rfid readers.
        :param reader_ips: Ip address of the rfid reader.
        :param reader_locations: location of the rfid readers.
        :param app: Gui window.
        :return: None
    """

    tasks = [listen_for_extruder_reader_responses(ip, location, app, message_labels) for ip, location in zip(reader_ips,
                                                                                                             reader_locations)]
    await asyncio.gather(*tasks)


async def listen_for_extruder_reader_responses(ip_address, location, app, message_labels):
    """
        Continuously listen for responses from an RFID reader on the extruder side.
        :param ip_address: Ip address of the rfid reader for which to listen response.
        :param location: Location of the rfid reader.
        :param app: Gui window.
        :return: None
    """
    global active_connections, reading_active

    if location.startswith('Extruder'):  # Only continue if the reader is located in one of extruder location.

        # Ensure a connection is established
        if ip_address not in active_connections:
            reader, writer = await open_net_connection(ip_address, port=2022)
            if reader and writer:
                active_connections[ip_address] = (reader, writer)
                reading_active[ip_address] = True  # Enabling the reader in the reading mode
                print(f"Connection established for listening on {ip_address}")
            else:
                print(f"Failed to establish connection for listening on {ip_address}")
                return

        reader, _ = active_connections[ip_address]
        while reading_active[ip_address]:  # If the reader is in reading mode.
            scan_end_time = datetime.now() + timedelta(seconds=10)  # After scan end time, it writes all the scanned tag

            while datetime.now() < scan_end_time:  # Listening to the rfid reader response will continue for 10 seconds

                print(f'--------------Started Listening to the rfid reader responses for ip - {ip_address}------------')
                try:
                    response = await asyncio.wait_for(reader.read(1024), timeout=1)
                    if response:  # If reader sent the response.
                        # Process response
                        rfid_tag = get_rfid_tag_info(response)
                        print(f'Received rfid tag response in hexadecimal format: {rfid_tag}')
                        if rfid_tag:
                            # Below checking if any rfid tag scanned is having a core id in the database
                            existing_core = server_connection_params. \
                                findMaterialCoreIDFromMaterialCoreRFIDTableUsingRFIDTag(rfid_tag)
                            if existing_core:  # If having existing core id for the rfid tag scanned, then that means
                                app.after(0, lambda: update_message_label(message_labels, location,
                                                                          'Core scanned and is good to use.','green'))
                                print(f"Core is scanned on the core station")

                            else:  # If no existing core id is found for the rfid tag scanned, then that means the core
                                # is not scanned on the core station
                                app.after(0, lambda: update_message_label(message_labels, location,
                                                                          'Core is not scanned .','red'))
                                print(f"Please scan the core on the core station")

                        else:
                            app.after(0, lambda: update_message_label(message_labels, location,
                                                                      'NO tags.','red'))
                            print(f"NO rfid tags {ip_address}")

                    else:
                        # Handle connection closed
                        # app.after(0, lambda: update_treeview_with_locations(tree, ip_address,
                        #                                                     f'Connection closed by reader.'))
                        print(f"Connection closed by reader {ip_address}")
                        break

                except asyncio.TimeoutError:
                    # No data received but still within the scanning window, continue listening
                    continue

                except Exception as e:
                    print(f"Error listening to {ip_address}: {e}")
                    break

    else:
        print(f'Ip - {ip_address} is not one of the extruder side reader.')
