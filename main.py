from gui import create_core_dashboard_window
import os
import time

if __name__ == '__main__':
    # Maximum wait time in seconds
    # max_wait_time = 60
    # wait_interval = 5  # Check every 5 seconds
    # waited_time = 0
    #
    # # Wait for the DISPLAY environment variable to be set
    # while 'DISPLAY' not in os.environ:
    #     if waited_time >= max_wait_time:
    #         print("Waited too long for a display to become available. Exiting.")
    #         exit(1)
    #     print("Waiting for a display to become available...")
    #     time.sleep(wait_interval)
    #     waited_time += wait_interval

    # Now that a display is presumably available, create the Tkinter window
    create_core_dashboard_window()
