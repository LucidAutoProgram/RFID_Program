import asyncio

from db_operations import server_connection_params
from gui import create_core_dashboard_window
from utils import manage_rfid_readers

if __name__ == '__main__':
    create_core_dashboard_window()
    # device_ips = [ip[0] for ip in server_connection_params.findAllDeviceIPInRFIDDeviceDetails()]
    # device_locations = []
    # for ip in device_ips:
    #     location_ids_for_ip = server_connection_params.findLocationIDInRFIDDeviceDetailsUsingDeviceIP(ip)[0]
    #     for location_id in location_ids_for_ip:
    #         locations_XYZ_for_ip = server_connection_params. \
    #             findLocationXYZInLocationTableUsingLocationID(location_id)
    #         if locations_XYZ_for_ip:
    #             device_locations.append(locations_XYZ_for_ip[0][0])
    #         else:
    #             # Handle case where no location is found for the IP, possibly with a placeholder
    #             device_locations.append("Unknown Location")
    # asyncio.run(manage_rfid_readers(device_ips, device_locations, app='app', message_labels='message'))