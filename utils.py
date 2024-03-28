import asyncio
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from db_operations import server_connection_params
from rfid_api import open_net_connection
from PIL import Image, ImageTk
from pathlib import Path
import RPi.GPIO as GPIO
from threading import Lock

# -------------------- Global Variables declarations ------------------

processed_core_ids = set()  # Keeps track of processed (written) core IDs
reading_active = {}  # This dictionary keeps track of the ip addresses of the rfid readers which are in reading mode.
active_connections = {}  # Global storage for active connections
location_labels = {}
location_lights = {}
roll_details = {}
terminal_message = {}
should_cancel = False
roll_specs_called = {}  # Dictionary to keep track of whether the processMaterialRollSpecs function is called for particular location
# Global lock for serializing access to GPIO operations
gpio_lock = Lock()

# Define the base directory as the directory where this script is located
base_dir = Path(__file__).parent

# Construct the image paths
green_image_path = base_dir / "Image" / "green.png"
red_image_path = base_dir / "Image" / "red.png"
yellow_image_path = base_dir / "Image" / "yellow.png"

# -------------- GPIO roll length measurement ---------------------

winder_click_pins = {  # Different GPIO pins connected to four different sensors of the extruder station, as there
    # are four winders on the extruder side.
    12: "Winder #01",
    17: "Winder #02",
    5: "Winder #03",
    27: "Winder #04"
}
# Initialize counters for each roll on the winder.
winder_click_counters = {
    "Winder #01": 0,
    "Winder #02": 0,
    "Winder #03": 0,
    "Winder #04": 0
}

mm_per_turn = 100  # Length of material per turn in mm

# Setup GPIO for each roll
GPIO.setmode(GPIO.BCM)  # Broadcom pin-numbering scheme
for pin in winder_click_pins.keys():
    GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)


def click_callback(channel):
    """
        Called when a GPIO event is detected. Updates the counter for the corresponding winder.
        :param channel: The GPIO pin/channel that triggered the event.
    """
    global winder_click_counters
    try:
        with gpio_lock:
            winder_name = winder_click_pins[channel]
            winder_click_counters[winder_name] += 1
            print(f"Turn detected! Total length: {winder_click_counters[winder_name] * mm_per_turn}mm")
    except Exception as e:
        print(f"Error in click_callback for channel {channel}: {e}")


def handle_gpio_blocking(gpio_pin):
    """
        Monitors GPIO pin for falling edge events in a blocking manner.
        :param gpio_pin: The GPIO pin to monitor.
    """
    global should_cancel
    try:
        with gpio_lock:
            print(f'Setting up event detection for GPIO pin {gpio_pin}')
            GPIO.setup(gpio_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)  # Re-setup if pin was cleaned up previously
            GPIO.add_event_detect(gpio_pin, GPIO.FALLING, callback=click_callback, bouncetime=200)

        while not should_cancel:
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("GPIO monitoring interrupted by keyboard")
    except Exception as e:
        print(f"Error in handle_gpio_blocking for GPIO pin {gpio_pin}: {e}")
    finally:
        with gpio_lock:
            # GPIO.cleanup()
            GPIO.cleanup(pin)


async def handle_gpio_async(gpio_pin):
    """
        Wrapper async function to run the blocking GPIO function in a separate thread
        :param gpio_pin: GPIO pin of the raspberry pi.
        :return: None
    """
    global should_cancel
    loop = asyncio.get_running_loop()
    with ThreadPoolExecutor() as pool:
        print(f'Calling handle gpio blocking - gpio {gpio_pin}')
        await loop.run_in_executor(pool, handle_gpio_blocking, gpio_pin)


async def remove_event_detect_async(gpio_pin):
    """
        Asynchronously removes event detection for a GPIO pin.
        :param gpio_pin: The GPIO pin for which to remove event detection.
    """
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, remove_event_detect, gpio_pin)


