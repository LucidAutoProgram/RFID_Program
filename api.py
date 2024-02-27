import serial
import socket
import binascii


def open_device(com_port, baud_rate_index):
    """
        Function to connect to the rfid reader device using serial.
        :param com_port: The com port of the serial.
        :param baud_rate_index: Index of the list containing baud rates.
        :return: Connection established using serial.
    """
    baud_rates = [9600, 19200, 38400, 57600, 115200]
    try:
        baud_rate = baud_rates[baud_rate_index]
        ser = serial.Serial(com_port, baud_rate, timeout=1)
        print(f"Connected to {com_port} at {baud_rate} baud.")
        return ser
    except Exception as e:
        print(f"Failed to open serial port {com_port}: {e}")
        return None


def open_net_connection(ip, port):
    """
        Function to connect to rfid reader using network(TCP/IP connection).
        :param ip: The ip of the rfid reader to connect to.
        :param port: Port of the rfid reader used to connect.
        :return: Connection established using network.
    """
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((ip, port))
        print(f"Network connection established to {ip}:{port}")
        return sock
    except socket.error as e:
        print(f"Failed to connect to {ip}:{port}: {e}")
        return None


def close_serial_connection(serial_connection):
    """
        Function to close the serial connection.
        :param serial_connection: Connection established using serial.
    """
    serial_connection.close()
    print("Serial connection closed.")


def close_network_connection(socket_connection):
    """
        Function to close the network connection.
        :param socket_connection: Connection established using socket(TCP/IP connection).
    """
    socket_connection.close()
    print("Network connection closed.")


def crc16_cal(data):
    """
    Method to calculate CRC16 checksum. CRC values are expected to differ between the command sent and the response
    received because each CRC calculation is specific to the data it accompanies. The CRC for a command reflects the
    integrity of that command data, while the CRC for a response checks the integrity of the response data. If the
    CRC of the received response matches the CRC you calculate based on the response data, it indicates the response
    data has not been altered or corrupted. This is how you use CRC to verify data integrity: by recalculating the
    CRC for the received data and comparing it to the provided CRC. If they match, the data is considered valid; if
    not, it suggests corruption or alteration.
    :param data: Data provided to calculate the crc16 checksum.
    """
    PRESET_VALUE = 0xFFFF
    POLYNOMIAL = 0x8408
    uiCrcValue = PRESET_VALUE

    for byte in data:
        uiCrcValue ^= byte
        for _ in range(8):
            if uiCrcValue & 0x0001:
                uiCrcValue = (uiCrcValue >> 1) ^ POLYNOMIAL
            else:
                uiCrcValue >>= 1
    return uiCrcValue


def interpret_response_status(status_code):
    """
    The interpret_response_status function translates status codes from the RFID reader (and possibly from tags,
    if applicable) into human-readable messages, facilitating debugging and operational monitoring
    :param status_code: Status code return by the rfid reader.
    """
    if status_code == 0x00:
        print("Successful execution.")
    elif status_code == 0x01:
        print("Parameter value is wrong or out of range.")
    elif status_code == 0x02:
        print("Command execution failed due to module internal error.")
    elif status_code == 0X03:
        print('Reserve')
    elif status_code == 0X12:
        print('There is no counting to the label or entire counting command is completed.')
    elif status_code == 0X14:
        print('Label response timeout')
    elif status_code == 0X15:
        print('Demodulation tag response error')
    elif status_code == 0X16:
        print('Protocol authentication failed.')
    elif status_code == 0X17:
        print('Password error')
    elif status_code == 0XFF:
        print('No more data')
    else:
        print(f"Unknown status code: {status_code}")


def send_rfid_reboot_command(connection, connection_type='serial'):
    """
        Function to send the reboot command(factory reset) to the rfid reader.
        :param connection: The connection established with the rfid reader.
        :param connection_type: The type of connection('serial' or 'tcp/ip(network)')
        :return status_code: Status code returned by the rfid reader (0X00 means success).
    """
    # According to the documentation, the reboot command structure is as follows:
    # HEAD 0xCF, ADDR 0xFF, CMD 0x0052, LEN 0x00, followed by CRC16
    command_bytes = [0xCF, 0xFF, 0x00, 0x52,
                     0x00]  # Construct the command in format - HEAD, ADDR, 0x00 and 0x52 together represent CMD, LEN
    crc16 = crc16_cal(bytes(command_bytes))  # Calculate CRC16
    command_bytes += [(crc16 >> 8) & 0xFF, crc16 & 0xFF]  # Append CRC16

    command = bytes(command_bytes)

    # Print the command being sent in hexadecimal format
    print('Sending command (Byte Format)', command)
    print(f"Sending command (Hexadecimal format): {binascii.hexlify(command)}")

    try:
        if connection_type == 'serial':
            connection.write(command)
            # Reading response with a flexible length, expecting at least 7 bytes for a valid response
            response = connection.read(10)  # Reading more bytes to ensure complete response
        elif connection_type == 'network':
            connection.sendall(command)
            response = connection.recv(1024)
        else:
            print("Unsupported connection type")
            return

        # Print the raw response received in hexadecimal format
        print(f"Raw response received: {binascii.hexlify(response)}")
        print('Byte format response received', response)

        if len(response) >= 7:  # Checking for minimum expected response length
            status_code = response[5]
            print('Status code ', status_code)
            interpret_response_status(status_code)
            return status_code
        else:
            print("Invalid or incomplete response received.")
            return None
    except Exception as e:
        print(f"Error sending reboot command: {e}")
        return None


