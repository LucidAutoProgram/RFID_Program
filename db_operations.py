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

    def findWorkOrderNumberFromWorkOrderMainTableUsingWorkOrderID(self, work_order_id: int) -> List[Tuple[str]]:
        """
            Fetches the WorkOrder_Number from WorkOrder_Main table based on its WorkOrder_ID.
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
                                        FROM WorkOrder_Main 
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

    def findMaterialRollIDInMaterialRollLengthTableUsingMaterialCoreID(self, material_core_id: int) -> List[Tuple[int]]:
        """
            Fetches the Material_Roll_ID from Material_Roll_Length based on its Material_Core_ID.
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
                                            FROM Material_Roll_Length
                                            WHERE Material_Core_ID = %s
                                          """
            db_cursor.execute(prepared_statement, (material_core_id,))
            db_result = db_cursor.fetchall()  # Get query results
            return db_result

        except Exception as e:
            print(f'Error from DatabaseOperations.'
                  f'findMaterialRollIDInMaterialRollLengthTableUsingMaterialCoreID => {e}')
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
        except Exception as e:
            print(f'Error from DatabaseOperations.writeToWorkOrderAssignmentTable => {e}')
        finally:
            if db_connection and db_connection.is_connected():
                db_cursor.close()
                db_connection.close()

    def writeToWorkOrderMainTable(self, work_order_id: int, work_order_number: str):
        """
            Method with which to write to WorkOrder_Main table

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
                                      INSERT INTO WorkOrder_Main (
                                      WorkOrder_ID, WorkOrder_Name) 
                                      VALUES (%s, %s);
                                 """

            db_cursor.execute(prepared_statement, write_operation)
            db_connection.commit()  # Save write work
        except Exception as e:
            print(f'Error from DatabaseOperations.writeToWorkOrderAssignmentTable => {e}')
        finally:
            if db_connection and db_connection.is_connected():
                db_cursor.close()
                db_connection.close()

    def writeToWorkOrderScheduledTable(self, work_order_id: int):
        """
            Method with which to write to WorkOrder_Main table.

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