def remove_event_detect(gpio_pin):
    """
        Removes event detection for a specified GPIO pin.
        :param gpio_pin: The GPIO pin for which to remove event detection.
    """
    try:
        with gpio_lock:
            GPIO.setmode(GPIO.BCM)  # Re-assert GPIO mode to ensure correct state
            GPIO.remove_event_detect(gpio_pin)
            print(f"Event detection removed for GPIO pin {gpio_pin}")
    except Exception as e:
        print(f"Error removing event detection for GPIO pin {gpio_pin}: {e}")


async def cancel_gpio_task(gpio_task, gpio_pin):
    """
        Cancels the GPIO monitoring task and performs necessary cleanup.
        :param gpio_task: The asyncio task associated with GPIO monitoring to be canceled.
        :param gpio_pin: The GPIO pin associated with the task to remove event detection.
    """
    global should_cancel
    # Signal the blocking function to stop
    should_cancel = True
    print('Cancellation flag set for GPIO task')

    # Now cancel the asyncio task
    gpio_task.cancel()
    try:
        await gpio_task
        print('GPIO task cancelled successfully')
    except asyncio.CancelledError:
        print("GPIO task acknowledged cancellation")

    # Perform GPIO cleanup by removing event detection asynchronously
    try:
        await remove_event_detect_async(gpio_pin)
    except Exception as e:
        print(f"Error during GPIO cleanup for pin {gpio_pin}: {e}")


async def processMaterialRollSpecs(material_roll_id, location):
    """
        Function to update the roll specs like roll length, number of turns, roll creation start time and end time.
        :param material_roll_id: Roll ID assigned to the roll.
        :param location: Location of the roll.
        :return: None
    """
    global winder_click_counters  # Global dictionary storing the winder location as key and counter count as value

    gpio_pin = None
    # Determine the GPIO pin based on the winder location
    if location in winder_click_pins.values():
        gpio_pin = [pin for pin, name in winder_click_pins.items() if name == location][0]

    if gpio_pin is not None:
        winder_click_counters[location] = 0

        print(f'Calling gpio async with gpio pin - {gpio_pin} for location - {location}')

        # Create and start the GPIO monitoring task
        gpio_task = asyncio.create_task(handle_gpio_async(gpio_pin))

        # update roll creation start time
        server_connection_params.updateMaterialRollCreationStartTimeInMaterialRollLengthTable(material_roll_id)

        # Here counting clicks are 0 when this function is called
        previous_click_count = -1
        print('Location in process material roll specs - ', location)
        print(f'Counter value for location - {location} is {winder_click_counters[location]}')

        try:
            while True:
                print(
                    f'Counter value in the while loop for location - {location}-  is {winder_click_counters[location]}')
                await asyncio.sleep(0.5)  # Poll the click_count every half second to see if it's still changing
                if winder_click_counters[location] == -1:
                    print(f"Exiting loop for {location} as no core is present for scanning.")
                    break  # Exit the loop if no core for scanning

                current_click_count = winder_click_counters[location]
                print(f'Current click count for location - {location} is - {current_click_count}')
                if current_click_count != previous_click_count:  # If there's a new click, i.e. new turn has been made by the roll, update the database
                    roll_length = current_click_count * mm_per_turn  # Calculate total length based on clicks
                    # Update the roll number of turns and roll length in the database
                    print('Roll length before updation - ', roll_length)
                    server_connection_params.updateMaterialRollLengthAndMaterialRollNumOfTurnsInMaterialRollLengthTable(
                        roll_length, current_click_count, material_roll_id)
                    previous_click_count = current_click_count  # Update the previous click count for the next iteration
                elif winder_click_counters[location] == -1:
                    # Break the loop immediately if the counter is set to -1, indicating no more processing is needed
                    print(f"Exiting loop for {location} as the counter is set to -1.")
                    break

            # After the loop completes (when click_count is -1), considering the rolling process done because there is no more
            # roll.
            # Update the roll making end time - when roll making is finished
            server_connection_params.updateMaterialRollCreationEndTimeInMaterialRollLengthTable(material_roll_id)

        except Exception as e:
            print(f"Error during material roll specs processing for {location}: {e}")

        # Cancel the GPIO monitoring task and perform cleanup
        await cancel_gpio_task(gpio_task, gpio_pin)
        print(f"Finished processing roll {material_roll_id}")

        # try:
        #     # Wait for the task to complete with a timeout (e.g., 5 seconds)
        #     await asyncio.wait_for(gpio_task, timeout=5)
        #     print('Awaited gpio task')
        # except asyncio.CancelledError:
        #     print("GPIO monitoring stopped cleanly.")
        # except TimeoutError:
        #     print("GPIO task did not cancel cleanly within timeout period.")

    else:
        print(f'Invalid location provided: {location}')


