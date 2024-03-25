import asyncio
import tkinter as tk
from threading import Thread
from db_operations import server_connection_params
from utils import manage_rfid_readers, display_message_and_image


def create_core_dashboard_window(title="CORE DASHBOARD", size="1800x800", background_color="white"):
    app = tk.Tk()
    app.title(title)
    app.geometry(size)
    app.configure(background=background_color)

    heading_label = tk.Label(app, text="CORE STATION", bg=background_color, fg="black", font=("Cambria", 24, 'bold'))
    heading_label.pack(pady=20)

    app.after(0, lambda: display_message_and_image('Please Put Core For scanning', "Images/core.png", app))

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
        app.destroy()  # Ensures window destruction is queued after cleanup

    app.protocol("WM_DELETE_WINDOW", close_event)

    def schedule_asyncio_tasks():
        device_ips = [ip[0] for ip in server_connection_params.findAllDeviceIPInRFIDDeviceDetails()]
        asyncio.run_coroutine_threadsafe(manage_rfid_readers(device_ips, app), loop)

    app.after(100, schedule_asyncio_tasks)
    app.mainloop()

    loop.close()  # Properly close the loop after the main loop ends
    t.join()  # Ensure the thread has finished
