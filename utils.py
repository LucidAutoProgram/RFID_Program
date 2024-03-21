import asyncio
import time
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


def update_location_image(location, image_path):
    """
    Updates the image for a given location label.

    :param location: The location identifier for the label to update.
    :param image_path: The path to the new image to display.
    """
    if location in location_lights:
        label = location_lights[location]
        new_image = Image.open(image_path)
        new_image = new_image.resize((20, 20), Image.LANCZOS)  # Adjust size as needed
        photo = ImageTk.PhotoImage(new_image)
        label.config(image=photo)
        label.image = photo  # Keep a reference!
    else:
        print(f"Location label for {location} not found.")


def update_message(label, new_text):
    """
    Updates the roll information

    :param label: The tkinter label widget to update.
    :param new_text: The new text to display on the label.

    """
    label.config(text=new_text)


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


def generateUniqueWorkOrderID():
    """
        Function for generating unique WorkOrder_ID not existing in the db.
        :return: Unique WorkOrder_ID.
    """
    max_wo_id_in_db = server_connection_params.findMaxWorkOrderIDFromWorkOrderMainTable()
    if max_wo_id_in_db:  # If a work order id exists in db
        work_order_id = max_wo_id_in_db + 1
    else:
        work_order_id = 1

    return work_order_id


def generateUniqueWorkOrderNumber():
    """
        Function for generating unique WorkOrder_Number in the db.
        :return: Unique WorkOrder_Number.
    """
    # Fetch existing work order numbers
    existing_numbers = server_connection_params.findAllWorkOrderNumberInWorkOrderMainTable()
    # Extract and convert the numeric part of each work order number to an integer
    existing_numbers_int = [int(number[0].replace('WO-', '')) for number in existing_numbers if
                            number[0].startswith('WO-')]
    # Determine the new work order number by incrementing the maximum existing number
    new_number_part = max(existing_numbers_int, default=0) + 1
    work_order_number = f"WO-{new_number_part}"
    return work_order_number


async def processWorkOrderIDAndNumberToDB(location_id):
    """
        Function to do assignment of WorkOrder_ID, WorkOrder_Number and Location_ID in the db.
    :param location_id: Location id of the roll.
    :return: None
    """
    work_order_id = generateUniqueWorkOrderID()
    work_order_number = generateUniqueWorkOrderNumber()
    server_connection_params.writeToWorkOrderMainTable(work_order_id, work_order_number)
    server_connection_params.writeToWorkOrderAssignmentTable(work_order_id, location_id)
    server_connection_params.writeToWorkOrderScheduledTable(work_order_id)


async def processMaterialRollSpecs(material_roll_id):
    """
        Function to update the roll specs like roll length, number of turns, roll creation start time and end time.
        :param material_roll_id: Roll ID assigned to the roll.
        :return: None
    """
    roll_turns = 0
    roll_length = 0
    # Function for updating the roll making start time
    server_connection_params.updateMaterialRollCreationStartTimeInMaterialRollLengthTable(material_roll_id)
    while roll_turns < 100:
        roll_turns = roll_turns + 1
        roll_length = roll_length + 2  # Increasing the roll length by 2, with an assumption that roll length is
        # increasing by 2 metres with each turn

        # Below updating the roll number of turns and roll length
        server_connection_params. \
            updateMaterialRollLengthAndMaterialRollNumOfTurnsInMaterialRollLengthTable(roll_length, roll_turns,
                                                                                       material_roll_id)
        await asyncio.sleep(1)  # Adding a sleep of 1 sec with an assumption that roll takes 1 second to
        # complete one turn.

    # Function for updating the roll making start time - when roll making is finished
    server_connection_params.updateMaterialRollCreationEndTimeInMaterialRollLengthTable(material_roll_id)


async def manage_rfid_readers(reader_ips, reader_locations, app):
    """
        Function to listen response of all the rfid readers.
        :param reader_ips: Ip address of the rfid reader.
        :param reader_locations: location of the rfid readers.
        :param app : window of GUI
        :return: None
    """

    tasks = [listen_for_extruder_reader_responses(ip, location, app) for ip, location in
             zip(reader_ips, reader_locations)]
    await asyncio.gather(*tasks)


