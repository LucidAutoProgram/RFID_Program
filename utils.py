import asyncio
import io
import platform
from datetime import datetime, timedelta
from queue import Queue
from PIL import Image
import threading
import PySimpleGUI as sg

from db_operations import server_connection_params
from rfid_api import open_net_connection, start_reading_mode, stop_reading_mode

# -------------------- Global Variables declarations ------------------

width = 15  # Width of the image 
height = 15  # Height of the image
active_connections = {}  # Global storage for active connections
global_asyncio_loop = None
reading_active = {}  # This dictionary keeps track of the ip addresses of the rfid readers which are in reading mode.
rfid_tag_response_queue = Queue()  # Queue to store rfid tag response.
rfid_ip_reading_mode = {}  # Dictionary to store the ip address with their reading mode status ('On' or 'Off')
rfid_reader_last_response_time = {}  # # Dictionary to track the last response time for each IP (rfid reader).
rfid_ip_status_color = {}  # Dictionary to store the ip address of the reader as the key and its status color
# (green/yellow/red) as value
stop_button_clicked = False  # To keep track of whether clicked on the stop button or not.


# -------------------- Functions ------------------------------------


def update_tooltip(ip, window, device_location, device_port):
    """
        Function to update tooltip message if their is any upddate.
        :param device_port:
        :param device_location:
        :param ip: Ip address of the rfid reader.
        :param window:  Window of the gui.
    """
    new_reading_mode_status = rfid_ip_reading_mode.get(ip, 'Not Available')
    print(new_reading_mode_status, f"new reading mode status for ip {ip} {device_location}")
    new_tooltip_text = f"IP: {ip}\nLocation: {device_location}\nPort: {device_port}\nReading Mode: " \
                       f"{new_reading_mode_status}"
    window[f'BUTTON_{ip}'].set_tooltip(new_tooltip_text)
    window.refresh()


def update_summary(window, active_connections, ip_addresses_with_location, ip_status_color):
    """
        Function to display the summary of all the rfid readers in the terminal box, it will show whether reader is
        connectable or not, in reader mode or not.
        :param window: Window of the gui.
        :param active_connections: Dictionary containing the ip address with the value True or False based on whether
         they are connected or not.
        :param ip_addresses_with_location: Tuple containing the ip address with their location.
        :param ip_status_color: Ip with its status color i.e. color of the light (green/yellow/red) based on its status.
    """
    online_summary_text = ""
    offline_summary_text = ""

    for ip, location in ip_addresses_with_location:
        if ip in active_connections:
            status_color = ip_status_color.get(ip, 'yellow')  # Assume yellow if unknown
            if status_color == 'green':
                read_mode = "[ONLINE] Reading mode is ON"
            else:
                read_mode = "[ONLINE] Reading mode is OFF"
            online_summary_text += f"{location} (IP: {ip}) {read_mode}\n\n"
        else:
            offline_summary_text += f"{location} (IP: {ip}) [OFFLINE] Connection not established\n\n"

    # Update the summary terminal with online IPs at the top and offline IPs at the bottom
    final_summary_text = online_summary_text + offline_summary_text
    if final_summary_text.strip():
        window['SUMMARY'].update(value=final_summary_text.strip())


def get_image_data(file, maxsize=(width, height)):
    """
        Generating image data using PIL
        :param file: The path of the image.
        :param maxsize: Maximum width and height of the image.
        :return : Binarized png image data.
    """
    img = Image.open(file)
    img.thumbnail(maxsize)
    with io.BytesIO() as output:
        img.save(output, format="PNG")
        data = output.getvalue()
    return data


def create_rfid_layout(ip, status_color, device_location, port):
    """
    Generating layout for each RFID box with location instead of IP on the button.
    :param ip: Ip address of the rfid reader.
    :param status_color: Color to display based on the status of rfid reader (red for unreachable rfid
    reader, yellow for reachable reader and green for reader which is reachable and in reading mode).
    :param device_location: Location of the rfid reader where it is placed.
    :param port: Port of the rfid reader.
    :return: Image and button displaying the status of the rfid and its location.
    """
    reading_mode_status = rfid_ip_reading_mode.get(ip, 'Unknown')

    tooltip_text = f"IP: {ip}\nLocation: {device_location}\nPort: {port}\nReading Mode: {reading_mode_status}"
    return [
        [sg.Image(data=get_image_data(f'images/{status_color}.png', maxsize=(width, height)), background_color='black',
                  key=f'IMAGE_{ip}'),
         sg.Button(device_location, button_color=('white', 'black'), border_width=0, focus=False,
                   key=f'BUTTON_{ip}', tooltip=tooltip_text)

         ],

    ]


