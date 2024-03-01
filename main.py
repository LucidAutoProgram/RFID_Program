from db_operations import server_connection_params

from gui import launch_gui
from utils import start_listening_response

if __name__ == '__main__':

    device_ips = [ip[0] for ip in server_connection_params.findAllDeviceIPInRFIDDeviceDetails()]  # This will contain
    # the list of ip addresses stored in it.

    ip_addresses_with_location = server_connection_params.findAllDeviceIPAndLocationInRFIDDeviceDetails()

    # Start listening for responses from RFID readers
    start_listening_response(device_ips)

    # Start the GUI
    launch_gui(device_ips, ip_addresses_with_location)
