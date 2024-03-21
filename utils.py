from datetime import datetime, timedelta
import asyncio
from db_operations import server_connection_params
from rfid_api import open_net_connection

# -------------------- Global Variables declarations ------------------

reading_active = {}  # This dictionary keeps track of the ip addresses of the rfid readers which are in reading mode.
active_connections = {}  # Global storage for active connections
processed_core_ids = set()  # Keeps track of processed (written) core IDs
location_labels = {}  # dictionary to store location with messages
location_color = {}  # dictionary to store location with locations to update background color


# updating the background color and message for message label
def update_message_label(label, new_text, bg_color):
    """
    Updates the text and background color of a given tkinter label widget.

    :param label: The tkinter label widget to update.
    :param new_text: The new text to display on the label.
    :param bg_color: update the background color.

    """
    label.config(text=new_text, bg=bg_color)


# updating the background color for location label
def update_color(label, bg_color):
    """
    Updates the background color of a given tkinter label widget.

    :param label: The tkinter label widget to update.
    :param bg_color: update the background color.
    """
    label.config(bg=bg_color)


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


async def manage_rfid_readers(reader_ips, reader_locations, app):
    """
        Function to listen response of all the rfid readers.
        :param reader_ips: Ip address of the rfid reader.
        :param reader_locations: location of the rfid readers.
        :param app: Gui window.
        :return: None
    """

    tasks = [listen_for_extruder_reader_responses(ip, location, app) for ip, location in zip(reader_ips,
                                                                                             reader_locations)]
    await asyncio.gather(*tasks)


