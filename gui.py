import asyncio
import tkinter as tk
from threading import Thread
from tkinter import ttk

from db_operations import server_connection_params
from utils import manage_rfid_readers, Roll_WorkOrder_Info

message_text = None


def create_core_dashboard_window(title="ROLL STORAGE DASHBOARD", size="1850x800", background_color="white"):
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
    heading_label = tk.Label(app, text="ROLL STORAGE STATION", bg=background_color, fg="black",
                             font=("Cambria", 24, 'bold'))
    heading_label.pack(pady=20)  # Use padding to space out the label from the window's top edge

    extruder_frame = tk.Frame(app, bg="darkgrey", bd=3, relief="groove")
    extruder_frame.place(relx=0.5, rely=0.5, anchor="center", relwidth=0.9, relheight=0.8)

    # Creating and applying style to the Treeview widget for customizing headings
    style = ttk.Style()
    style.theme_use("default")
    style.configure("Treeview.Heading", background="black", foreground="white", font=('Cambria', 14, 'bold'))
    style.configure("Treeview", font=('Cambria', 13), rowheight=30)  # Increase the font size for row values

    # Define column names for the treeview
    columns = ('Work Order', 'Roll ID', 'Roll Weight', 'Roll In Time', 'Roll Location')

    # Create the treeview with these columns
    table = ttk.Treeview(extruder_frame, columns=columns, show='headings')
    table.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    # Adding a vertical scrollbar to the treeview
    scrollbar_vertical = ttk.Scrollbar(extruder_frame, orient="vertical", command=table.yview)
    scrollbar_vertical.pack(side=tk.RIGHT, fill="y")

    # Linking scrollbar and treeview
    table.configure(yscrollcommand=scrollbar_vertical.set)

    # Configure each column's heading and width
    for col in columns:
        table.heading(col, text=col)
        table.column(col, width=100, anchor="center")

    # Calling the function which fetches the information of all roles stored in storage
    Roll_WorkOrder_Info(app, table)

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
        print(f'Device ips {device_ips} with device locations XYZ- {device_locations}')
        # Scheduling the manage_rfid_readers coroutine to run in the asyncio loop
        asyncio.run_coroutine_threadsafe(manage_rfid_readers(device_ips, device_locations, app, table), loop)

    # Scheduling the asyncio task after a short delay to ensure everything is initialized properly
    app.after(100, schedule_asyncio_tasks)

    # Starting the Tkinter main loop to make the window responsive
    app.mainloop()

    # After exiting the main loop, ensuring the asyncio loop is stopped and the thread is joined before exiting the
    # program
    loop.close()  # Closing the asyncio loop
    t.join()  # Waiting for the thread running the asyncio loop to finish
