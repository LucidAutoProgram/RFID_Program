from typing import Tuple, List
import mysql.connector
from mysql.connector import Error


class DatabaseOperations:
    def __init__(self, host_ip, host_username, db_password, db_name, db_ip, db_port, db_pool_name, db_pool_size):
        self.host_ip = host_ip
        self.host_username = host_username
        self.db_password = db_password
        self.db_name = db_name
        self.db_ip = db_ip
        self.db_port = db_port
        self.db_pool_name = db_pool_name
        self.db_pool_size = db_pool_size
        self.connection = self.create_server_connection()  # Establish connection at initialization

    def create_server_connection(self):
        try:
            connection = mysql.connector.connect(
                host=self.host_ip,
                user=self.host_username,
                passwd=self.db_password,
                database=self.db_name,
                port=self.db_port
            )
            print("MySQL Database connection successful")
            return connection
        except Error as err:
            print(f"Error Making DataBase Connection to {self.db_ip}: '{err}'")
            return None

    def findAllDeviceIPInRFIDDeviceDetails(self) -> List[Tuple[str]]:
        """
           Fetches all the Device_IP from the RFID_Device_Details table.

        :return: List[Tuple[
                            Device_IP
                    ]]
        """
        db_cursor = None
        try:
            db_cursor = self.connection.cursor()
            prepared_statement = """
                                    SELECT Device_IP 
                                    FROM RFID_Device_Details 
                                  """
            db_cursor.execute(prepared_statement)
            db_result = db_cursor.fetchall()  # Get query results
            return db_result

        except Exception as e:
            print(f'Error from DatabaseOperations.findAllDeviceIPInRFIDDeviceDetails => {e}')
        finally:
            db_cursor.close()

    def findDevicePortInRFIDDeviceDetailsUsingDeviceIP(self, device_ip) -> List[Tuple[str]]:
        """
            Fetches the Device Port based on its DeviceIP.
            :param device_ip: The ip address of the rfid device.
            :return: List[Tuple[
                                Device_Port
                        ]]
        """
        db_cursor = None
        try:
            db_cursor = self.connection.cursor()
            prepared_statement = """
                                            SELECT Device_Port 
                                            FROM RFID_Device_Details 
                                            WHERE Device_IP = %s
                                          """
            db_cursor.execute(prepared_statement, (device_ip,))
            db_result = db_cursor.fetchall()  # Get query results
            return db_result

        except Exception as e:
            print(f'Error from DatabaseOperations.findDevicePortInRFIDDeviceDetailsUsingDeviceIP => {e}')
        finally:
            db_cursor.close()

    def findDeviceLocationInRFIDDeviceDetailsUsingDeviceIP(self, device_ip) -> List[Tuple[str]]:
        """
            Fetches the Device Location based on its DeviceIP.
            :param device_ip: The ip address of the rfid device.
            :return: List[Tuple[
                                Location
                        ]]
        """
        db_cursor = None
        try:
            db_cursor = self.connection.cursor()
            prepared_statement = """
                                            SELECT Location 
                                            FROM RFID_Device_Details 
                                            WHERE Device_IP = %s
                                          """
            db_cursor.execute(prepared_statement, (device_ip,))
            db_result = db_cursor.fetchall()  # Get query results
            return db_result

        except Exception as e:
            print(f'Error from DatabaseOperations.findDeviceLocationInRFIDDeviceDetailsUsingDeviceIP => {e}')
        finally:
            db_cursor.close()

    def findReadingModeInRFIDDeviceDetailsUsingDeviceIP(self, device_ip) -> List[Tuple[str]]:
        """
            Fetches the reading mode based on its DeviceIP, whether it is on or off.
            :param device_ip: The ip address of the rfid device.
            :return: List[Tuple[
                                Reading_Mode
                        ]]
        """
        db_cursor = None
        try:
            db_cursor = self.connection.cursor()
            prepared_statement = """
                                            SELECT Reading_Mode 
                                            FROM RFID_Device_Details 
                                            WHERE Device_IP = %s
                                          """
            db_cursor.execute(prepared_statement, (device_ip,))
            db_result = db_cursor.fetchall()  # Get query results
            return db_result

        except Exception as e:
            print(f'Error from DatabaseOperations.findReadingModeInRFIDDeviceDetailsUsingDeviceIP => {e}')
        finally:
            db_cursor.close()

    def findAllDeviceIPAndLocationInRFIDDeviceDetails(self) -> List[Tuple[str, str]]:
        """
        Fetches all the Device_IP and Location from the RFID_Device_Details table.

        :return: List[Tuple[
                            Device_IP,
                            Location
                    ]]
        """
        db_cursor = None
        try:
            db_cursor = self.connection.cursor()
            prepared_statement = """
                                    SELECT Device_IP, Location 
                                    FROM RFID_Device_Details 
                                  """
            db_cursor.execute(prepared_statement)
            db_result = db_cursor.fetchall()  # Get query results
            return db_result

        except Exception as e:
            print(f'Error from DatabaseOperations.findAllDeviceIPAndLocationInRFIDDeviceDetails => {e}')
        finally:
            if db_cursor:
                db_cursor.close()


server_connection_params = DatabaseOperations(
    host_ip='192.168.10.1',
    host_username='LucidAuto',
    db_password='Lucid@390',
    db_name='LucidAutoDB',
    db_ip='192.168.10.1',
    db_port=3306,
    db_pool_name='server_db_pool',
    db_pool_size=5
)

# device_ips = server_connection_params.findAllDeviceIPInRFIDDeviceDetails()
# if device_ips:
#     print(f"Device IPs: {device_ips}")
#     for ip in device_ips:
#         device_port = server_connection_params.findDevicePortInRFIDDeviceDetailsUsingDeviceIP(ip[0])
#         print(f'Device Port for {ip[0]} - {device_port}')
#         device_location = server_connection_params.findDeviceLocationInRFIDDeviceDetailsUsingDeviceIP(ip[0])
#         print(f'Device Location for {ip[0]} is {device_location}')
#         reading_mode = server_connection_params.findReadingModeInRFIDDeviceDetailsUsingDeviceIP(ip[0])
#         print(f'Reading mode for {ip[0]} is {reading_mode}')
# else:
#     print("Device IPs could not be found or an error occurred.")

