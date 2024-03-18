from datetime import datetime
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

    def findRFIDDeviceIDInRFIDDeviceDetailsTableUsingDeviceIP(self, device_ip) -> List[Tuple[str]]:
        """
            Fetches the Device ID from RFID_Device_Details table based on its DeviceIP.
            :param device_ip: The ip address of the rfid device.
            :return: List[Tuple[
                                RFID_Device_ID
                        ]]
        """
        db_connection = None
        db_cursor = None
        try:
            db_connection = self.get_connection()  # Get a connection from connection pool
            db_cursor = db_connection.cursor()
            prepared_statement = """
                                               SELECT RFID_Device_ID 
                                               FROM RFID_Device_Details 
                                               WHERE Device_IP = %s
                                             """
            db_cursor.execute(prepared_statement, (device_ip,))
            db_result = db_cursor.fetchall()  # Get query results
            return db_result

        except Exception as e:
            print(f'Error from DatabaseOperations.findRFIDDeviceIDInRFIDDeviceDetailsTableUsingDeviceIP => {e}')
        finally:
            if db_cursor:
                db_cursor.close()
            if db_connection:
                db_connection.close()

    def findLocationIDInRFIDDeviceTableUsingRFIDDeviceID(self, device_id) -> List[Tuple[str]]:
        """
            Fetches the  Location_ID from RFID_Device table based on its RIFD_Device_ID.
            :param device_id: The device id of the rfid device.
            :return: List[Tuple[
                                Location_ID
                        ]]
        """
        db_connection = None
        db_cursor = None
        try:
            db_connection = self.get_connection()  # Get a connection from connection pool
            db_cursor = db_connection.cursor()
            prepared_statement = """
                                                 SELECT Location_ID 
                                                 FROM RFID_Device 
                                                 WHERE RIFD_Device_ID = %s
                                               """
            db_cursor.execute(prepared_statement, (device_id,))
            db_result = db_cursor.fetchall()  # Get query results
            return db_result

        except Exception as e:
            print(f'Error from DatabaseOperations.findLocationIDInRFIDDeviceTableUsingRFIDDeviceID => {e}')
        finally:
            if db_cursor:
                db_cursor.close()
            if db_connection:
                db_connection.close()

    def findMaterialCoreIDInMaterialRollLocationUsingLocationID(self, location_id) -> List[Tuple[int]]:
        """
            Fetches the Material_Core_ID from Material_Roll_Location table based on its Location_ID.
            :param location_id: The id of the location of the rfid device.
            :return: List[Tuple[
                                Material_Core_ID
                        ]]
        """
        db_connection = None
        db_cursor = None
        try:
            db_connection = self.get_connection()  # Get a connection from connection pool
            db_cursor = db_connection.cursor()
            prepared_statement = """
                                                 SELECT Material_Core_ID 
                                                 FROM Material_Roll_Location 
                                                 WHERE Location_ID = %s
                                               """
            db_cursor.execute(prepared_statement, (location_id,))
            db_result = db_cursor.fetchall()  # Get query results
            return db_result

        except Exception as e:
            print(f'Error from DatabaseOperations.findMaterialCoreIDInMaterialRollLocationUsingLocationID => {e}')
        finally:
            if db_cursor:
                db_cursor.close()
            if db_connection:
                db_connection.close()

    def findDeviceLocationIDInRFIDDeviceDetailsUsingDeviceIP(self, device_ip) -> List[Tuple[str]]:
        """
            Fetches the Device Location_ID based on its DeviceIP.
            :param device_ip: The ip address of the rfid device.
            :return: List[Tuple[
                                Location_ID
                        ]]
        """
        db_connection = None
        db_cursor = None
        try:
            db_connection = self.get_connection()  # Get a connection from connection pool
            db_cursor = db_connection.cursor()
            prepared_statement = """
                                            SELECT Location_ID 
                                            FROM RFID_Device_Details 
                                            WHERE Device_IP = %s
                                          """
            db_cursor.execute(prepared_statement, (device_ip,))
            db_result = db_cursor.fetchall()  # Get query results
            return db_result

        except Exception as e:
            print(f'Error from DatabaseOperations.findDeviceLocationIDInRFIDDeviceDetailsUsingDeviceIP => {e}')
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

    def findLocationXYZInLocationTableUsingLocationID(self, location_id: str) -> List[Tuple[str]]:
        """
            Fetches the LocationXYZ of the rfid reader device based on its Location_ID.
            :param location_id: The id of the location of the rfid reader device.
            :return: List[Tuple[
                                LocationXYZ
                        ]]
        """
        db_connection = None
        db_cursor = None
        try:
            db_connection = self.get_connection()  # Get a connection from connection pool
            db_cursor = db_connection.cursor()
            prepared_statement = """
                                       SELECT LocationXYZ 
                                       FROM Location 
                                       WHERE Location_ID = %s
                                     """
            db_cursor.execute(prepared_statement, (location_id,))
            db_result = db_cursor.fetchall()  # Get query results
            return db_result

        except Exception as e:
            print(f'Error from DatabaseOperations.findLocationXYZInLocationTableUsingLocationID => {e}')
        finally:
            if db_cursor:
                db_cursor.close()
            if db_connection:
                db_connection.close()

    def findAllDeviceIPAndLocationIDInRFIDDeviceDetails(self) -> List[Tuple[str, str]]:
        """
        Fetches all the Device_IP and Location_ID from the RFID_Device_Details table.

        :return: List[Tuple[
                            Device_IP,
                            Location_ID
                    ]]
        """
        db_connection = None
        db_cursor = None
        try:
            db_connection = self.get_connection()  # Get a connection from connection pool
            db_cursor = db_connection.cursor()
            prepared_statement = """
                                    SELECT Device_IP, Location_ID
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

    def findMaterialCoreIDFromMaterialCoreRFIDTableUsingRFIDTag(self, rfid_tag: str) -> List[Tuple[str]]:
        """
            Fetches all the Material_Core_ID from the Material_Core_RFID table based on the RFID_Tag.
            :param rfid_tag: RFID tag scanned by the rfid reader.

            :return: List[Tuple[
                                Material_Core_ID
                        ]]
        """
        db_connection = None
        db_cursor = None
        try:
            db_connection = self.get_connection()  # Get a connection from connection pool
            db_cursor = db_connection.cursor()
            prepared_statement = """
                                      SELECT DISTINCT Material_Core_ID 
                                      FROM Material_Core_RFID
                                      WHERE RFID_Tag = %s 
                                    """
            db_cursor.execute(prepared_statement, (rfid_tag,))
            db_result = db_cursor.fetchall()  # Get query results
            return db_result

        except Exception as e:
            print(f'Error from DatabaseOperations.findMaterialCoreIDFromMaterialCoreRFIDTableUsingRFIDTag => {e}')
        finally:
            if db_cursor:
                db_cursor.close()
            if db_connection:
                db_connection.close()

    def findMaxMaterialCoreIdFromMaterialCoreRFIDTableUsingDeviceIP(self, device_ip: str) -> str:
        """
            Fetches the maximum Material_Core_ID from the Material_Core_RFID table for a particular ip address.
            :return: The maximum Material_Core_ID for a particular ip address.
        """
        db_connection = None
        db_cursor = None
        try:
            db_connection = self.get_connection()
            db_cursor = db_connection.cursor()
            prepared_statement = """
                                        SELECT MAX(Material_Core_ID) FROM Material_Core_RFID
                                        WHERE Device_IP = %s
                                   """
            db_cursor.execute(prepared_statement, (device_ip,))
            db_result = db_cursor.fetchone()
            if db_result and db_result[0] is not None:
                return db_result[0]
        except Exception as e:
            print(f'Error fetching maximum Material_Core_ID for device ip - {device_ip}: {e}')
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

    def writeToMaterialCoreRFIDTable(self, rfid_tag: str, material_core_id: int, material_core_rfid_start: datetime):
        """
            Method with which to write to Material_Core_RFID table

            :param rfid_tag: The rfid tag scanned by the rfid reader.
            :param material_core_id: Unique id for each core. It is assigned after scanning the tags on the core.
            :param material_core_rfid_start: The rfid tag first scan date and time by the rfid reader.

            :return: Null
        """
        db_connection = None
        db_cursor = None
        try:
            db_connection = self.get_connection()  # Get a connection from connection pool
            db_cursor = db_connection.cursor()

            write_operation = (rfid_tag, material_core_id, material_core_rfid_start)
            prepared_statement = """
                                          INSERT INTO Material_Core_RFID (
                                          RFID_Tag, Material_Core_ID,
                                          Material_Core_RFID_Start) 
                                          VALUES (%s, %s, %s);
                                       """

            db_cursor.execute(prepared_statement, write_operation)
            db_connection.commit()  # Save write work
        except Exception as e:
            print(f'Error from DatabaseOperations.writeToMaterialCoreRFIDTable => {e}')
        finally:
            if db_connection and db_connection.is_connected():
                db_cursor.close()
                db_connection.close()

    def writeToMaterialCoreTable(self, material_core_id: int):
        """
            Method with which to write  table

            :param material_core_id: Unique id for each core. It is assigned after scanning the tags on the core.

            :return: Null
        """
        db_connection = None
        db_cursor = None
        try:
            db_connection = self.get_connection()  # Get a connection from connection pool
            db_cursor = db_connection.cursor()

            prepared_statement = """
                                          INSERT INTO Material_Core_RFID (
                                          RFID_Tag, Material_Core_ID,
                                          Material_Core_RFID_Start) 
                                          VALUES (%s, %s, %s);
                                       """

            db_cursor.execute(prepared_statement, (material_core_id,))
            db_connection.commit()  # Save write work
        except Exception as e:
            print(f'Error from DatabaseOperations.writeToMaterialCoreTable => {e}')
        finally:
            if db_connection and db_connection.is_connected():
                db_cursor.close()
                db_connection.close()


# ----------------------- Establishing the connection ---------------------

server_connection_params = DatabaseOperations(
    host_ip='192.168.10.200',
    host_username='LucidAuto',
    db_password='Lucid@390',
    db_name='LucidAutoDB',
    db_ip='192.168.10.200',
    db_port=3306,
    db_pool_name='server_db_pool',
    db_pool_size=5
)
