import asyncio
import binascii
import io
import platform
from queue import Queue
from PIL import Image
import threading
import PySimpleGUI as sg

from rfid_api import open_net_connection, start_reading_mode, stop_reading_mode

# Setting the desired width and height of image
width = 15
height = 15
active_connections = {}  # Global storage for active connections
# Global dictionary to store online status of IP addresses
online_locations = {}


def get_image_data(file, maxsize=(width, height)):
    """
        Generating image data using PIL
    """
    img = Image.open(file)
    img.thumbnail(maxsize)
    with io.BytesIO() as output:
        img.save(output, format="PNG")
        data = output.getvalue()
    return data


def create_rfid_layout(ip, status_color, location, port, reading_mode):
    """
        Generating layout for each RFID box with location instead of IP on the button.
    """
    tooltip_text = f"IP: {ip}\nLocation: {location}\nPort: {port}\nReading Mode: {reading_mode}"
    return [
        [sg.Image(data=get_image_data(f'images/{status_color}.png', maxsize=(width, height)), background_color='black',
                  key=f'IMAGE_{ip}'),
         sg.Button(location, button_color=('white', 'black'), border_width=0, focus=False,
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


# This function will run the asyncio event loop
# def start_asyncio_loop(ip_addresses, queue):
#     """
#         This function initializes a new asyncio event loop for the thread.
#     """
#
#     # Initialize a new event loop for the thread
#     loop = asyncio.new_event_loop()
#     asyncio.set_event_loop(loop)
#
#     # Create and schedule your asynchronous tasks
#     loop.create_task(async_update_rfid_status(ip_addresses, queue))
#
#     # Start the loop to process tasks
#     loop.run_forever()


# def schedule_async_task(coroutine_func, *args):
#     """
#     Schedules an async coroutine to be executed.
#
#     :param coroutine_func: The async function to schedule.
#     :param args: Arguments to pass to the coroutine function.
#     """`
#     try:
#         loop = asyncio.get_running_loop()
#     except RuntimeError:  # If no running event loop
#         loop = asyncio.new_event_loop()
#         asyncio.set_event_loop(loop)
#
#     if loop.is_running():
#         loop.call_soon_threadsafe(lambda: asyncio.ensure_future(coroutine_func(*args)))
#     else:
#         asyncio.run(coroutine_func(*args))

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


global_asyncio_loop = None


def start_asyncio_loop(ip_addresses, queue):
    global global_asyncio_loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    global_asyncio_loop = loop  # Store the loop in a global variable
    print('Global asyncio loop in utils', global_asyncio_loop)
    loop.create_task(async_update_rfid_status(ip_addresses, queue))
    loop.run_forever()


def get_global_asyncio_loop():
    global global_asyncio_loop
    return global_asyncio_loop


async def async_update_rfid_status(ip_addresses, queue):
    global active_connections  # Access to the active connections dictionary
    """
        Asynchronously updates RFID status and puts results in a queue.
    """
    while True:
        # Create a list of tasks for all IP addresses
        tasks = [rfid_connectivity_checker(ip) for ip in ip_addresses]

        # Gather results from all tasks
        results = await asyncio.gather(*tasks)

        # Process the results
        for ip_address, is_online in zip(ip_addresses, results):
            if is_online:
                # Check if connection is already established
                if ip_address not in active_connections:
                    reader, writer = await open_net_connection(ip_address, port=2022)  # Adjust port as needed
                    if reader and writer:
                        active_connections[ip_address] = (reader, writer)
                        print(f"Connection established for {ip_address}")
                status_color = 'yellow'
            else:
                # If the IP address goes offline, remove it from active connections
                if ip_address in active_connections:
                    del active_connections[ip_address]
                    print(f"Connection closed for {ip_address}")
                status_color = 'red'

            print(f'Status color {status_color} for {ip_address}')

            image_data = get_image_data(f'images/{status_color}.png', maxsize=(width, height))
            queue.put((ip_address, image_data))

        # Wait a bit before the  next check
        await asyncio.sleep(10)


def setup_async_updates(ip_addresses):
    """
        Sets up asynchronous update tasks.
    """
    queue = Queue()

    # Pass IP addresses and queue to the thread
    thread = threading.Thread(target=start_asyncio_loop, args=(ip_addresses, queue), daemon=True)
    thread.start()

    return queue


reading_active = {}
rfid_tag_response_queue = Queue()  # Queue to store rfid tag response.


def getRFIDResponseQueue():
    """
        Functions to return the rfid_tag_response_queue
        :return: rfid_tag_response_queue
    """
    global rfid_tag_response_queue
    return rfid_tag_response_queue


async def start_reading(ip_address):
    """
        :param ip_address: Ip address of the device to start the reading mode for.
    """
    global reading_active
    connection = active_connections.get(ip_address)
    if connection:
        reader, writer = connection
        await start_reading_mode(reader, writer)
        print(f"Started reading mode for {ip_address}")
        reading_active[ip_address] = True

        print("Listening for responses...")
        try:
            while reading_active[ip_address]:
                response = await reader.read(1024)  # Wait indefinitely for data
                if response:
                    rfid_tag = get_rfid_tag_info(response)
                    print(f'Received rfid tag response in hexadecimal format: {rfid_tag}')
                    rfid_tag_response_queue.put(f"RFID tag: {rfid_tag}")
                else:
                    # If an empty response is received, the connection was likely closed
                    print("The connection was closed by the reader.")
                    break
        except Exception as e:
            print(f"Error receiving response: {e}")
        finally:
            writer.close()
            await writer.wait_closed()
    else:
        print(f"No active connection for {ip_address}")


async def stop_reading(ip_address):
    """
        :param ip_address: Ip address of the device to start the reading mode for.
    """
    connection = active_connections.get(ip_address)
    if connection:
        _, writer = connection
        await stop_reading_mode(writer)
        reading_active[ip_address] = False  # Signal the loop to stop

        while not rfid_tag_response_queue.empty():
            rfid_tag_response_queue.get_nowait()  # Clear any remaining items in the queue
        print(f"Stopped reading mode for {ip_address}")
    else:
        print(f"No active connection for {ip_address}")
