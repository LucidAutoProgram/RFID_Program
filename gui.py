import asyncio
import tkinter as tk
from threading import Thread
from tkinter import ttk, messagebox
from PIL import Image, ImageTk

from db_operations import server_connection_params
from utils import manage_rfid_readers, display_message_and_image


def create_core_dashboard_window(title="CORE DASHBOARD", size="600x500", background_color="white"):
    app = tk.Tk()
    app.title(title)
    app.geometry(size)

    # Set the window background color
    app.configure(background=background_color)

    # Create the heading label with "Core Station" text
    heading_label = tk.Label(app, text="CORE STATION", bg=background_color, fg="black", font=("Cambria", 24, 'bold'))
    heading_label.pack(pady=20)  # Use padding to space out the label from the window's top edge

    app.after(0, lambda: display_message_and_image(
        f'Please put Core For scanning', "Images/core.png", app))

    def start_asyncio_loop(loop):
        asyncio.set_event_loop(loop)
        loop.run_forever()

    def close_event():
        loop.call_soon_threadsafe(loop.stop)
        app.destroy()

    app.protocol("WM_DELETE_WINDOW", close_event)

    loop = asyncio.new_event_loop()
    t = Thread(target=start_asyncio_loop, args=(loop,))
    t.start()

    # Schedule the asyncio tasks from the Tkinter main thread, ensuring thread safety
    def schedule_asyncio_tasks():
        device_ips = [ip[0] for ip in server_connection_params.findAllDeviceIPInRFIDDeviceDetails()]
        asyncio.run_coroutine_threadsafe(manage_rfid_readers(device_ips,app), loop)

    app.after(100, schedule_asyncio_tasks)  # Schedule the asyncio task after a short delay

    app.mainloop()

    # Ensuring the asyncio loop stops before exiting
    loop.close()
    t.join()

    app.mainloop()
