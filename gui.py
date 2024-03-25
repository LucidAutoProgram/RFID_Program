import asyncio
import tkinter as tk
from threading import Thread
from db_operations import server_connection_params
from utils import manage_rfid_readers, location_labels, location_color


def create_extruder_dashboard_window(title="Extruder Roll Station", size="1700x800", background_color="white"):
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
    heading_label = tk.Label(app, text="EXTRUDER ROLL STATION", bg=background_color, fg="black",
                             font=("Cambria", 24, 'bold'))
    heading_label.pack(pady=20)  # Use padding to space out the label from the window's top edge

    loop = asyncio.new_event_loop()

    def start_asyncio_loop(loop):
        asyncio.set_event_loop(loop)
        loop.run_forever()

    t = Thread(target=start_asyncio_loop, args=(loop,))
    t.start()

    async def cleanup_tasks():
        tasks = [task for task in asyncio.all_tasks(loop) if task is not asyncio.current_task()]
        [task.cancel() for task in tasks]
        await asyncio.gather(*tasks, return_exceptions=True)
        loop.stop()

    def close_event():
        asyncio.run_coroutine_threadsafe(cleanup_tasks(), loop)
        app.destroy()

    app.protocol("WM_DELETE_WINDOW", close_event)

    extruder_frame = tk.Frame(app, bg="black", bd=4, relief="groove")
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

        # Filter locations that start with "Winder"
        winder_locations = [loc for loc in device_locations if loc.startswith("Winder")]

        for index, location in enumerate(winder_locations):
            row = index // 2
            column = index % 2

            message_frame = tk.Frame(extruder_frame, bg="black", bd=2, relief="sunken")
            message_frame.grid(row=row, column=column, padx=10, pady=10, sticky="nsew")
            extruder_frame.grid_columnconfigure(column, weight=1, minsize=200)
            extruder_frame.grid_rowconfigure(row, weight=1, minsize=100)

            location_label = tk.Label(message_frame, text=location, bg="yellow", fg="black", font=('Cambria', 18,
                                                                                                   'bold italic'))
            location_label.pack(expand=True, fill='both')

            # mapping location to location_label for updating background color
            location_color[location] = location_label

            message_label = tk.Label(message_frame, text='No Core for scanning.\nPlease Put Core For Scanning',
                                     bg="yellow", fg="black", font=('Cambria', 18, 'bold italic'))
            message_label.pack(expand=True, fill='both')

            # mapping location to message_label for updating background color and message text
            location_labels[location] = message_label

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
