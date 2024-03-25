import asyncio
import tkinter as tk
from threading import Thread
from db_operations import server_connection_params
from utils import manage_rfid_readers, display_message_and_image


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
        f'Please Put Core For scanning', "Images/core.png", app))

    def start_asyncio_loop(loop):
        """
            Function to start the asyncio event loop in a separate thread
            :param loop: Separate event loop for the async operations.
            :return: None
        """
        asyncio.set_event_loop(loop)  # Setting the event loop for the asyncio operations
        loop.run_forever()  # Start the loop to run forever

    def close_event():
        """
            Function to handle window close event
            :return: None
        """
        # Attempt to cancel all tasks
        for task in asyncio.all_tasks(loop):
            task.cancel()
        try:
            loop.run_until_complete(asyncio.gather(*asyncio.all_tasks(loop)))
        except asyncio.CancelledError:
            # Expecting all tasks to be cancelled, so cancelled errors are ignored
            pass

        loop.call_soon_threadsafe(loop.stop)  # Safely stop the asyncio loop from another thread
        app.destroy()  # Destroying the Tkinter window, effectively closing the application

    # Binding the window close event to the custom close_event function
    app.protocol("WM_DELETE_WINDOW", close_event)

    # Initializing a new asyncio event loop
    loop = asyncio.new_event_loop()
    # Starting the asyncio loop in a separate thread to avoid blocking the Tkinter main loop
    t = Thread(target=start_asyncio_loop, args=(loop,))
    t.start()

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


