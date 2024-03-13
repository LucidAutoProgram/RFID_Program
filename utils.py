from datetime import datetime, timedelta
import asyncio
import tkinter as tk
from PIL import Image, ImageTk
from db_operations import server_connection_params
from rfid_api import open_net_connection

# -------------------- Global Variables declarations ------------------

reading_active = {}  # This dictionary keeps track of the ip addresses of the rfid readers which are in reading mode.
active_connections = {}  # Global storage for active connections


def display_message_and_image(message, image_path, app):
    """
        Function to display the image and message on the gui window.
        :param message: Message to be displayed on the gui window.
        :param image_path: Path of the image.
        :param app: window of the gui.
        :return: None
    """
    # Opening the image file located at `image_path`
    img = Image.open(image_path)

    # Resizing the image to 150x150 pixels using Lanczos resampling for high quality
    img = img.resize((150, 150), Image.Resampling.LANCZOS)

    # Converting the PIL image to a format that Tkinter can use
    photo = ImageTk.PhotoImage(img)

    # Creating a frame within the `app` window to contain the message and image, with specific styling
    message_frame = tk.Frame(app, bg="black", bd=4, relief="groove")

    # Positioning the frame within the window, centered and taking up 80% of the width and 50% of the height
    message_frame.place(relx=0.5, rely=0.6, anchor="center", relwidth=0.8, relheight=0.5)

    # Creating a label within the frame for displaying the image, with a black background
    image_label = tk.Label(message_frame, image=photo, bg="black")

    # Keeping a reference to the image to prevent it from being garbage collected, ensuring it displays properly
    image_label.image = photo

    # Packing the image label on the left side of the frame, with some padding
    image_label.pack(side="left", padx=10)

    # Creating a label within the frame for displaying the message, styled with a white foreground and specific font
    message_label = tk.Label(message_frame, text=message, bg="black", fg="white", font=("Cambria", 12),
                             wraplength=240)  # The `wrap length` determines how text wraps in the label

    # Packing the message label on the right side of the frame, allowing it to expand and fill the available space
    message_label.pack(side="right", expand=True, fill="both", padx=10)


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


async def manage_rfid_readers(reader_ips, app):
    """
        Function to listen response of all the rfid readers.
        :param reader_ips: Ip address of the rfid reader.
        :param app: Gui window.
        :return: None
    """
    tasks = [listen_for_responses(ip, app) for ip in reader_ips]
    await asyncio.gather(*tasks)


async def listen_for_responses(ip_address, app):
    """
        Continuously listen for responses from an RFID reader.
        :param ip_address: Ip address of the rfid reader for which to listen response.
        :param app: Gui window.
        :return: None
    """
    global active_connections, reading_active

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
        current_tags = set()  # Set for storing all the rfid_tags in a particular rfid scan session.
        current_tags_datetime = {}  # To track the first scan datetime of each tag
        scan_end_time = datetime.now() + timedelta(seconds=10)  # After scan end time, it writes all the scanned tag
        # info to the database.
        existing_rfid_tags = set()  # Set containing the existing rfid tags in the database
        all_tags = set()
        all_tags_datetime = {}

        while datetime.now() < scan_end_time:  # Listening to the rfid reader response will continue for 10 seconds

            print(f'--------------Started Listening to the rfid reader responses for ip - {ip_address}---------------')
            try:
                response = await asyncio.wait_for(reader.read(1024), timeout=1)
                if response:
                    # Process response
                    rfid_tag = get_rfid_tag_info(response)
                    print(f'Received rfid tag response in hexadecimal format: {rfid_tag}')
                    if rfid_tag:
                        current_datetime = datetime.now()
                        all_tags.add(rfid_tag)
                        all_tags_datetime[rfid_tag] = datetime.now()

                        device_id_list = server_connection_params.findRFIDDeviceIDInRFIDDeviceDetailsTableUsingDeviceIP(
                            ip_address)
                        if device_id_list:
                            device_id = device_id_list[0][0]

                            location_id_list = server_connection_params.\
                                findLocationIDInRFIDDeviceTableUsingRFIDDeviceID(device_id)

                            if location_id_list:
                                location_id = location_id_list[0][0]

                                material_core_id_list = server_connection_params. \
                                    findMaterialCoreIDInMaterialRollLocationUsingLocationID(location_id)
                                if material_core_id_list:
                                    for material_core_id_tuple in material_core_id_list:
                                        material_core_id = material_core_id_tuple[0]

                                        rfid_tags_list = server_connection_params. \
                                            findRFIDTagInMaterialCoreRFIDUsingMaterialCoreID(material_core_id)
                                        if rfid_tags_list:
                                            for rfid_tags_tuple in rfid_tags_list:
                                                existing_rfid_tags.add(rfid_tags_tuple[0])

                        print('Existing rfid tags ', existing_rfid_tags)

                        # Process only new and unique RFID
                        if rfid_tag and rfid_tag not in current_tags and rfid_tag not in existing_rfid_tags:
                            current_tags.add(rfid_tag)
                            current_tags_datetime[rfid_tag] = current_datetime
                            print(f'New unique RFID tag received: {rfid_tag}')

                        elif not rfid_tag:
                            print(f"Received an empty RFID tag response for ip - {ip_address}, ignoring.")

                        else:
                            print(f"RFID tag {rfid_tag} for ip - {ip_address} already exists in the database or is a "
                                  f"duplicate in the current batch.")

                    else:
                        app.after(0, lambda: display_message_and_image(
                            f'NO RESPONSE', "Images/fail.png", app))
                        print(f"NO rfid tags {ip_address}")

                else:
                    # Handle connection closed
                    app.after(0, lambda: display_message_and_image(
                        f'NO RESPONSE', "Images/fail.png", app))
                    print(f"Connection closed by reader {ip_address}")
                    break

            except asyncio.TimeoutError:
                # No data received but still within the scanning window, continue listening
                continue

            except Exception as e:
                print(f"Error listening to {ip_address}: {e}")
                break

        # Checking if any tags have been received in the current RFID reader session
        if all_tags:
            # Checking if the number of tags in all_tags is equal to or more than three
            if len(all_tags) >= 3:
                # Finding the intersection of all_tags and existing_rfid_tags to identify any repeated tags
                tags_repeated = all_tags.intersection(existing_rfid_tags)

                # If there are repeated tags even one tag then , it implies some or all tags have been scanned before
                if tags_repeated:
                    print('Core is already scanned.')
                    await processCoreInfoToMaterialCoreRFIDTable(ip_address, all_tags, all_tags_datetime, app,
                                                                 existing_rfid_tags, all_tags)
                else:
                    # If there are no repeated tags, it means all current tags are new
                    await processCoreInfoToMaterialCoreRFIDTable(ip_address, current_tags, current_tags_datetime,
                                                                 app, existing_rfid_tags, all_tags)
            else:
                # If there are less than 3 tags, calculating how many more are needed to proceed
                tags_needed = 3 - len(all_tags)
                # Prompting the user that more tags are needed for processing
                app.after(0, lambda: display_message_and_image(
                    f'RFID tags are less than 3. Need {tags_needed} more tag', "Images/fail.png", app))


