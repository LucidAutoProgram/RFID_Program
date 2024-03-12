import asyncio

from db_operations import server_connection_params
from gui import create_core_dashboard_window
from utils import manage_rfid_readers

if __name__ == '__main__':
    create_core_dashboard_window()