def get_device_info(connection, connection_type='serial'):
    """
    This function sends the command to the rfid reader to obtain the current device version information, include CP
    module and RFID module hardware version number, firmware version and SN number.
    :param connection: The connection established with the rfid reader.
    :param connection_type: The type of connection('serial' or 'tcp/ip(network)')
    :return:  Returns the status_code and the response returned by the rfid reader.
    """
    command_bytes = [0xCF, 0xFF, 0x00, 0x70,
                     0x00]  # Construct the command in format - HEAD, ADDR, 0x00 and 0x70 together represent CMD, LEN
    crc16 = crc16_cal(bytes(command_bytes))  # Calculate CRC16 checksum
    command_bytes += [(crc16 >> 8) & 0xFF, crc16 & 0xFF]  # Appending CRC16 checksum to command
    command = bytes(command_bytes)

    print(f"Sending GET device info command (In byte format): {command}")
    print(f"Sending GET DEVICE INFO command (in hexadecimal format): {binascii.hexlify(command)}")

    try:
        if connection_type == 'serial':
            connection.write(command)
            response = connection.read(1024)  # Adjust based on the expected response length
        elif connection_type == 'network':
            connection.sendall(command)
            response = connection.recv(1024)
        else:
            print("Unsupported connection type")
            return None, None  # Return None for both status code and response if unsupported connection type

        print(f"Raw response received(Hexadecimal format): {binascii.hexlify(response)}")
        print(f"Raw response received (Byte format): {response}")

        # Process the response here as needed
        if response:
            status_code = response[5]
            print(f"Status code: {status_code}")
            interpret_response_status(status_code)
            return status_code, response  # Return both status code and raw response for further analysis

        else:
            print("Invalid or incomplete response received.")
            return None, None  # Return None if response is invalid or incomplete

    except Exception as e:
        print(f"Error sending GET DEVICE INFO command: {e}")
        return None, None  # Return None in case of exceptions


def stop_reading_mode(connection, connection_type='serial'):
    """
        Function for stopping the rfid reader reading.
        :param connection: The connection established with the rfid reader.
        :param connection_type: The type of connection('serial' or 'tcp/ip(network)')
        :return:  Returns the status_code returned by the rfid reader.
    """
    # Command format for RFM_INVENTORY_STOP
    command_bytes = [0xCF, 0xFF, 0x00, 0x02, 0x00]  # HEAD, ADDR, CMD, LEN
    crc16 = crc16_cal(bytes(command_bytes))  # Calculate the CRC16 checksum
    command_bytes += [(crc16 >> 8) & 0xFF, crc16 & 0xFF]  # Append CRC16 to the command

    command = bytes(command_bytes)  # Convert the command list to bytes

    try:
        if connection_type == 'serial':
            connection.write(command)
            response = connection.read(10)
        elif connection_type == 'network':
            connection.sendall(command)
            response = connection.recv(1024)
        else:
            print("Unsupported connection type")
            return None

        if len(response) >= 7:  # Basic validation for response length
            status_code = response[5]
            interpret_response_status(status_code)  # Interpret the status code from the response
            return status_code
        else:
            print("Invalid or incomplete response received.")
            return None
    except Exception as e:
        print(f"Error sending RFM_INVENTORY_STOP command: {e}")
        return None


def start_reading_mode(connection, connection_type, inv_type=0x00, inv_param=0):
    """
        The command sent by this function to the rfid reader will start the reading mode for an infinite period and rfid
        reading will continue until stop counting command is received.

        :param connection: The connection object (serial or socket)
        :param connection_type: The type of connection ('serial' or 'network')
        :param inv_type: Inventory type (0x00 for indefinite operation). Counting tag
        according to the time, stop counting after executing the specified time or stop counting after receiving the
        stop counting command;
        :param inv_param:  InvParam indicates the counting time, unit is seconds. If the value
        is 0, it indicates that the counting label will continue until the stop counting command is received;
    """
    command_bytes = [0xCF, 0xFF, 0x00, 0x01, 0x05, inv_type] + list(
        inv_param.to_bytes(4, byteorder='little'))  # list(inv_param.to_bytes(4, byteorder='little')):
    # Converts the inv_param (inventory parameter) into a 4-byte list, specifying the counting duration or number of
    # cycles, depending on inv_type. The byteorder='little' indicates the byte order is little-endian, meaning the
    # least significant byte is stored first.
    crc16 = crc16_cal(bytes(command_bytes))  # Calculate the CRC16 checksum
    command_bytes += [(crc16 >> 8) & 0xFF, crc16 & 0xFF]  # Append CRC16 to the command

    command = bytes(command_bytes)  # Convert the command list to bytes
    print(f'Sending Command in hexadecimal format: {binascii.hexlify(command)}')

    try:
        if connection_type == 'serial':
            connection.write(command)
            response = connection.read(1024)  # Read the response, adjust size as needed
        elif connection_type == 'network':
            connection.sendall(command)
            response = connection.recv(1024)  # Adjust based on expected response size
        else:
            print("Unsupported connection type")
            return

        print(f'Response from reader in hexadecimal format: {binascii.hexlify(response)}')
        # Basic validation for response length; adjust according to expected response
        if len(response) >= 7:
            print("Reading Mode is Starting.......")
            status_code = response[5]
            interpret_response_status(status_code)
            return status_code, response
        else:
            print("Invalid or no response received.")
            return None, None
    except Exception as e:
        print(f"Error sending RFM_INVENTORY_CONTINUE command: {e}")
        return None, None
