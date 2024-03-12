import asyncio
from datetime import datetime, timedelta

from db_operations import server_connection_params
from rfid_api import open_net_connection

# -------------------- Global Variables declarations ------------------

reading_active = {}  # This dictionary keeps track of the ip addresses of the rfid readers which are in reading mode.
active_connections = {}  # Global storage for active connections


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


async def manage_rfid_readers(reader_ips):
    tasks = [listen_for_responses(ip) for ip in reader_ips]
    await asyncio.gather(*tasks)


async def listen_for_responses(ip_address):
    """
        Continuously listen for responses from an RFID reader.
        :param ip_address: Ip address of the rfid reader for which to listen response.
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
        # print(f'Reading is active for ip - {ip_address}')
        # print(f'Current date time - {datetime.now()} and scan end time is {scan_end_time}')

        while datetime.now() < scan_end_time:  # Listening to the rfid reader response will continue for 10 seconds

            print(f'--------------Started Listening to the rfid reader responses for ip - {ip_address}---------------')
            try:
                response = await asyncio.wait_for(reader.read(1024), timeout=1)
                if response:
                    # Process response
                    rfid_tag = get_rfid_tag_info(response)
                    print(f'Received rfid tag response in hexadecimal format: {rfid_tag}')
                    current_datetime = datetime.now()

                    device_id_list = server_connection_params.findRFIDDeviceIDInRFIDDeviceDetailsTableUsingDeviceIP(
                        ip_address)
                    if device_id_list:
                        device_id = device_id_list[0][0]

                        location_id_list = server_connection_params.findLocationIDInRFIDDeviceTableUsingRFIDDeviceID(
                            device_id)

                        if location_id_list:
                            location_id = location_id_list[0][0]

                            material_core_id_list = server_connection_params.\
                                findMaterialCoreIDInMaterialRollLocationUsingLocationID(location_id)
                            if material_core_id_list:
                                for material_core_id_tuple in material_core_id_list:
                                    material_core_id = material_core_id_tuple[0]

                                    rfid_tags_list = server_connection_params.\
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
                    # Handle connection closed
                    print(f"Connection closed by reader {ip_address}")
                    break

            except asyncio.TimeoutError:
                # No data received but still within the scanning window, continue listening
                continue

            except Exception as e:
                print(f"Error listening to {ip_address}: {e}")
                break

        if len(current_tags) >= 3:  # If length of the tags found in the scan is greater than 3.
            # Process tags after each scanning cycle - this is only for
            print(f'Current tags received - {current_tags} for ip - {ip_address}')
            await processCoreInfoToMaterialCoreRFIDTable(ip_address, current_tags, current_tags_datetime)

        else:
            print(f' tags found in the scan session of the rfid reader with ip - {ip_address} is less than 3')


async def processCoreInfoToMaterialCoreRFIDTable(ip_address, tags, tag_scan_time):
    """
        Function to process the core specs and rfid tag and its scan time info to the database.
        :param ip_address: The ip address of the rfid reader.
        :param tags: Rfid tags scanned by the reader.
        :param tag_scan_time: Scanning time of the rfid tags.
    """
    device_id = server_connection_params.findRFIDDeviceIDInRFIDDeviceDetailsTableUsingDeviceIP(ip_address)[0][0]
    location_id = server_connection_params.findLocationIDInRFIDDeviceTableUsingRFIDDeviceID(device_id)[0][0]

    # First, check if any of the tags already exists in the database
    existing_core_id = None
    for tag in tags:
        result = server_connection_params.findMaterialCoreIDFromMaterialCoreRFIDTableUsingRFIDTag(tag)
        if result:
            existing_core_id = result[0][0]
            break  # Break the loop if any of the tags is found in the database

    # If an existing rfid tag exists in the database use its existing Core_ID
    if existing_core_id:
        core_id = existing_core_id

    else:
        # If no existing RFID tag found in the database, then create a new Material_Core_ID

        # Fetch the current max core_id.
        max_core_id = server_connection_params.findMaxCoreIdFromMaterialCoreRFIDTable()

        if max_core_id is not None:
            core_id = max_core_id + 1  # Incrementing by 1 from the current maximum core id in the db, to create a new
            #  core id.
            server_connection_params.writeToMaterialCoreTable(core_id)
            server_connection_params.writeToMaterialRollLocation(core_id, location_id)

        else:
            # Create a new core_id, if not even a single core_id is found in the db
            core_id = 1
            server_connection_params.writeToMaterialCoreTable(core_id)
            server_connection_params.writeToMaterialRollLocation(core_id, location_id)

    for tag in tags:
        try:
            # Fetch the correct scan time for each individual tag
            rfid_tag_start = tag_scan_time[tag]  # Time when the tag was first scanned.
            server_connection_params.writeToMaterialCoreRFIDTable(tag, core_id, rfid_tag_start)
            print(f'Wrote {tag} to database with core id {core_id}, scan time {rfid_tag_start}')
        except Exception as e:
            print(f"Error processing tag {tag}: {e}")