# ------------------------ Function for checking the status of rfid reader whether it is online or not.----------------

async def rfid_connectivity_checker(ip_address, number_of_attempts: int = 2):
    """
    Offloads a pinging operation asynchronously.
    Sets fail threshold to 2 attempts.

    :param ip_address: The IP to ping
    :param number_of_attempts: The amount of times to ping before giving up. Default is 2 attempts.

    :return: True if the ping is successful within the given attempts, False otherwise.
    """
    # Determine the number of pings based on the operating system
    if platform.system().lower() == 'windows':
        param = f'-n {number_of_attempts}'  # Windows uses '-n' for count
    else:
        param = f'-c {number_of_attempts}'  # Linux and macOS use '-c' for count
    command = f'ping {param} {ip_address}'

    # Run the ping command asynchronously
    process = await asyncio.create_subprocess_shell(
        command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )

    # Wait for the ping command to complete
    stdout, stderr = await process.communicate()

    # Check the return code to determine success or failure
    return process.returncode == 0


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


def start_asyncio_loop(ip_addresses, queue):
    """
        This function is for performing the asynchronous tasks with the synchronous tasks like with the GUI to run them
        async tasks smoothly.
        :param ip_addresses: List of the ip addresses of the rfid reader.
        :param queue: Queue to store the status of the rfid reader.
    """
    # Access the global variable to store the event loop reference for later access across the application.
    global global_asyncio_loop

    def loop_in_thread(event):
        global global_asyncio_loop  # Ensure we're referring to the global variable

        # Create a new asyncio event loop. This is necessary because the default event loop might not be suitable or
        # available, especially in contexts where the application is running in a thread (e.g., a GUI application
        # thread) or in environments where the default event loop is already running or closed.
        loop = asyncio.new_event_loop()

        # Set the newly created event loop as the current event loop for the current thread.
        # This makes it possible to use asyncio.run_coroutine_threadsafe and other asyncio functionalities
        # that depend on the current event loop.
        asyncio.set_event_loop(loop)

        # Store the loop in a global variable so it can be accessed from other parts of the application,
        # such as where asynchronous tasks are scheduled or where the loop needs to be referenced for operations
        # like shutting down the application cleanly.
        global_asyncio_loop = loop
        print('Global asyncio loop in utils', global_asyncio_loop)

        # Create a task for asynchronously updating RFID status. This demonstrates the primary reason for having
        # a dedicated event loop running - to perform asynchronous operations in the background while the rest of
        # the application (like a GUI) runs synchronously or in a different event loop.
        loop.create_task(async_update_rfid_status(ip_addresses, queue))

        # Creating task for updating reading mode of the rfid reader based on the response received within last 2
        # minutes.
        loop.create_task(async_update_reading_mode_in_db(ip_addresses))

        event.set()  # Signal that the loop is now set up and ready

        # Start the event loop and keep it running. This is crucial for the continuous execution of asynchronous
        # tasks. The loop will run indefinitely until it is stopped explicitly, allowing async tasks to be scheduled
        # and executed as long as the application is running.
        loop.run_forever()

    if global_asyncio_loop is None:
        loop_started_event = threading.Event()
        # Start the event loop in a new daemon thread
        thread = threading.Thread(target=loop_in_thread, args=(loop_started_event,), daemon=True)
        thread.start()
        loop_started_event.wait()


def setup_async_updates(ip_addresses):
    """
        Sets up asynchronous update tasks for monitoring and updating the RFID readers' status.

        This function creates a new thread that runs an asyncio event loop. This approach allows
        asynchronous tasks to run in the background, making it possible to perform non-blocking network
        operations like checking the connectivity status of RFID readers.

        :param ip_addresses: A list of IP addresses for RFID readers to monitor.

        :return:
            Queue instance that will be used to communicate updates back to the main thread,
            typically to update the GUI with the status of each RFID reader.
    """
    queue = Queue()

    # Pass IP addresses and queue to the thread
    thread = threading.Thread(target=start_asyncio_loop, args=(ip_addresses, queue), daemon=True)
    thread.start()
    return queue


