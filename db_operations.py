from typing import Tuple, List
import mysql.connector
from mysql.connector import Error


class DatabaseOperations:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(DatabaseOperations, cls).__new__(cls)
        return cls._instance

    def __init__(self, host_ip, host_username, db_password, db_name, db_ip, db_port, db_pool_name, db_pool_size):
        if not hasattr(self, 'is_initialized'):
            self.host_ip = host_ip
            self.host_username = host_username
            self.db_password = db_password
            self.db_name = db_name
            self.db_ip = db_ip
            self.db_port = db_port
            self.db_pool_name = db_pool_name
            self.db_pool_size = db_pool_size
            self.connection_pool = self.create_connection_pool()
            self.is_initialized = True

    def create_connection_pool(self):
        try:
            pool = mysql.connector.pooling.MySQLConnectionPool(
                pool_name=self.db_pool_name,
                pool_size=self.db_pool_size,
                host=self.host_ip,
                user=self.host_username,
                passwd=self.db_password,
                database=self.db_name,
                port=self.db_port
            )
            print("Connection pool is created.")
            return pool
        except Error as err:
            print(f"Error creating a connection pool: '{err}'")
            return None

    def get_connection(self):
        try:
            return self.connection_pool.get_connection()
        except Error as err:
            print(f"Error getting connection from pool: '{err}'")
            return None

    def findAllDeviceIPInRFIDDeviceDetails(self) -> List[Tuple[str]]:
        """
           Fetches all the Device_IP from the RFID_Device_Details table.

        :return: List[Tuple[
                            Device_IP
                    ]]
        """
        db_connection = None
        db_cursor = None
        try:
            db_connection = self.get_connection()  # Get a connection from connection pool
            db_cursor = db_connection.cursor()
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
            if db_cursor:
                db_cursor.close()
            if db_connection:
                db_connection.close()

    def findDevicePortInRFIDDeviceDetailsUsingDeviceIP(self, device_ip) -> List[Tuple[str]]:
        """
            Fetches the Device Port based on its DeviceIP.
            :param device_ip: The ip address of the rfid device.
            :return: List[Tuple[
                                Device_Port
                        ]]
        """
        db_connection = None
        db_cursor = None
        try:
            db_connection = self.get_connection()  # Get a connection from connection pool
            db_cursor = db_connection.cursor()
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
            if db_cursor:
                db_cursor.close()
            if db_connection:
                db_connection.close()

    def findDeviceLocationInRFIDDeviceDetailsUsingDeviceIP(self, device_ip) -> List[Tuple[str]]:
        """
            Fetches the Device Location based on its DeviceIP.
            :param device_ip: The ip address of the rfid device.
            :return: List[Tuple[
                                Location
                        ]]
        """
        db_connection = None
        db_cursor = None
        try:
            db_connection = self.get_connection()  # Get a connection from connection pool
            db_cursor = db_connection.cursor()
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
            if db_cursor:
                db_cursor.close()
            if db_connection:
                db_connection.close()

    def findReadingModeInRFIDDeviceDetailsUsingDeviceIP(self, device_ip) -> List[Tuple[str]]:
        """
            Fetches the reading mode based on its DeviceIP, whether it is on or off.
            :param device_ip: The ip address of the rfid device.
            :return: List[Tuple[
                                Reading_Mode
                        ]]
        """
        db_connection = None
        db_cursor = None
        try:
            db_connection = self.get_connection()  # Get a connection from connection pool
            db_cursor = db_connection.cursor()
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
            if db_cursor:
                db_cursor.close()
            if db_connection:
                db_connection.close()

    def findAllDeviceIPAndLocationInRFIDDeviceDetails(self) -> List[Tuple[str, str]]:
        """
        Fetches all the Device_IP and Location from the RFID_Device_Details table.

        :return: List[Tuple[
                            Device_IP,
                            Location
                    ]]
        """
        db_connection = None
        db_cursor = None
        try:
            db_connection = self.get_connection()  # Get a connection from connection pool
            db_cursor = db_connection.cursor()
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
            if db_connection:
                db_connection.close()

    def updateReadingModeStatusInRFIDDeviceDetails(self, reading_mode: str, device_ip: str):
        """
            This function is for updating the status of rfid reading mode ('On' or 'Off') based on the device ip.
            :param reading_mode: Status of rfid reader reading mode.
            :param device_ip: The ip address of the rfid reader.
            :return: None
        """
        db_connection = None
        db_cursor = None
        try:
            db_connection = self.get_connection()  # Get a connection from connection pool
            db_cursor = db_connection.cursor()

            update_operation = (reading_mode, device_ip)
            prepared_statement = """
                                    UPDATE RFID_Device_Details 
                                    SET Reading_Mode = %s 
                                    WHERE Device_IP = %s
                                 """

            db_cursor.execute(prepared_statement, update_operation)
            db_connection.commit()
        except Exception as e:
            print(f'Error from DatabaseOperations.updateReadingModeStatusInRFIDDeviceDetails => {e}')
        finally:
            if db_cursor:
                db_cursor.close()
            if db_connection:
                db_connection.close()


# ----------------------- Creating the connection ---------------------

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

