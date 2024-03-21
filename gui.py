import asyncio
import tkinter as tk
from threading import Thread
from PIL import Image, ImageTk
from db_operations import server_connection_params
from utils import manage_rfid_readers, location_lights, roll_details, update_location_image, terminal_message

message_text = None


def create_core_dashboard_window(title="WORKORDER DASHBOARD", size="1600x800", background_color="white"):
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
    heading_label = tk.Label(app, text="EXTRUDER WORK ORDER ROLL STATION", bg=background_color, fg="black",
                             font=("Cambria", 24, 'bold'))
    heading_label.pack(pady=20)  # Use padding to space out the label from the window's top edge

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

    extruder_frame = tk.Frame(app, bg="darkgrey", bd=4, relief="groove")
    extruder_frame.place(relx=0.5, rely=0.5, anchor="center", relwidth=0.8, relheight=0.8)

    def schedule_asyncio_tasks():
        """
            Function to schedule asyncio tasks from the Tkinter main thread
            :return: None
        """

        global message_text
        device_ips = [ip[0] for ip in server_connection_params.findAllDeviceIPInRFIDDeviceDetails()]
        device_locations = []
        for ip in device_ips:
            location_ids_for_ip = server_connection_params.findLocationIDInRFIDDeviceDetailsUsingDeviceIP(ip)[0]
            for location_id in location_ids_for_ip:
                locations_XYZ_for_ip = server_connection_params. \
                    findLocationXYZInLocationTableUsingLocationID(location_id)
                if locations_XYZ_for_ip:
                    device_locations.append(locations_XYZ_for_ip[0][0])
                else:
                    # Handle case where no location is found for the IP, possibly with a placeholder
                    device_locations.append("Unknown Location")

        # Filter locations that start with "Extruder"
        extruder_locations = [loc for loc in device_locations if loc.startswith("Extruder")]

        for index, location in enumerate(extruder_locations):
            row = index // 4  # Assuming 4 locations per row for layout purposes
            column = index % 4
            extruder_frame.grid_columnconfigure(column, weight=1, minsize=200)
            extruder_frame.grid_rowconfigure(row, weight=1)

            message_frame = tk.Frame(extruder_frame, bg="darkgrey", bd=2, relief="sunken")
            message_frame.grid(row=row, column=column, sticky="nsew")
            message_frame.grid_columnconfigure(0, weight=1)  # Allow internal content to expand

            # Location Frame
            location_frame = tk.Frame(message_frame, bg="black", bd=2, relief="raised")
            location_frame.pack(fill='both')

            # Load and display image within the location frame
            image_path = "Image/yellow.png"  # Update with the actual image path
            image = Image.open(image_path)
            image = image.resize((20, 20), Image.LANCZOS)
            photo = ImageTk.PhotoImage(image)

            # It's crucial to keep a reference to the photo object to prevent garbage collection.
            location_label_image = tk.Label(location_frame, image=photo, bg="black")  # Attach the image
            location_label_image.image = photo  # Keep a reference
            location_label_image.pack(side="left", padx=10)
            location_label = tk.Label(location_frame, text=location, bg="black",
                                      fg="white", font=('Cambria', 15))
            location_label.pack()

            # Message Label Frame
            roll_details_frame = tk.Frame(message_frame, bg="black", bd=2, relief="raised")
            roll_details_frame.pack(fill='both', expand=True)

            roll_detail_label = tk.Label(roll_details_frame, text='No Roll on the Winder ', bg="black", fg="white",
                                         font=('Cambria', 15))
            roll_detail_label.pack()

            # Terminal Frame
            terminal_frame = tk.Frame(message_frame, bg="black", bd=2, relief="raised")
            terminal_frame.pack(fill='both', expand=True, )

            terminal_window = tk.Label(terminal_frame, text='', bg="black", fg="white", font=('Cambria', 15))
            terminal_window.pack()

            # mapping location to location_label for updating image
            location_lights[location] = location_label_image
            roll_details[location] = roll_detail_label
            terminal_message[location] = terminal_window

        print(f'Device ips {device_ips} with device locations XYZ- {device_locations}')
        # Scheduling the manage_rfid_readers coroutine to run in the asyncio loop
        asyncio.run_coroutine_threadsafe(manage_rfid_readers(device_ips, device_locations, app), loop)

    # Scheduling the asyncio task after a short delay to ensure everything is initialized properly
    app.after(100, schedule_asyncio_tasks)

    # Starting the Tkinter main loop to make the window responsive
    app.mainloop()

    # After exiting the main loop, ensuring the asyncio loop is stopped and the thread is joined before exiting the
    # program
    loop.close()  # Closing the asyncio loop
    t.join()  # Waiting for the thread running the asyncio loop to finish
