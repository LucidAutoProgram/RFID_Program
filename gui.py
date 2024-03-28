import asyncio
import tkinter as tk
from threading import Thread
from db_operations import server_connection_params
from utils import manage_rfid_readers, display_message_and_image
from pathlib import Path

# Define the base directory as the directory where this script is located
base_dir = Path(__file__).parent

# Construct the image paths
core_image_path = base_dir / "Images" / "core.png"


def create_core_dashboard_window(title="CORE DASHBOARD", size="1800x800", background_color="white"):
    """
        Initializing the main Tkinter application window
        :param title: Title of the gui window.
        :param size: Size of the gui window
        :param background_color: Background color of the window.
        :return: None
    """
    app = tk.Tk()
    app.title(title)  # Setting the title of the window
    app.geometry(size)  # Setting the size of the window
    # Setting the window background color
    app.configure(background=background_color)

    # Creating the heading label with "Core Station" text
    heading_label = tk.Label(app, text="CORE STATION", bg=background_color, fg="black", font=("Cambria", 24, 'bold'))
    heading_label.pack(pady=20)  # Use padding to space out the label from the window's top edge

    # Displaying the initial message and image to for the user to place the core for scanning
    app.after(0, lambda: display_message_and_image(
        f'Please Put Core For scanning', str(core_image_path), app))

    loop = asyncio.new_event_loop()

    def start_asyncio_loop(loop):
        """
            Function to start the asyncio event loop in a separate thread
            :param loop: Separate event loop for the async operations.
            :return: None
        """
        asyncio.set_event_loop(loop)  # Setting the event loop for the asyncio operations
        loop.run_forever()  # Start the loop to run forever

    t = Thread(target=start_asyncio_loop, args=(loop,))
    t.start()

    async def cleanup_tasks():
        tasks = [task for task in asyncio.all_tasks(loop) if task is not asyncio.current_task()]
        [task.cancel() for task in tasks]
        await asyncio.gather(*tasks, return_exceptions=True)
        loop.stop()

    def close_event():
        """
            Function to handle window close event
            :return: None
        """
        asyncio.run_coroutine_threadsafe(cleanup_tasks(), loop)
        app.destroy()  # Ensures window destruction is queued after cleanup

    # Binding the window close event to the custom close_event function
    app.protocol("WM_DELETE_WINDOW", close_event)

    def schedule_asyncio_tasks():
        """
            Function to schedule asyncio tasks from the Tkinter main thread
            :return: None
        """

        device_ips = [ip[0] for ip in server_connection_params.findAllDeviceIPInRFIDDeviceDetails()]
        # Scheduling the manage_rfid_readers coroutine to run in the asyncio loop
        asyncio.run_coroutine_threadsafe(manage_rfid_readers(device_ips, app), loop)

    # Scheduling the asyncio task after a short delay to ensure everything is initialized properly
    app.after(100, schedule_asyncio_tasks)

    # Starting the Tkinter main loop to make the window responsive
    app.mainloop()

    # After exiting the main loop, ensuring the asyncio loop is stopped and the thread is joined before exiting the
    # program
    loop.close()  # Closing the asyncio loop
    t.join()  # Waiting for the thread running the asyncio loop to finish