def get_global_asyncio_loop():
    # Access the global variable where the asyncio event loop reference is stored.
    global global_asyncio_loop

    # Return the stored event loop. This function provides a way to access the event loop from anywhere in the
    # application, which is necessary for scheduling tasks, running coroutines from synchronous code, or managing
    # the event loop state (like stopping the loop during application shutdown).
    return global_asyncio_loop


async def async_start_listening_response(ip_addresses):
    """
        Async wrapper for start_listening_response function.
        :param ip_addresses: List of the ip addresses of the rfid readers.
    """
    loop = asyncio.get_running_loop()
    # Run the synchronous function in the default executor (ThreadPoolExecutor)
    # This allows for the blocking call to not block the asyncio event loop
    await loop.run_in_executor(None, start_listening_response, ip_addresses)


def start_listening_response(ip_addresses):
    """
        Initialize listening response from all RFID readers.
        :param ip_addresses: List of the ip addresses of the rfid readers.
    """
    global global_asyncio_loop
    if global_asyncio_loop is None:
        start_asyncio_loop(ip_addresses, Queue())  # Assuming a queue is still relevant for your design

    for ip_address in ip_addresses:
        if ip_address not in reading_active:  # Check if not already listening
            asyncio.run_coroutine_threadsafe(listen_for_responses(ip_address), global_asyncio_loop)
            reading_active[ip_address] = True


async def listen_for_responses(ip_address):
    """
        Continuously listen for responses from an RFID reader.
        :param ip_address: Ip address of the rfid reader for which to listen response.
    """
    global active_connections, rfid_reader_last_response_time, reading_active
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
        try:
            response = await reader.read(1024)
            if response:
                # Process response
                rfid_tag = get_rfid_tag_info(response)
                print(f'Received rfid tag response in hexadecimal format: {rfid_tag}')
                rfid_tag_response_queue.put({rfid_tag, ip_address})
                rfid_reader_last_response_time[ip_address] = datetime.now()
            else:
                # Handle connection closed
                print(f"Connection closed by reader {ip_address}")
                break
            await asyncio.sleep(0.01)
        except Exception as e:
            print(f"Error listening to {ip_address}: {e}")
            break


async def async_update_reading_mode_in_db(ip_addresses):
    """
        This function is for updating the Reading_Mode in the database based on the response received within last 2
        minutes. If it receives a response and stop button is not clicked then updating Reading_Mode as 'On' else 'Off'
        :param ip_addresses: The list of ip addresses of the rfid reader.
    """
    global stop_button_clicked
    while True:
        for ip_address in ip_addresses:
            try:
                current_time = datetime.now()
                last_response = rfid_reader_last_response_time.get(ip_address, current_time - timedelta(minutes=3))

                if stop_button_clicked is False and (current_time - last_response).total_seconds() <= 120:
                    # If response received from the reader within last 2 minutes and stop button is not clicked.
                    server_connection_params.updateReadingModeStatusInRFIDDeviceDetails('On', ip_address)  # Writing
                    # reading mode as 'On' for the reader
                    print(f'Updated reading mode to On for {ip_address}')

                else:
                    server_connection_params.updateReadingModeStatusInRFIDDeviceDetails('Off', ip_address)
                    print(f'Updated reading mode to Off for {ip_address}')

            except Exception as e:
                print(f"Error updating reading mode status for {ip_address}: {e}")

        await asyncio.sleep(9)  # Wait for 9 seconds for next response check


