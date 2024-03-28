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

    def findLocationIDInMaterialRollLocationUsingMaterialCoreID(self, material_core_id: int) -> List[Tuple[str]]:
        """
            Fetches the Location_ID from Material_Roll_Location based on its Material_Core_ID.
            :param material_core_id: The ID of the core.
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
                                            FROM Material_Roll_Location 
                                            WHERE Material_Core_ID = %s
                                          """
            db_cursor.execute(prepared_statement, (material_core_id,))
            db_result = db_cursor.fetchall()  # Get query results
            return db_result

        except Exception as e:
            print(f'Error from DatabaseOperations.findLocationIDInMaterialRollLocationUsingMaterialCoreID => {e}')
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

    def findAllWorkOrderNumberInWorkOrderMainTable(self) -> List[Tuple[str]]:
        """
           Fetches all the WorkOrder_Number from the WorkOrder_main table.

        :return: List[Tuple[
                            WorkOrder_Number
                    ]]
        """
        db_connection = None
        db_cursor = None
        try:
            db_connection = self.get_connection()  # Get a connection from connection pool
            db_cursor = db_connection.cursor()
            prepared_statement = """
                                      SELECT WorkOrder_Number 
                                      FROM WorkOrder_main 
                                    """
            db_cursor.execute(prepared_statement)
            db_result = db_cursor.fetchall()  # Get query results
            return db_result

        except Exception as e:
            print(f'Error from DatabaseOperations.findAllWorkOrderNumberInWorkOrderMainTable => {e}')
        finally:
            if db_cursor:
                db_cursor.close()
            if db_connection:
                db_connection.close()

    def findMaxWorkOrderIDFromWorkOrderMainTable(self) -> int:
        """
            Fetches the maximum WorkOrder_ID from the WorkOrder_main table.
            :return: The maximum WorkOrder_ID.
        """
        db_connection = None
        db_cursor = None
        try:
            db_connection = self.get_connection()
            db_cursor = db_connection.cursor()
            prepared_statement = """
                                    SELECT MAX(WorkOrder_ID) FROM WorkOrder_main
                                 """
            db_cursor.execute(prepared_statement)
            db_result = db_cursor.fetchone()
            if db_result and db_result[0] is not None:
                return db_result[0]
        except Exception as e:
            print(f'Error fetching maximum WorkOrder_ID: {e}')
        finally:
            if db_cursor:
                db_cursor.close()
            if db_connection:
                db_connection.close()

    def findWorkOrderNumberFromWorkOrderMainTableUsingWorkOrderID(self, work_order_id: int) -> List[Tuple[str]]:
        """
            Fetches the WorkOrder_Number from WorkOrder_main table based on its WorkOrder_ID.
            :param work_order_id: The id of the work order assigned to particular roll.
            :return: List[Tuple[
                                WorkOrder_Number
                        ]]
        """
        db_connection = None
        db_cursor = None
        try:
            db_connection = self.get_connection()  # Get a connection from connection pool
            db_cursor = db_connection.cursor()
            prepared_statement = """
                                        SELECT WorkOrder_Number 
                                        FROM WorkOrder_main 
                                        WHERE WorkOrder_ID = %s
                                 """
            db_cursor.execute(prepared_statement, (work_order_id,))
            db_result = db_cursor.fetchall()  # Get query results
            return db_result

        except Exception as e:
            print(f'Error from DatabaseOperations.findWorkOrderNumberFromWorkOrderMainTableUsingWorkOrderID => {e}')
        finally:
            if db_cursor:
                db_cursor.close()
            if db_connection:
                db_connection.close()

    def findMaterialRollIDInMaterialRollTableUsingMaterialCoreID(self, material_core_id: int) -> List[Tuple[int]]:
        """
            Fetches the Material_Roll_ID from Material_Roll based on its Material_Core_ID.
            :param material_core_id: The ID of the core.
            :return: List[Tuple[
                                Material_Roll_ID
                        ]]
        """
        db_connection = None
        db_cursor = None
        try:
            db_connection = self.get_connection()  # Get a connection from connection pool
            db_cursor = db_connection.cursor()
            prepared_statement = """
                                            SELECT Material_Roll_ID 
                                            FROM Material_Roll
                                            WHERE Material_Core_ID = %s
                                          """
            db_cursor.execute(prepared_statement, (material_core_id,))
            db_result = db_cursor.fetchall()  # Get query results
            return db_result

        except Exception as e:
            print(f'Error from DatabaseOperations.'
                  f'findMaterialRollIDInMaterialRollTableUsingMaterialCoreID => {e}')
        finally:
            if db_cursor:
                db_cursor.close()
            if db_connection:
                db_connection.close()

    def writeToWorkOrderAssignmentTable(self, work_order_id: int, location_id: str):
        """
            Method with which to write to WorkOrder_Assignment table

            :param work_order_id: The work order id assigned to a particular roll.
            :param location_id: Location of the roll where it is getting scanned.

            :return: Null
        """
        db_connection = None
        db_cursor = None
        try:
            db_connection = self.get_connection()  # Get a connection from connection pool
            db_cursor = db_connection.cursor()

            write_operation = (work_order_id, location_id)
            prepared_statement = """
                                    INSERT INTO WorkOrder_Assignment (
                                    WorkOrder_ID, Location_ID) 
                                    VALUES (%s, %s);
                                 """

            db_cursor.execute(prepared_statement, write_operation)
            db_connection.commit()  # Save write work
            print(f'Successfully wrote work order id - {work_order_id} with location id - {location_id} to work order'
                  f'assignment table')
        except Exception as e:
            print(f'Error from DatabaseOperations.writeToWorkOrderAssignmentTable => {e}')
        finally:
            if db_connection and db_connection.is_connected():
                db_cursor.close()
                db_connection.close()

    def writeToWorkOrderMainTable(self, work_order_id: int, work_order_number: str):
        """
            Method with which to write to WorkOrder_main table

            :param work_order_id: The work order id assigned to a particular roll.
            :param work_order_number: The work order number assigned to particular roll.

            :return: Null
        """
        db_connection = None
        db_cursor = None
        try:
            db_connection = self.get_connection()  # Get a connection from connection pool
            db_cursor = db_connection.cursor()

            write_operation = (work_order_id, work_order_number)
            prepared_statement = """
                                      INSERT INTO WorkOrder_main (
                                      WorkOrder_ID, WorkOrder_Number) 
                                      VALUES (%s, %s);
                                 """

            db_cursor.execute(prepared_statement, write_operation)
            db_connection.commit()  # Save write work
            print(f'Successfully wrote work order id - {work_order_id} with work order number - {work_order_number} to'
                  f'WorkOrder_main table')
        except Exception as e:
            print(f'Error from DatabaseOperations.writeToWorkOrderMainTable => {e}')
        finally:
            if db_connection and db_connection.is_connected():
                db_cursor.close()
                db_connection.close()

    def writeToWorkOrderScheduledTable(self, work_order_id: int):
        """
            Method with which to write to WorkOrder_Scheduled table.

            :param work_order_id: The work order id assigned to a particular roll.

            :return: Null
        """
        db_connection = None
        db_cursor = None
        try:
            db_connection = self.get_connection()  # Get a connection from connection pool
            db_cursor = db_connection.cursor()

            write_operation = (work_order_id,)
            prepared_statement = """
                                         INSERT INTO WorkOrder_Scheduled (
                                         WorkOrder_ID, Schedule_DateTime) 
                                         VALUES (%s, NOW());
                                    """

            db_cursor.execute(prepared_statement, write_operation)
            db_connection.commit()  # Save write work
            print(f'Successfully wrote work order id - {work_order_id} to WorkOrder_Scheduled table')

        except Exception as e:
            print(f'Error from DatabaseOperations.writeToWorkOrderScheduledTable => {e}')
        finally:
            if db_connection and db_connection.is_connected():
                db_cursor.close()
                db_connection.close()

    def updateMaterialRollLengthAndMaterialRollNumOfTurnsInMaterialRollLengthTable(self, material_roll_length: int,
                                                                                   material_roll_num_of_turns: int,
                                                                                   material_roll_id: int):
        """
            This function is for updating material roll length and material roll number of turns in Material_Roll_Length
            table.
            :param material_roll_length: Length of the role made.
            :param material_roll_num_of_turns: The number of turns roll have made.
            :param material_roll_id: material roll id of the roll.
            :return: None
        """
        db_connection = None
        db_cursor = None
        try:
            db_connection = self.get_connection()  # Get a connection from connection pool
            db_cursor = db_connection.cursor()

            update_operation = (material_roll_length, material_roll_num_of_turns, material_roll_id)
            prepared_statement = """
                                    UPDATE Material_Roll_Length 
                                    SET Material_Roll_Length = %s,
                                    Material_Roll_Num_of_Turns = %s
                                    WHERE Material_Roll_ID = %s
                                 """

            db_cursor.execute(prepared_statement, update_operation)
            db_connection.commit()
        except Exception as e:
            print(f'Error from DatabaseOperations.'
                  f'updateMaterialRollLengthAndMaterialRollNumOfTurnsInMaterialRollLengthTable => {e}')
        finally:
            if db_cursor:
                db_cursor.close()
            if db_connection:
                db_connection.close()

    def updateMaterialRollCreationStartTimeInMaterialRollLengthTable(self, material_roll_id: int):
        """
            This function is for updating Material_Roll_Creation_StartTime in Material_Roll_Length table.
            :param material_roll_id: material roll id of the roll.
            :return: None
        """
        db_connection = None
        db_cursor = None
        try:
            db_connection = self.get_connection()  # Get a connection from connection pool
            db_cursor = db_connection.cursor()

            update_operation = (material_roll_id,)
            prepared_statement = """
                                    UPDATE Material_Roll_Length 
                                    SET Material_Roll_Creation_StartTime = NOW()
                                    WHERE Material_Roll_ID = %s
                                 """

            db_cursor.execute(prepared_statement, update_operation)
            db_connection.commit()
        except Exception as e:
            print(f'Error from DatabaseOperations.'
                  f'updateMaterialRollCreationStartTimeInMaterialRollLengthTable => {e}')
        finally:
            if db_cursor:
                db_cursor.close()
            if db_connection:
                db_connection.close()

    def updateMaterialRollCreationEndTimeInMaterialRollLengthTable(self, material_roll_id: int):
        """
            This function is for updating Material_Roll_Creation_EndTime in Material_Roll_Length table.
            :param material_roll_id: material roll id of the roll.
            :return: None
        """
        db_connection = None
        db_cursor = None
        try:
            db_connection = self.get_connection()  # Get a connection from connection pool
            db_cursor = db_connection.cursor()

            update_operation = (material_roll_id,)
            prepared_statement = """
                                    UPDATE Material_Roll_Length 
                                    SET Material_Roll_Creation_EndTime = NOW()
                                    WHERE Material_Roll_ID = %s
                                 """

            db_cursor.execute(prepared_statement, update_operation)
            db_connection.commit()
        except Exception as e:
            print(f'Error from DatabaseOperations.'
                  f'updateMaterialRollCreationEndTimeInMaterialRollLengthTable => {e}')
        finally:
            if db_cursor:
                db_cursor.close()
            if db_connection:
                db_connection.close()

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

    def findRFIDDeviceIDInRFIDDeviceDetailsTableUsingDeviceIP(self, device_ip: str) -> List[Tuple[int]]:
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

    def findLocationIDInRFIDDeviceTableUsingRFIDDeviceID(self, device_id: int) -> List[Tuple[str]]:
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
                                                 WHERE RFID_Device_ID = %s
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

    def findAllRFIDTagsInMaterialCoreRFID(self) -> List[Tuple[str]]:
        """
           Fetches all the rfid_tags from the Material_Core_RFID table.

        :return: List[Tuple[
                            RFID_Tag
                    ]]
        """
        db_connection = None
        db_cursor = None
        try:
            db_connection = self.get_connection()  # Get a connection from connection pool
            db_cursor = db_connection.cursor()
            prepared_statement = """
                                     SELECT RFID_Tag 
                                     FROM Material_Core_RFID 
                                   """
            db_cursor.execute(prepared_statement)
            db_result = db_cursor.fetchall()  # Get query results
            return db_result

        except Exception as e:
            print(f'Error from DatabaseOperations.findAllRFIDTagsInMaterialCoreRFID => {e}')
        finally:
            if db_cursor:
                db_cursor.close()
            if db_connection:
                db_connection.close()

    def findMaterialCoreIDInMaterialRollLocationUsingLocationID(self, location_id: str) -> List[Tuple[int]]:
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

    def findRFIDTagInMaterialCoreRFIDUsingMaterialCoreID(self, material_core_id: int) -> List[Tuple[str]]:
        """
            Fetches the RFID_Tag from Material_Core_RFID table based on its Material_Core_ID.
            :param material_core_id: The id of the material core.
            :return: List[Tuple[
                                RFID_Tag
                        ]]
        """
        db_connection = None
        db_cursor = None
        try:
            db_connection = self.get_connection()  # Get a connection from connection pool
            db_cursor = db_connection.cursor()
            prepared_statement = """
                                                 SELECT DISTINCT RFID_Tag 
                                                 FROM Material_Core_RFID 
                                                 WHERE Material_Core_ID = %s
                                               """
            db_cursor.execute(prepared_statement, (material_core_id,))
            db_result = db_cursor.fetchall()  # Get query results
            return db_result

        except Exception as e:
            print(f'Error from DatabaseOperations.findRFIDTagInMaterialCoreRFIDUsingMaterialCoreID => {e}')
        finally:
            if db_cursor:
                db_cursor.close()
            if db_connection:
                db_connection.close()

    def findMaxCoreIdFromMaterialCoreRFIDTable(self) -> int:
        """
            Fetches the maximum Material_Core_ID from the Material_Core_RFID table.
            :return: The maximum Material_Core_ID.
        """
        db_connection = None
        db_cursor = None
        try:
            db_connection = self.get_connection()
            db_cursor = db_connection.cursor()
            prepared_statement = """
                                    SELECT MAX(Material_Core_ID) FROM Material_Core_RFID
                                 """
            db_cursor.execute(prepared_statement)
            db_result = db_cursor.fetchone()
            if db_result and db_result[0] is not None:
                return db_result[0]
        except Exception as e:
            print(f'Error fetching maximum Material_Core_ID: {e}')
        finally:
            if db_cursor:
                db_cursor.close()
            if db_connection:
                db_connection.close()

    def findLocationIDInRFIDDeviceDetailsUsingDeviceIP(self, device_ip) -> List[Tuple[str]]:
        """
            Fetches the Location_ID based on its DeviceIP.
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
            print(f'Error from DatabaseOperations.findLocationIDInRFIDDeviceDetailsUsingDeviceIP => {e}')
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
            print(f'Error from DatabaseOperations.findAllDeviceIPAndLocationIDInRFIDDeviceDetails => {e}')
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

    def updateMaterialCoreRFIDEndInMaterialCoreRFIDTable(self, material_core_rfid_end: datetime, rfid_tag: str,
                                                         material_core_id: int):
        """
            This function is for updating the end date of the rfid tag, basically when rfid tag is damaged.
            :param material_core_rfid_end: End time of the rfid tag, like when it got damaged.
            :param rfid_tag: The rfid tag scanned by the rfid reader.
            :param material_core_id: Id of the Core.
            :return: None
        """
        db_connection = None
        db_cursor = None
        try:
            db_connection = self.get_connection()  # Get a connection from connection pool
            db_cursor = db_connection.cursor()

            prepared_statement = """
                                    UPDATE Material_Core_RFID 
                                    SET Material_Core_RFID_End = %s 
                                    WHERE RFID_Tag = %s AND 
                                    Material_Core_ID = %s
                                 """

            db_cursor.execute(prepared_statement, (material_core_rfid_end, rfid_tag, material_core_id))
            db_connection.commit()
            print(f'Updated end time for tag - {rfid_tag} with core id - {material_core_id}')
        except Exception as e:
            print(f'Error from DatabaseOperations.updateMaterialCoreRFIDEndInMaterialCoreRFIDTable => {e}')
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
            Method with which to write to Material_Core table

            :param material_core_id: Unique id for each core. It is assigned after scanning the tags on the core.

            :return: Null
        """
        db_connection = None
        db_cursor = None
        try:
            db_connection = self.get_connection()  # Get a connection from connection pool
            db_cursor = db_connection.cursor()

            prepared_statement = """
                                          INSERT INTO Material_Core(
                                          Material_Core_ID) 
                                          VALUES (%s);
                                       """

            db_cursor.execute(prepared_statement, (material_core_id,))
            db_connection.commit()  # Save write work
        except Exception as e:
            print(f'Error from DatabaseOperations.writeToMaterialCoreTable => {e}')
        finally:
            if db_connection and db_connection.is_connected():
                db_cursor.close()
                db_connection.close()

    def writeToMaterialRollLocation(self, material_core_id: int, location_id: int):
        """
            Method with which to write to Material_Roll_Location table

            :param material_core_id: Unique id for each core. It is assigned after scanning the tags on the core.
            :param location_id: The id of the location of the core.

            :return: Null
        """
        db_connection = None
        db_cursor = None
        try:
            db_connection = self.get_connection()  # Get a connection from connection pool
            db_cursor = db_connection.cursor()

            prepared_statement = """
                                   INSERT INTO Material_Roll_Location(
                                   Material_Core_ID, Location_ID) 
                                   VALUES (%s, %s);
                                 """

            db_cursor.execute(prepared_statement, (material_core_id, location_id))
            db_connection.commit()  # Save write work
            print(f'successfully write location {location_id} to material core {material_core_id}')

        except Exception as e:
            print(f'Error from DatabaseOperations.writeToMaterialCoreTable => {e}')
        finally:
            if db_connection and db_connection.is_connected():
                db_cursor.close()
                db_connection.close()

    def checkExistingRecord(self, material_core_id, location_id):
        db_connection = None
        db_cursor = None
        try:
            db_connection = self.get_connection()  # Get a connection from the connection pool
            db_cursor = db_connection.cursor()
            query = """
                    SELECT COUNT(*) FROM Material_Roll_Location
                    WHERE Material_Core_ID = %s AND Location_ID = %s
                    """
            db_cursor.execute(query, (material_core_id, location_id))
            db_result = db_cursor.fetchone()  # Fetch the first row of the result
            if db_result[0] > 0:
                return True  # Record exists
            else:
                return False  # Record does not exist

        except Exception as e:
            print(f'Error from DatabaseOperations.checkExistingRecord => {e}')
            return False  # no record exists in case of error
        finally:
            if db_cursor:
                db_cursor.close()
            if db_connection:
                db_connection.close()

    def writeToMaterialRollTable(self, material_roll_id: int, material_core_id: int):
        """
            Method with which to write to Material_Roll table

            :param material_roll_id: material roll id assigned to roll.
            :param material_core_id: Unique id for each core. It is assigned after scanning the tags on the core.

            :return: Null
        """
        db_connection = None
        db_cursor = None
        try:
            db_connection = self.get_connection()  # Get a connection from connection pool
            db_cursor = db_connection.cursor()

            prepared_statement = """
                                         INSERT INTO Material_Roll(
                                         Material_Roll_ID,
                                         Material_Core_ID) 
                                         VALUES (%s, %s);
                                     """

            db_cursor.execute(prepared_statement, (material_roll_id, material_core_id))
            db_connection.commit()  # Save write work
            print(f'Successfully wrote role id - {material_roll_id} core id - {material_core_id} to material roll '
                  f'table')
        except Exception as e:
            print(f'Error from DatabaseOperations.writeToMaterialRollTable => {e}')
        finally:
            if db_connection and db_connection.is_connected():
                db_cursor.close()
                db_connection.close()

    def writeMaterialRoleIDToMaterialRollLengthTable(self, material_roll_id: int):
        """
            Method with which to write Material_Roll_ID to Material_Roll table

            :param material_roll_id: material roll id assigned to roll.

            :return: Null
        """
        db_connection = None
        db_cursor = None
        try:
            db_connection = self.get_connection()  # Get a connection from connection pool
            db_cursor = db_connection.cursor()

            prepared_statement = """
                                           INSERT INTO Material_Roll_Length(
                                           Material_Roll_ID) 
                                           VALUES (%s);
                                       """

            db_cursor.execute(prepared_statement, (material_roll_id,))
            db_connection.commit()  # Save write work
            print(f'Successfully wrote role id - {material_roll_id} to material roll length table')
        except Exception as e:
            print(f'Error from DatabaseOperations.writeMaterialRoleIDToMaterialRollLengthTable => {e}')
        finally:
            if db_connection and db_connection.is_connected():
                db_cursor.close()
                db_connection.close()

    def findWorkOrderIDFromWorkOrderAssignmentTableUsingLocationID(self, location_ID: str) -> List[Tuple[str]]:
        """
            Fetches the WorkOrder_ID from the WorkOrder_Assignment table based on the Location_ID.
            :param location_ID: location where rfid tags are getting scanned

            :return: List[Tuple[
                                WorkOrder_ID
                        ]]
        """
        db_connection = None
        db_cursor = None
        try:
            db_connection = self.get_connection()  # Get a connection from connection pool
            db_cursor = db_connection.cursor()
            prepared_statement = """
                                      SELECT DISTINCT WorkOrder_ID 
                                      FROM WorkOrder_Assignment
                                      WHERE Location_ID = %s 
                                    """
            db_cursor.execute(prepared_statement, (location_ID,))
            db_result = db_cursor.fetchall()  # Get query results
            return db_result

        except Exception as e:
            print(f'Error from DatabaseOperations.findWorkOrderIDFromWorkOrderAssignmentTableUsingLocationID => {e}')
        finally:
            if db_cursor:
                db_cursor.close()
            if db_connection:
                db_connection.close()

    def findWorkOrderIDFromWorkOrderAssignmentTableUsingRollID(self, roll_id: int) -> List[Tuple[int]]:
        """
            Fetches the WorkOrder_ID from the WorkOrder_Assignment table based on the Roll_ID.
            :param roll_id: unique id assigned to specific roll

            :return: List[Tuple[
                                WorkOrder_ID
                        ]]
        """
        db_connection = None
        db_cursor = None
        try:
            db_connection = self.get_connection()  # Get a connection from connection pool
            db_cursor = db_connection.cursor()
            prepared_statement = """
                                         SELECT DISTINCT WorkOrder_ID 
                                         FROM WorkOrder_Assignment
                                         WHERE Roll_ID = %s 
                                       """
            db_cursor.execute(prepared_statement, (roll_id,))
            db_result = db_cursor.fetchall()  # Get query results
            return db_result

        except Exception as e:
            print(f'Error from DatabaseOperations.findWorkOrderIDFromWorkOrderAssignmentTableUsingLocationID => {e}')
        finally:
            if db_cursor:
                db_cursor.close()
            if db_connection:
                db_connection.close()

    def findMaterialRollSpecsFromMaterialRollLengthTableUsingMaterialRollID(self, material_roll_id: int) -> \
            List[Tuple[int, datetime, datetime, int]]:
        """
            Fetches the MaterialRoll Specification from the Material_Roll_Length table based on the Material_Roll_ID.
            :param material_roll_id: location where rfid tags are getting scanned

            :return: List[Tuple[
                                Material_Roll_Length,
                                Material_Roll_Creation_StartTime,
                                Material_Roll_Creation_EndTime,
                                Material_Roll_Num_of_Turns,
                        ]]
        """
        db_connection = None
        db_cursor = None
        try:
            db_connection = self.get_connection()  # Get a connection from connection pool
            db_cursor = db_connection.cursor()
            prepared_statement = """
                                    SELECT DISTINCT Material_Roll_Length,
                                    Material_Roll_Creation_StartTime,
                                    Material_Roll_Creation_EndTime,
                                    Material_Roll_Num_of_Turns
                                    FROM Material_Roll_Length
                                    WHERE Material_Roll_ID = %s 
                                  """
            db_cursor.execute(prepared_statement, (material_roll_id,))
            db_result = db_cursor.fetchall()  # Get query results
            return db_result

        except Exception as e:
            print(f'Error from DatabaseOperations.findMaterialRollSpecsFromMaterialRollLengthTableUsingMaterialRollID '
                  f'=> {e}')
        finally:
            if db_cursor:
                db_cursor.close()
            if db_connection:
                db_connection.close()

    def writeRollIDRollInTimeLocationID(self, material_roll_id: int, roll_in_time: datetime,
                                        roll_out_time: datetime, location_id: str):

        """
            Method with which to write Material_Roll_ID , Roll_In_Time  and Location_ID to
             Roll_Storage table
            :param roll_out_time: time when role exit storage
            :param location_id: location at which role is stored.
            :param roll_in_time: time when roll enter in storage unit.
            :param material_roll_id: material roll id assigned to roll.
            :return: Null
         """
        db_connection = None
        db_cursor = None
        try:
            db_connection = self.get_connection()  # Get a connection from connection pool
            db_cursor = db_connection.cursor()

            prepared_statement = """
                                       INSERT INTO Roll_Storage(
                                       Roll_ID,
                                       Roll_In_Time,
                                       Roll_Out_Time,
                                       Location_ID) 
                                       VALUES (%s,%s,%s,%s);
                                 """

            db_cursor.execute(prepared_statement, (material_roll_id, roll_in_time, roll_out_time, location_id))
            db_connection.commit()  # Save write work
            print(f'Successfully wrote role id - {material_roll_id} with role in time -{roll_in_time} at '
                  f'location {location_id}to roll storage table')
        except Exception as e:
            print(f'Error from DatabaseOperations.writeRollIDRollInTimeLocationID => {e}')
        finally:
            if db_connection and db_connection.is_connected():
                db_cursor.close()
                db_connection.close()

    def updateRollOutTime(self, material_roll_id: int, roll_out_time: datetime, location_id: int):
        """
        Method to update Material_Roll_ID's Roll_Out_Time and Location_ID in the Roll_Storage table.
        :param material_roll_id: The ID of the material roll.
        :param roll_out_time: The time when the roll exits the storage unit.
        :param location_id: The new location ID for the roll.
        :return: None
        """
        db_connection = None
        db_cursor = None
        try:
            db_connection = self.get_connection()  # Get a connection from the connection pool
            db_cursor = db_connection.cursor()

            prepared_statement = """
                                    UPDATE Roll_Storage
                                    SET Roll_Out_Time = %s, Location_ID = %s
                                    WHERE Roll_ID = %s
                                 """

            db_cursor.execute(prepared_statement, (roll_out_time, location_id, material_roll_id,))
            db_connection.commit()  # Save the update
            print(
                f'Successfully updated roll out time to {roll_out_time} and location ID to {location_id} for roll ID'
                f' {material_roll_id} in the Roll_Storage table.')
        except Exception as e:
            print(f'Error from DatabaseOperations.updateRollOutTime => {e}')
        finally:
            if db_connection and db_connection.is_connected():
                db_cursor.close()
                db_connection.close()

    def updateDataForRoll(self, material_roll_id: int, roll_in_time: datetime,
                          location_id: int):
        """
        Method to update Material_Roll_ID's Roll_Out_Time and Location_ID in the Roll_Storage table.
        :param roll_in_time: Time at which role enter storage unit
        :param material_roll_id: The ID of the material roll.
        :param location_id: The new location ID for the roll.
        :return: None
        """
        db_connection = None
        db_cursor = None
        try:
            db_connection = self.get_connection()  # Get a connection from the connection pool
            db_cursor = db_connection.cursor()

            prepared_statement = """
                                    UPDATE Roll_Storage
                                    SET Roll_In_Time = %s, Roll_Out_Time = NULL, Location_ID = %s
                                    WHERE Roll_ID = %s
                                 """

            db_cursor.execute(prepared_statement, (roll_in_time, location_id, material_roll_id,))
            db_connection.commit()  # Save the update
            print(
                f'Successfully updated  roll in time to {roll_in_time}'
                f' and location ID to {location_id} for roll ID {material_roll_id} in the Roll_Storage table.')
        except Exception as e:
            print(f'Error from DatabaseOperations.updateDataForRole => {e}')
        finally:
            if db_connection and db_connection.is_connected():
                db_cursor.close()
                db_connection.close()

    def findAllRollIDRollInTimeInStorageRollTable(self) -> List[Tuple[str]]:
        """
           Fetches all the Roll_ID and Roll_In_Time and Location_ID from the Roll_Storage table.

        :return: List[Tuple[
                            Roll_ID , Roll_In_Time,Roll_Out_Time,Location_ID
                    ]]
        """
        db_connection = None
        db_cursor = None
        try:
            db_connection = self.get_connection()  # Get a connection from connection pool
            db_cursor = db_connection.cursor()
            prepared_statement = """
                                         SELECT Roll_ID , Roll_In_Time , Roll_Out_Time,Location_ID 
                                         FROM Roll_Storage
                                       """
            db_cursor.execute(prepared_statement)
            db_result = db_cursor.fetchall()  # Get query results
            return db_result

        except Exception as e:
            print(f'Error from DatabaseOperations.findAllRollIDRollInTimeInStorageRollTable => {e}')
        finally:
            if db_cursor:
                db_cursor.close()
            if db_connection:
                db_connection.close()


# ----------------------- Establishing the database connection ---------------------

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
