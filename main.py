from db_operations import DatabaseOperations
from gui import launch_gui


if __name__ == '__main__':
    # Initialize database operations and fetch device IPs
    db_connection = DatabaseOperations(
        host_ip='192.168.10.1', host_username='LucidAuto', db_password='Lucid@390',
        db_name='LucidAutoDB', db_ip='192.168.10.1', db_port=3306, db_pool_name='server_db_pool', db_pool_size=5
    )

    device_ips = [ip[0] for ip in db_connection.findAllDeviceIPInRFIDDeviceDetails()]  # This will contain the list of
    # ip addresses stored in it.

    ip_addresses_with_location = db_connection.findAllDeviceIPAndLocationInRFIDDeviceDetails()

    # Start the GUI
    launch_gui(device_ips, ip_addresses_with_location)