# async def processMaterialRollSpecs(material_roll_id):
#     """
#         Function to update the roll specs like roll length, number of turns, roll creation start time and end time.
#         :param material_roll_id: Roll ID assigned to the roll.
#         :return: None
#     """
#     roll_turns = 0
#     roll_length = 0
#     # Function for updating the roll making start time
#     server_connection_params.updateMaterialRollCreationStartTimeInMaterialRollLengthTable(material_roll_id)
#     while roll_turns < 100:
#         roll_turns = roll_turns + 1
#         roll_length = roll_length + 2  # Increasing the roll length by 2, with an assumption that roll length is
#         # increasing by 2 metres with each turn
#
#         # Below updating the roll number of turns and roll length
#         server_connection_params. \
#             updateMaterialRollLengthAndMaterialRollNumOfTurnsInMaterialRollLengthTable(roll_length, roll_turns,
#                                                                                        material_roll_id)
#         await asyncio.sleep(1)  # Adding a sleep of 1 sec with an assumption that roll takes 1 second to
#         # complete one turn.
#
#     # Function for updating the roll making start time - when roll making is finished
#     server_connection_params.updateMaterialRollCreationEndTimeInMaterialRollLengthTable(material_roll_id)


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


async def processWorkOrderIDAndNumberToDB(location_id, roll_id):
    """
        Function to do assignment of WorkOrder_ID, WorkOrder_Number and Location_ID in the db.
    :param location_id: Location id of the roll.
    :return: None
    """
    work_order_id = generateUniqueWorkOrderID()
    work_order_number = generateUniqueWorkOrderNumber()
    server_connection_params.writeToWorkOrderMainTable(work_order_id, work_order_number)
    server_connection_params.writeToWorkOrderAssignmentTable(work_order_id, location_id, roll_id)
    server_connection_params.writeToWorkOrderScheduledTable(work_order_id)


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
    global active_connections, reading_active, processed_core_ids, last_core_id, winder_click_counters, roll_specs_called

    if location.startswith('Winder'):  # Only continue if the reader is located in one of extruder winder location.

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
            session_rfid_tags = set()  # All the rfid tags received in the session of inner while loop, are stored in
            # this set.
            all_stored_tags = set()  # All tags stored in the database are present in this set.

            all_Tags = server_connection_params.findAllRFIDTagsInMaterialCoreRFID()
            for tags in all_Tags:
                # Adding all the rfid tags present in the db, in the below set.
                all_stored_tags.add(tags[0])

            while datetime.now() < scan_end_time:  # Listening to the rfid reader for specified scanning time, and
                # then processing the tags to the db, displaying messages accordingly on the gui.

                # print(f'--------------Started Listening to the rfid reader responses for ip - {ip_address}------------')
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

            locations_set = set()  # Set containing all the locations where rfid tag or core is scanned
            core_location_set = set()  # Set containing the location of the core station if the core is scanned
            # on the core station.
            winder_location_set = set()  # Set containing the location of the winders.
            # storing rfid tags with the respective core id
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
                        # fetching core location
                        existing_core_location_IDs = server_connection_params. \
                            findLocationIDInMaterialRollLocationUsingMaterialCoreID(material_core_id)

                        if existing_core_location_IDs:

                            # Determining if the last location ID in the list matches the current location ID
                            last_location_id_in_list = existing_core_location_IDs[-1][0] if existing_core_location_IDs \
                                else None

                            current_location_IDs = server_connection_params. \
                                findLocationIDInRFIDDeviceDetailsUsingDeviceIP(ip_address)

                            if current_location_IDs:
                                # Extract the first Location_ID from the result
                                current_location_ID = current_location_IDs[0][0]

                                # Checking the last location if the last location and current location is same then
                                # filter the last location
                                if last_location_id_in_list == current_location_ID:
                                    filtered_core_location_IDs = [filter_id for filter_id in existing_core_location_IDs
                                                                  if filter_id[0] != last_location_id_in_list]
                                else:
                                    filtered_core_location_IDs = existing_core_location_IDs

                                existing_locations = set()
                                for location_id_tuple in filtered_core_location_IDs:
                                    location_id = location_id_tuple[0]  # Extract the Location_ID
                                    print('filter location', location_id)
                                    all_locations = \
                                        server_connection_params.findLocationXYZInLocationTableUsingLocationID(
                                            location_id)
                                    existing_locations.add(all_locations[0][0])

                                location_name = None
                                print('Existing locations', existing_locations)
                                for location_tuple in existing_locations:

                                    location_name = location_tuple
                                    print('Location name', location_name)
                                    locations_set.add(location_name)

                                    if location_name.startswith('CoreStation'):
                                        core_location_set.add(location_name)

                                    elif location_name.startswith('Winder'):
                                        winder_location_set.add(location_name)

                                    print(
                                        f"Processing Location {location_name}")

                                print('Location set', locations_set)
                                print('Winder set', winder_location_set)
                                print('Core set', core_location_set)

                                # Only if the winder set is not empty and is a subset of location_set, i.e. all the
                                # elements of the winder_location_set are there in location_set.
                                if winder_location_set and winder_location_set.issubset(locations_set):
                                    print(f"Location name {location_name} starts with 'Winder'")
                                    print(f"Core is not scanned on the core station")
                                    app.after(0,
                                              lambda: update_location_image(location,
                                                                            str(red_image_path)))
                                    app.after(0,
                                              lambda: update_message(terminal_message[location],
                                                                     'Core is not scanned on core station.\n'
                                                                     'Scan it on core station before using it.'
                                                                     ''))
                                    app.after(0,
                                              lambda: update_message(roll_details[location],
                                                                     '\n\n\n\n\n\nNo Information to display.'))

                                # Only if the core_location_set is not empty and is a subset of location_set, i.e. all
                                # the elements of the core_location_set are there in location_set.
                                elif core_location_set and core_location_set.issubset(locations_set):
                                    print(f"Core is  scanned ")
                                    current_location_IDs = server_connection_params. \
                                        findLocationIDInRFIDDeviceDetailsUsingDeviceIP(ip_address)
                                    print(f'Current location id - {current_location_IDs}')
                                    app.after(0,
                                              lambda: update_location_image(location,
                                                                            str(green_image_path)))
                                    # app.after(0,
                                    #           lambda: update_message(roll_details[location],
                                    #                                  '\n\n\n\n\nCore is good to use \n Wait for'
                                    #                                  ' details.....'))

                                    if current_location_IDs:
                                        # Extract the first Location_ID from the result
                                        current_location_ID = current_location_IDs[0][0]

                                        # Adding the core ID to the set of processed IDs
                                        processed_core_ids.add(current_location_ID)

                                        material_roll_id_list = server_connection_params. \
                                            findMaterialRollIDInMaterialRollTableUsingMaterialCoreID(
                                            material_core_id)

                                        location_xyz = \
                                        server_connection_params.findLocationXYZInLocationTableUsingLocationID(
                                            current_location_ID)[0][0]

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
                                                current_location_ID, material_core_id))

                                            if not roll_specs_called.get(location_xyz, False):

                                                # ------- Assigning the roll specs, like length, turns etc ----
                                                asyncio.create_task(processMaterialRollSpecs(material_core_id,
                                                                                             location_xyz))

                                                roll_specs_called[location_xyz] = True
                                                print(
                                                    f'Setted the roll_specs_called dict flag for location - {location_xyz} to True')
                                            else:
                                                print(
                                                    f'processMaterialRollSpecs for - {location_xyz} has already been called')

                                            # # Run the synchronous database operation in a separate thread
                                            # executor = ThreadPoolExecutor(max_workers=1)
                                            #
                                            # # -------- Doing the work order assignment below ----------
                                            # await asyncio.get_event_loop(). \
                                            #     run_in_executor(executor,
                                            #                     processWorkOrderIDAndNumberToDB,
                                            #                     current_location_ID)

                                        else:
                                            print('Already assigned roll id and work order to roll, '
                                                  'so cannot reassign a new one.')
                                            material_roll_id = material_roll_id_list[0][0]
                                            work_order_IDs = server_connection_params. \
                                                findWorkOrderIDFromWorkOrderAssignmentTableUsingLocationID(
                                                current_location_ID)

                                            roll_specs = server_connection_params. \
                                                findMaterialRollSpecsFromMaterialRollLengthTableUsingMaterialRollID(
                                                material_roll_id)

                                            if roll_specs and not all(value is None for value in roll_specs[0]):
                                                roll_len, roll_start_time, roll_end_time, roll_turns = roll_specs[0]
                                                wo_id = work_order_IDs[-1][0]  # Extract the ID from the list of tuples
                                                work_order_numbers = server_connection_params. \
                                                    findWorkOrderNumberFromWorkOrderMainTableUsingWorkOrderID(wo_id)

                                                # Extract the work order number from the list of tuples
                                                work_order_number = work_order_numbers[0][0]
                                                print(
                                                    f'Work Order ID: {wo_id}, Work Order Number: {work_order_number}')

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
                                                app.after(0,
                                                          lambda: update_message(terminal_message[location], '\n'))

                                else:
                                    print(f'None of the location matched with location set')
                    else:
                        print("Fail: Not all tags have the same core ID.")
                        app.after(0,
                                  lambda: update_location_image(location,
                                                                str(red_image_path)))
                        app.after(0,
                                  lambda: update_message(terminal_message[location],
                                                         'Core is not scanned on core station.\n'
                                                         'Scan it on core station before using it.'))
                        app.after(0,
                                  lambda: update_message(roll_details[location],
                                                         '\n\n\n\n\n\nNo Information to display.'))

                else:
                    print(f"Core is  not scanned on the core station")
                    app.after(0,
                              lambda: update_location_image(location,
                                                            str(red_image_path)))
                    app.after(0,
                              lambda: update_message(terminal_message[location],
                                                     'Core is not scanned on core station.\n'
                                                     'Scan it on core station before using it.'))
                    app.after(0,
                              lambda: update_message(roll_details[location],
                                                     '\n\n\n\n\n\nNo Information to display.'))

            if not response_received:
                print('No core for scanning')
                # When there is no core for scanning on any winder, setting the click_count to -1 for that particular
                # winder.
                winder_click_counters[location] = -1
                print(
                    f'Setting counter value to {winder_click_counters[location]} for location - {location} since no response received.')

                roll_specs_called[
                    location] = False  # Setting the flag to False since gpio task for that location roll which has no response is closed.
                print(f'Setted the roll_specs_called dict flag for location - {location} to False')

                # Remove event detect for the specific GPIO pin as it's no longer needed
                # gpio_pin = next(key for key, value in winder_click_pins.items() if value == location)
                # print(F'Removing event for location - {location} with gpio pin - {gpio_pin}')
                # GPIO.remove_event_detect(gpio_pin)

                app.after(0,
                          lambda: update_location_image(location, str(yellow_image_path)))
                app.after(0,
                          lambda: update_message(terminal_message[location], '\n'))
                app.after(0,
                          lambda: update_message(roll_details[location], '\n\n\n\n\n\nNo Roll on the Winder.'))

    else:
        print(f'Ip - {ip_address} is not one of the extruder side reader.')
