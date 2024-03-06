from db_operations import server_connection_params

from gui import launch_gui

if __name__ == '__main__':

    device_ips = [ip[0] for ip in server_connection_params.findAllDeviceIPInRFIDDeviceDetails()]  # This will contain
    # the list of ip addresses stored in it.

    # Collection of tuples containing rfid reader ip with its location
    ip_addresses_with_location = server_connection_params.findAllDeviceIPAndLocationInRFIDDeviceDetails()

    # Display the GUI window
    launch_gui(device_ips, ip_addresses_with_location)
