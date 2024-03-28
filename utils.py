import asyncio
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta

from db_operations import server_connection_params
from rfid_api import open_net_connection
from PIL import Image, ImageTk

# -------------------- Global Variables declarations ------------------

processed_core_ids = set()  # Keeps track of processed (written) core IDs
reading_active = {}  # This dictionary keeps track of the ip addresses of the rfid readers which are in reading mode.
active_connections = {}  # Global storage for active connections
location_labels = {}
location_lights = {}
roll_details = {}
terminal_message = {}
last_core_id = None
processed_work_orders = set()  # Keeps track of processed (inserted) work order numbers


def reapply_row_color_tags(table):
    """
    Reapplies color tags to all rows in the table to ensure even rows are light grey and odd rows are white.
    """
    even = True  # Start with even since we're zero-indexed
    for item in table.get_children():
        color_tag = 'evenrow' if even else 'oddrow'
        table.item(item, tags=(color_tag,))
        even = not even  # Toggle between even and odd


def insert_or_update_treeview_row(table, work_order_name, material_roll_id, roll_len, roll_enter_time, location_name,
                                  roll_end_time):
    # No need for a persistent counter anymore
    print(f"Searching for Work Order: {work_order_name}, Roll ID: {material_roll_id}")

    for item in table.get_children():
        values = table.item(item, 'values')
        print(f"Comparing with Row Values: Work Order: {values[0]}, Roll ID: {values[1]}")
        if str(values[0]) == str(work_order_name) and str(values[1]) == str(material_roll_id):
            print("Found match, checking for end time...")
            if roll_end_time is not None:
                print("End time provided, removing row...")
                table.delete(item)
                reapply_row_color_tags(table)  # Reapply the color tags after deletion
            else:
                print("No end time, updating row (if necessary)...")
                table.item(item, values=(work_order_name, material_roll_id, roll_len, roll_enter_time, location_name))
            return

    if roll_end_time is None:
        print("No match found and no end time, inserting new row...")
        table.insert('', 'end', values=(work_order_name, material_roll_id, roll_len, roll_enter_time, location_name))
        reapply_row_color_tags(table)  # Reapply the color tags after insertion
    else:
        print("End time provided, not inserting new row.")

    # Make sure to configure tags just once, ideally when initializing your GUI or table
    table.tag_configure('evenrow', background='light grey')
    table.tag_configure('oddrow', background='white')


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


def Roll_WorkOrder_Info(app, table):
    storage_roll_specs = server_connection_params.findAllRollIDRollInTimeInStorageRollTable()

    # Initialize an empty list roll information
    formatted_roll_infos = []

    # Initializing the mapping dictionary to map work order with role information
    roll_to_work_order_map = {}

    # Extract values and format them into tuples
    for roll in storage_roll_specs:
        roll_id, roll_enter_time, roll_exit_time, roll_location_id = roll
        formatted_roll_infos.append((roll_id, roll_enter_time, roll_exit_time, roll_location_id))

    # Now, for each tuple in formatted_roll_info's, find the associated work order ID
    for storage_roll_info in formatted_roll_infos:
        roll_id, roll_enter_time, roll_exit_time, roll_location_id = storage_roll_info

        work_order_ids = server_connection_params.findWorkOrderIDFromWorkOrderAssignmentTableUsingRollID(roll_id)
        if work_order_ids:
            work_order_id = work_order_ids[0][0]  # Extract the work order ID from the first tuple

            location_name = server_connection_params.findLocationXYZInLocationTableUsingLocationID(roll_location_id)[0][
                0]

            roll_info = \
                server_connection_params.findMaterialRollSpecsFromMaterialRollLengthTableUsingMaterialRollID(roll_id)[0]
            roll_len, _, _, _ = roll_info

            work_order_name = \
                server_connection_params.findWorkOrderNumberFromWorkOrderMainTableUsingWorkOrderID(work_order_id)[0][0]

            # Add to dictionary
            roll_to_work_order_map[work_order_name] = (
                work_order_name, roll_id, roll_len, roll_enter_time, location_name, roll_exit_time)
        else:
            print(f"No work order ID found for roll ID {roll_id}")
            roll_to_work_order_map[roll_id] = None  # Use None as a placeholder for no ID found

    # Insert data into the table
    for _, details in roll_to_work_order_map.items():
        if details is not None:
            # work_order_name, material_roll_id, roll_len, roll_enter_time, location_name,roll_exit_time = details
            # # insert_data_into_table(app, table, work_order_name, material_roll_id, roll_len, roll_enter_time,
            # #                        location_name)
            insert_or_update_treeview_row(table, *details)


