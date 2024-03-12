import asyncio

from db_operations import server_connection_params
from utils import manage_rfid_readers

if __name__ == '__main__':

    device_ips = [ip[0] for ip in server_connection_params.findAllDeviceIPInRFIDDeviceDetails()]  # This will contain
    # the list of ip addresses stored in it.

    asyncio.run(manage_rfid_readers(device_ips))