async def listen_for_extruder_reader_responses(ip_address, location, app):
    """
        Continuously listen for responses from an RFID reader on the extruder side.
        :param ip_address: Ip address of the rfid reader for which to listen response.
        :param location: Location of the rfid reader.
        :param app : window of GUI
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
            scan_end_time = datetime.now() + timedelta(seconds=5)  # After scan end time, it writes all the scanned tag
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

                            current_location_IDs = server_connection_params. \
                                findLocationIDInRFIDDeviceDetailsUsingDeviceIP(ip_address)

                            if current_location_IDs:
                                # Extract the first Location_ID from the result
                                current_location_ID = current_location_IDs[0][0]

                                # checking the last location if the last location and current location is same then
                                # filter the last location
                                if last_location_id_in_list == current_location_ID:
                                    filtered_core_location_IDs = [filter_id for filter_id in existing_core_location_IDs
                                                                  if filter_id[0] != last_location_id_in_list]
                                else:
                                    filtered_core_location_IDs = existing_core_location_IDs

                                for location_id_tuple in filtered_core_location_IDs:
                                    location_id = location_id_tuple[0]  # Extract the Location_ID
                                    existing_core_locations = \
                                        server_connection_params.findLocationXYZInLocationTableUsingLocationID(
                                            location_id)

                                    for location_tuple in existing_core_locations:
                                        core_location = location_tuple[0]
                                        print(
                                            f"Processing Location ID {location_id} with Core Location {core_location}")

                                        if core_location.startswith('Extruder'):
                                            print(f"Location ID {location_id} starts with 'Extruder'")
                                            print(f"Core is not scanned on the core station")
                                            app.after(0,
                                                      lambda: update_location_image(location,
                                                                                    'Image/red.png'))
                                            app.after(0,
                                                      lambda: update_message(terminal_message[location],
                                                                             'Core is not scanned on core station.\n'
                                                                             'Scan it on core station before using it.'
                                                                             ''))
                                            app.after(0,
                                                      lambda: update_message(roll_details[location],
                                                                             'No Information to display.'))

                                        else:
                                            if core_location.startswith('CoreStation'):
                                                print(f"Core is  scanned ")

                                                current_location_IDs = server_connection_params. \
                                                    findLocationIDInRFIDDeviceDetailsUsingDeviceIP(ip_address)
                                                print(f'Current location id - {current_location_IDs}')
                                                app.after(0,
                                                          lambda: update_location_image(location,
                                                                                        'Image/green.png'))

                                                if current_location_IDs:
                                                    # Extract the first Location_ID from the result
                                                    current_location_ID = current_location_IDs[0][0]

                                                    # Adding the core ID to the set of processed IDs
                                                    processed_core_ids.add(current_location_ID)

                                                    material_roll_id_list = server_connection_params. \
                                                        findMaterialRollIDInMaterialRollTableUsingMaterialCoreID(
                                                            material_core_id)

                                                    if not material_roll_id_list:  # if the material roll id is not
                                                        # assigned yet, then work order assignment can be made.

                                                        # ------ Doing core id and role id assignment below -------
                                                        server_connection_params.writeToMaterialRollTable(
                                                            material_core_id, material_core_id)
                                                        server_connection_params. \
                                                            writeMaterialRoleIDToMaterialRollLengthTable(
                                                                material_core_id)

                                                        # -------- Doing the work order assignment below ----------

                                                        asyncio.create_task(processWorkOrderIDAndNumberToDB(
                                                            current_location_ID))

                                                        # ------- Assigning the roll specs, like length, turns etc ----
                                                        asyncio.create_task(processMaterialRollSpecs(material_core_id))

                                                    else:
                                                        print('Already assigned roll id and work order to roll, '
                                                              'so cannot reassign a new one.')
                                                        material_roll_id = material_roll_id_list[0][0]
                                                        print(material_roll_id,material_core_id,'id')
                                                        work_order_IDs = server_connection_params. \
                                                            findWorkOrderIDFromWorkOrderAssignmentTableUsingLocationID(
                                                                current_location_ID)

                                                        roll_specs = server_connection_params. \
                                                            findMaterialRollSpecsFromMaterialRollLengthTableUsingMaterialRollID(
                                                                material_roll_id)

                                                        print('Roll Specs', roll_specs)

                                                        roll_len, roll_start_time, roll_end_time, roll_turns = \
                                                            roll_specs[0]

                                                        for ids in work_order_IDs:
                                                            wo_id = ids[0]  # Extract the ID from the tuple
                                                            work_order_numbers = server_connection_params. \
                                                                findWorkOrderNumberFromWorkOrderMainTableUsingWorkOrderID(
                                                                    wo_id)

                                                            for number in work_order_numbers:
                                                                # Extract the work order number from the tuple
                                                                work_order_number = number[0]
                                                                print(
                                                                    f'Work Order ID: {wo_id}, Work Order Number: '
                                                                    f'{work_order_number}')

                                                                app.after(0,
                                                                          lambda: update_message(roll_details[location],
                                                                                                 f'Work Order Number -> '
                                                                                                 f'{work_order_number}\n'
                                                                                                 f'Roll ID ->{material_roll_id}\n'
                                                                                                 f'Location -> {location}\n'
                                                                                                 f'Roll Length -> {roll_len}\n'
                                                                                                 f'Roll Turns -> {roll_turns}\n'
                                                                                                 f'Roll Creation Start time -> '
                                                                                                 f'{roll_start_time}\n'
                                                                                                 f'Roll Creation End Time->'
                                                                                                 f'{roll_end_time}'
                                                                                                 ))

            else:
                print(f"Core is  not scanned on the core station")
                app.after(0,
                          lambda: update_location_image(location,
                                                        'Image/red.png'))
                app.after(0,
                          lambda: update_message(terminal_message[location],
                                                 'Core is not scanned on core station.\n'
                                                 'Scan it on core station before using it.'))
                app.after(0,
                          lambda: update_message(roll_details[location],
                                                 'No Information to display.'))

            if not response_received:
                print('No core for scanning')

    else:
        print(f'Ip - {ip_address} is not one of the extruder side reader.')