async def manage_rfid_readers(reader_ips, reader_locations, app, table):
    """
        Function to listen response of all the rfid readers.
        :param reader_ips: Ip address of the rfid reader.
        :param reader_locations: location of the rfid readers.
        :param app : window of GUI
        :return: None
    """

    tasks = [listen_for_extruder_reader_responses(ip, location, app, table) for ip, location in
             zip(reader_ips, reader_locations)]
    await asyncio.gather(*tasks)


async def listen_for_extruder_reader_responses(ip_address, location, app, table):
    """
        Continuously listen for responses from an RFID reader on the extruder side.
        :param ip_address: Ip address of the rfid reader for which to listen response.
        :param location: Location of the rfid reader.
        :param app : window of GUI
        :return: None
    """
    global active_connections, reading_active, processed_core_ids, last_core_id

    if location.startswith('Storage'):  # Only continue if the reader is located in one of extruder winder location.

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
            scan_end_time = datetime.now() + timedelta(seconds=5)  # After scan end time, it writes all the scanned tag
            session_rfid_tags = set()  # All the rfid tags received in the session of inner while loop, are stored in
            all_stored_tags = set()  # All tags stored in the database are present in this set.

            all_Tags = server_connection_params.findAllRFIDTagsInMaterialCoreRFID()
            for tags in all_Tags:
                # Adding all the rfid tags present in the db, in the below set.
                all_stored_tags.add(tags[0])

            while datetime.now() < scan_end_time:  # Listening to the rfid reader for specified scanning time, and
                # then processing the tags to the db, displaying messages accordingly on the gui.

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

            tag_to_last_core_id = {}
            material_core_id = None

            # Correctly check if all session tags are within the stored tags in the db.
            if session_rfid_tags:
                if session_rfid_tags.issubset(all_stored_tags):

                    # Below extracting the core id from rfid tags
                    for tags in session_rfid_tags:
                        existing_core = server_connection_params. \
                            findMaterialCoreIDFromMaterialCoreRFIDTableUsingRFIDTag(tags)
                        if existing_core:
                            # If a core ID is found, extract the last core ID from the results
                            last_core_id = existing_core[-1][0]
                            # Map the current tag to its corresponding core ID in the dictionary
                            tag_to_last_core_id[tags] = last_core_id

                            material_core_id = last_core_id
                        else:
                            # Handling the case where no core IDs were found for the tag
                            tag_to_last_core_id[tags] = 'No associated Core ID'

                    # Converting the dictionary values (core IDs) to a list
                    core_ids = list(tag_to_last_core_id.values())
                    print(core_ids, 'core_ids')

                    # Checking if the list of core IDs does not contain the placeholder for missing IDs
                    # and all entries in the list are identical (implying all tags have the same core ID)
                    if 'No associated Core ID' not in core_ids and len(set(core_ids)) == 1:
                        print("Pass: All tags have the same core ID.")

                        current_location_IDs = server_connection_params. \
                            findLocationIDInRFIDDeviceDetailsUsingDeviceIP(ip_address)

                        print('Current location ids', current_location_IDs)

                        if current_location_IDs:
                            # Extract the first Location_ID from the result
                            current_location_ID = current_location_IDs[0][0]
                            print('Current location id value ', current_location_ID)
                            # Fetching Location Name using Location ID
                            current_location = \
                                server_connection_params.findLocationXYZInLocationTableUsingLocationID(
                                    current_location_ID)
                            print('Current location list', current_location)

                            # Extract Current Location Name
                            current_location_name = current_location[0][0]
                            print('Current location name', current_location_name)

                            # Fetching Roll_ID from Material roll Table
                            material_roll_id_list = server_connection_params. \
                                findMaterialRollIDInMaterialRollTableUsingMaterialCoreID(
                                material_core_id)
                            print('Material roll id list', material_roll_id_list)

                            # Extracting Roll ID from Tuple
                            material_roll_id = material_roll_id_list[0][0]
                            print('Material roll id ', material_roll_id)

                            if current_location_name.startswith('Storage #IN'):
                                # Fetching Work_order_Id from WorkOrderAssignmentTable
                                work_order_IDs = server_connection_params. \
                                    findWorkOrderIDFromWorkOrderAssignmentTableUsingRollID(
                                    material_roll_id)

                                # Extract the ID from the list of tuples
                                wo_id = work_order_IDs[0][0]

                                # Fetching Work Order from WorkOrder_main
                                work_order_numbers = server_connection_params. \
                                    findWorkOrderNumberFromWorkOrderMainTableUsingWorkOrderID(wo_id)

                                # Fetching Roll Information from WorkOrderAssignmentTable
                                roll_specs = server_connection_params. \
                                    findMaterialRollSpecsFromMaterialRollLengthTableUsingMaterialRollID(
                                    material_roll_id)
                                roll_len, roll_start_time, roll_end_time, roll_turns = roll_specs[0]

                                # Extract the work order number from the list of tuples
                                work_order_number = work_order_numbers[0][0]

                                # setting the role_in_time to current date and time
                                roll_in_time = datetime.now()

                                # setting the role_out_time to None
                                roll_out_time = None

                                # existing_roll_id_set
                                existing_roll_id_set = set()
                                current_roll_id_set = set()
                                current_roll_id_set.add(material_roll_id)

                                existing_roll_ids = server_connection_params.findAllRollIDRollInTimeInStorageRollTable()
                                for roll_id_tuple in existing_roll_ids:
                                    existing_roll_id = roll_id_tuple[0]
                                    print(existing_roll_id, 'ids')
                                    existing_roll_id_set.add(existing_roll_id)

                                if current_roll_id_set and current_roll_id_set.issubset(existing_roll_id_set):
                                    # The roll ID exists, so update the record.
                                    print(f"Updating existing roll ID: {material_roll_id} for work order"
                                          f" {work_order_number} at location {current_location_name}")
                                    server_connection_params.updateDataForRoll(material_roll_id, roll_in_time,
                                                                               current_location_ID)
                                    Roll_WorkOrder_Info(app, table)
                                else:
                                    # The roll ID does not exist, so insert new record.
                                    print(f"Inserting new roll ID: {material_roll_id}")
                                    server_connection_params.writeRollIDRollInTimeLocationID(material_roll_id,
                                                                                             roll_in_time,
                                                                                             roll_out_time,
                                                                                             current_location_ID)
                                    print( f'Work Order Number: {work_order_number}, Roll ID: {material_roll_id}, '
                                           f'Roll Length: {roll_len}')

                                checkPreviousLocationsIDs = server_connection_params.\
                                    findLocationIDInMaterialRollLocationUsingMaterialCoreID(material_core_id)

                                # Check if there are any previous locations
                                if checkPreviousLocationsIDs:
                                    checkPreviousLocationID = checkPreviousLocationsIDs[-1][0] # Get the last written location
                                    print(checkPreviousLocationID, 'check location')

                                    if str(checkPreviousLocationID) != str(current_location_ID):
                                        server_connection_params.writeToMaterialRollLocation(material_core_id,
                                                                                             current_location_ID)
                                        print(
                                            f"New location {current_location_ID} written for material core ID "
                                            f"{material_core_id}.")
                                    else:
                                        print(
                                            f"Skipped writing location {current_location_ID} for material core ID "
                                            f"{material_core_id} as it matches the last location.")
                                else:
                                    print('ERROR')

                            elif current_location_name.startswith('Storage #OUT'):
                                # setting the role_end_time to current date and time
                                roll_out_time = datetime.now()
                                # write the role end time and location id to roll storage table
                                server_connection_params.updateRollOutTime(material_roll_id, roll_out_time,
                                                                           current_location_ID)

                                # Writing Location of roll in Material roll location Table
                                server_connection_params.writeToMaterialRollLocation(material_core_id,
                                                                                     current_location_ID)
                                print(
                                    f'Updated end date time to {roll_out_time} of roll id {material_roll_id},')
                    else:
                        print("Unknown RFID Tag detected")
                else:
                    print(f"Core is  not scanned on the core station")

            # Function fetches the storage roll information
            Roll_WorkOrder_Info(app, table)
    else:
        print(f'Ip - {ip_address} is not one of the extruder side reader.')