async def processCoreInfoToMaterialCoreRFIDTable(ip_address, tags, tag_scan_time, app, existing_tags,
                                                 all_received_tags):
    """
       Function to process the core specs and rfid tag and its scan time info to the database.
       :param ip_address: The ip address of the rfid reader.
       :param tags: Rfid tags scanned by the reader.
       :param tag_scan_time: Scanning time of the rfid tags.
       :param existing_tags: Tags which are already present in the database.
       :param all_received_tags: All the rfid tags which are received in the particular rfid scan session.
    """

    device_id = server_connection_params.findRFIDDeviceIDInRFIDDeviceDetailsTableUsingDeviceIP(ip_address)[0][0]
    location_id = server_connection_params.findLocationIDInRFIDDeviceTableUsingRFIDDeviceID(device_id)[0][0]

    # First, check if any of the tags already exists in the database
    existing_core_id = None
    for tag in tags:
        result = server_connection_params.findMaterialCoreIDFromMaterialCoreRFIDTableUsingRFIDTag(tag)
        if result:
            existing_core_id = result[0][0]
            print(existing_core_id, "core_id")
            break  # Break the loop if any of the tags is found in the database

    # If an existing rfid tag exists in the database use its existing Core_ID
    if existing_core_id:
        core_id = existing_core_id
        app.after(0, lambda: display_message_and_image(
            f'Core is already scanned and assigned Core ID is {core_id} and is ready to use',
            "Images/pass.png", app))
        app.after(5000, lambda: display_message_and_image(
            f'Please put Core For scanning', "Images/core.png", app))

        # Case for handling missing tags
        missing_tags = existing_tags - all_received_tags
        if missing_tags:  # If there ar missing tags, let's say when reusing the core.
            for missing_tag in missing_tags:
                server_connection_params.updateMaterialCoreRFIDEndInMaterialCoreRFIDTable(datetime.now(), missing_tag,
                                                                                          core_id)

    else:
        # If no existing RFID tag found in the database, then create a new Material_Core_ID
        # Fetch the current max core_id.
        max_core_id = server_connection_params.findMaxCoreIdFromMaterialCoreRFIDTable()

        if max_core_id is not None:
            core_id = max_core_id + 1  # Incrementing by 1 from the current maximum core id in the db, to create a new
            #  core id.
            server_connection_params.writeToMaterialCoreTable(core_id)
            server_connection_params.writeToMaterialRollLocation(core_id, location_id)

            # Prompting the user that new core is successfully scanned and new core id is assigned
            app.after(0, lambda: display_message_and_image(
                f'Core is successfully scanned. \n Assigned Core ID is {core_id}. \n Core is ready to use.',
                "Images/pass.png", app))

            app.after(5000, lambda: display_message_and_image(
                f'Please put Core For scanning', "Images/core.png", app))

        else:
            # Create a new core_id, if not even a single core_id is found in the db
            core_id = 1
            server_connection_params.writeToMaterialCoreTable(core_id)
            server_connection_params.writeToMaterialRollLocation(core_id, location_id)

            # Prompting the user that new core is successfully scanned and new core id is assigned
            app.after(0, lambda: display_message_and_image(
                f'Core is successfully scanned. \n Assigned Core ID is {core_id}. \n Core is ready to use.',
                "Images/pass.png", app))

            app.after(5000, lambda: display_message_and_image(
                f'Please put Core For scanning', "Images/core.png", app))

    for tag in tags:
        try:
            # Fetch the correct scan time for each individual tag
            rfid_tag_start = tag_scan_time[tag]  # Time when the tag was first scanned.
            server_connection_params.writeToMaterialCoreRFIDTable(tag, core_id, rfid_tag_start)
            print(f'Wrote {tag} to database with core id {core_id}, scan time {rfid_tag_start}')

        except Exception as e:
            print(f"Error processing tag {tag}: {e}")
            app.after(0, lambda: display_message_and_image(f"Error processing tag {tag}: {e}", "Images/fail.png", app))