async def listen_for_extruder_reader_responses(ip_address, location, app):
    """
        Continuously listen for responses from an RFID reader on the extruder side.
        :param ip_address: Ip address of the rfid reader for which to listen response.
        :param location: Location of the rfid reader.
        :param app: Gui window.
        :return: None
    """
    global active_connections, reading_active, processed_core_ids

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
        print(f"Initializing listening for {ip_address}")
        while reading_active[ip_address]:  # If the reader is in reading mode.
            print(f"Reading active for {ip_address}")
            scan_end_time = datetime.now() + timedelta(seconds=10)  # After scan end time, it writes all the scanned tag
            response_received = False  # Initialize the response received flag to False at the start of each scanning
            session_rfid_tags = set()
            all_stored_tags = set()
            all_Tags = server_connection_params.findAllRFIDTagsInMaterialCoreRFID()
            for tags in all_Tags:
                all_stored_tags.add(tags[0])

            while datetime.now() < scan_end_time:  # Listening to the rfid reader response will continue for 10 seconds

                print(f'--------------Started Listening to the rfid reader responses for ip - {ip_address}------------')
                try:
                    response = await asyncio.wait_for(reader.read(1024), timeout=1)
                    if response:  # If reader sent the response.
                        response_received = True  # Set the flag to True since a response was received
                        rfid_tag = get_rfid_tag_info(response)
                        if rfid_tag:
                            session_rfid_tags.add(rfid_tag)
                    else:
                        print("no response")
                        break

                except asyncio.TimeoutError:
                    # No data received but still within the scanning window, continue listening
                    continue

                except Exception as e:
                    print(f"Error listening to {ip_address}: {e}")
                    break

            # Correctly check if all session tags are within the stored tags
            if session_rfid_tags.issubset(all_stored_tags):

                # Below extracting the core id from rfid tags
                for tags in session_rfid_tags:
                    existing_core = server_connection_params. \
                        findMaterialCoreIDFromMaterialCoreRFIDTableUsingRFIDTag(tags)

                    if existing_core:

                        # fetching the last core id attached with those rfid tags
                        material_core_id = existing_core[-1][0]

                        # fetching core location
                        existing_core_location_IDs = (
                            server_connection_params.
                            findLocationIDInMaterialRollLocationUsingMaterialCoreID(
                                material_core_id))

                        if existing_core_location_IDs:
                            print(existing_core_location_IDs, "id")

                            # Determining if the last location ID in the list matches the current location ID
                            last_location_id_in_list = existing_core_location_IDs[-1][0] if existing_core_location_IDs \
                                else None

                            current_location_IDs = server_connection_params.\
                                findLocationIDInRFIDDeviceDetailsUsingDeviceIP(ip_address)

                            if current_location_IDs:
                                # Extract the first Location_ID from the result
                                current_location_ID = current_location_IDs[0][0]

                                # checking the last location if the last location and current location is same then
                                # filter the last location
                                if last_location_id_in_list == current_location_ID:
                                    filtered_core_location_IDs = [id for id in existing_core_location_IDs if
                                                                  id[0] != last_location_id_in_list]
                                else:
                                    filtered_core_location_IDs = existing_core_location_IDs

                                for location_id_tuple in filtered_core_location_IDs:
                                    location_id = location_id_tuple[0]  # Extract the Location_ID
                                    existing_core_locations = \
                                        server_connection_params.findLocationXYZInLocationTableUsingLocationID(
                                            location_id)

                                    for location_tuple in existing_core_locations:
                                        core_location = location_tuple[0]

                                        if core_location.startswith('Extruder'):
                                            print(f"Location ID {location_id} starts with 'Extruder'")

                                            app.after(0, lambda: update_message_label(location_labels[location],
                                                                                      f"Core is not scanned at "
                                                                                      f"core station.\n Scan it at core"
                                                                                      f"Station before using it",
                                                                                      'orange'))
                                            app.after(0, lambda: update_color(location_color[location],
                                                                              "orange"))
                                            print(f"Core is not scanned on the core station")

                                        else:
                                            if core_location.startswith('CoreStation'):
                                                print('Core is scanned on core station')
                                                server_connection_params.writeToMaterialRollTable(material_core_id,
                                                                                                  material_core_id)
                                                server_connection_params.writeMaterialRoleIDToMaterialRollLengthTable(
                                                    material_core_id)

                                                app.after(0, lambda: update_message_label(location_labels[location],
                                                                                          f"Core is  scanned at"
                                                                                          f" core station.\n Good for "
                                                                                          f"roll making",
                                                                                          'green'))
                                                app.after(0, lambda: update_color(location_color[location],
                                                                                  "green"))
                                                print(f"Core is  scanned ")

                                            current_location_IDs = server_connection_params.\
                                                findLocationIDInRFIDDeviceDetailsUsingDeviceIP(ip_address)

                                            if current_location_IDs:
                                                # Extract the first Location_ID from the result
                                                current_location_ID = current_location_IDs[0][0]

                                                # Check if this combination is already in the database
                                                if not server_connection_params.checkExistingRecord(
                                                        material_core_id, current_location_ID):
                                                    # If not, proceed with writing to the database
                                                    server_connection_params.writeToMaterialRollLocation(
                                                        material_core_id, current_location_ID)
                                                    # After writing to the database, adding the core ID to
                                                    # the set of processed IDs
                                                    processed_core_ids.add(current_location_ID)
                                                else:
                                                    print(
                                                        f"Duplicate record not written for Core ID {material_core_id} "
                                                        f"at Location ID"
                                                        f" {current_location_ID}")

            else:

                # If no existing core id is found for the rfid tag scanned, then that means the core
                # is not scanned on the core station
                app.after(0, lambda: update_message_label(location_labels[location],
                                                          f"Core is not scanned at core station.\n Scan it at core "
                                                          f"Station before using it",
                                                          'red'))
                app.after(0, lambda: update_color(location_color[location],
                                                  "red"))

                print(f"Core is  not scanned on the core station")

            if not response_received:
                app.after(0, lambda: update_message_label(location_labels[location],
                                                          f"No Core for Scanning .\n Please put core on {location}"
                                                          f" for scanning.",
                                                          "yellow"))
                app.after(0, lambda: update_color(location_color[location],
                                                  "yellow"))
    else:
        print(f'Ip - {ip_address} is not one of the extruder side reader.')