async def async_update_rfid_status(ip_addresses, queue):
    """
        Asynchronously updates RFID status and puts results in a queue.
        :param ip_addresses: List containing the ip addresses of the rfid reader.
        :param queue: Queue where to store the status of the rfid reader ip addresses.
    """
    global active_connections, rfid_ip_reading_mode, rfid_reader_last_response_time, rfid_ip_status_color
    while True:
        # Create a list of tasks for all IP addresses
        tasks = [rfid_connectivity_checker(ip) for ip in ip_addresses]

        # Gather results from all tasks
        results = await asyncio.gather(*tasks)

        # Process the results
        for ip_address, is_online in zip(ip_addresses, results):
            # Initialize status_color to 'red' as default
            status_color = 'red'
            reading_mode = 'Not available'
            if is_online:
                # Check reading mode from the database
                reading_mode_result = server_connection_params.findReadingModeInRFIDDeviceDetailsUsingDeviceIP(
                    ip_address)
                reading_mode = reading_mode_result[0][0]

                current_time = datetime.now()

                # Below setting Default value of scanning time for the ip address to >2min ago i.e. 3 minutes ago if ip
                # not found. So, if there's no entry for the given ip_address in rfid_reader_last_response_time, it
                # means we haven't received a response from this reader recently, and for the purpose of the subsequent
                # logic, it's as if the last response was more than 2 minutes ago.
                last_response = rfid_reader_last_response_time.get(ip_address, current_time - timedelta(minutes=3))

                # Determine if a response has been received in the last 2 minutes

                if reading_mode == 'On' and (current_time - last_response).total_seconds() <= 120:
                    # Reading mode is On in the db and a response was received in the last 2 minutes
                    status_color = 'green'

                elif reading_mode == 'On' and (current_time - last_response).total_seconds() > 120:
                    # Reading mode is On in the db but no response in the last 2 minutes
                    status_color = 'yellow'

                else:
                    # Reading mode is off but reader is reachable
                    status_color = 'yellow'

                if status_color == 'green':
                    reading_mode = 'On'
                    rfid_ip_reading_mode[ip_address] = reading_mode
                else:
                    reading_mode = 'Off'
                    rfid_ip_reading_mode[ip_address] = reading_mode

                # Check if connection is already established
                if ip_address not in active_connections:
                    reader, writer = await open_net_connection(ip_address, port=2022)  # Adjust port as needed
                    if reader and writer:
                        active_connections[ip_address] = (reader, writer)
                        print(f"Connection established for {ip_address}")
            else:
                reading_mode = 'Not Available'
                rfid_ip_reading_mode[ip_address] = 'Not Available'

                # If the IP address goes offline, remove it from active connections dictionary
                if ip_address in active_connections:
                    del active_connections[ip_address]
                    print(f"Connection closed for {ip_address}")

            # Update the rfid_ip_status_color dictionary with the current status color
            rfid_ip_status_color[ip_address] = status_color

            image_data = get_image_data(f'images/{status_color}.png', maxsize=(width, height))
            queue.put((ip_address, image_data, reading_mode, rfid_ip_status_color))

        # Wait a bit before the  next check
        await asyncio.sleep(1)


def getRFIDResponseQueue():
    """
        Functions to return the rfid_tag_response_queue
        :return: rfid_tag_response_queue
    """
    global rfid_tag_response_queue
    return rfid_tag_response_queue


async def start_reading(ip_address):
    """
        Function to start the rfid reading on the start button press.
        :param ip_address: Ip address of the device to start the reading mode for.
    """
    global reading_active, active_connections, rfid_reader_last_response_time, stop_button_clicked
    stop_button_clicked = False
    connection = active_connections.get(ip_address)

    if not connection or connection[0]._transport.is_closing() or connection[1]._transport.is_closing():
        # Re-establish connection if not exists or closed
        print(f"Re-establishing connection for {ip_address}")
        new_connection = await open_net_connection(ip_address, port=2022)
        if new_connection:
            active_connections[ip_address] = new_connection
            reading_active[ip_address] = True
            await listen_for_responses(ip_address)
        else:
            print(f"Failed to re-establish connection for {ip_address}")
            return
        reader, writer = new_connection
    reader, writer = active_connections[ip_address]
    if not reader or not writer:
        print(f"No valid connection for {ip_address}")
        return

    if active_connections[ip_address]:  # If the connection is established only then
        await start_reading_mode(reader, writer)
        print(f"Started reading mode for {ip_address}")
        reading_active[ip_address] = True
        await listen_for_responses(ip_address)

        print("Listening for responses...")

    else:
        print(f"No active connection for {ip_address}")


async def stop_reading(ip_address):
    """
        Function to stop the reading for a rfid device.
        :param ip_address: Ip address of the device to stop the reading mode for.
    """
    global stop_button_clicked
    stop_button_clicked = True
    connection = active_connections.get(ip_address)
    if connection:
        _, writer = connection
        await stop_reading_mode(writer)
        reading_active[ip_address] = False  # Signal the loop to stop

        # Ensure clean closure of the writer
        if not writer.transport.is_closing():
            writer.close()
        await writer.wait_closed()

        while not rfid_tag_response_queue.empty():
            rfid_tag_response_queue.get_nowait()  # Clear any remaining items in the queue
        print(f"Stopped reading mode for {ip_address}")
    else:
        print(f"No active connection for {ip_address}")
