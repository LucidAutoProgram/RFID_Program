import serial
import binascii
import asyncio


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


async def open_net_connection(ip, port, timeout=3):
    """
        Asynchronously establish a network connection to the RFID reader with a timeout.

        :param ip: The IP address to connect to.
        :param port: The port number to connect to.
        :param timeout: The timeout in seconds for the connection attempt.
        :return: A tuple of (reader, writer) if the connection is successful, (None, None) otherwise.
    """
    try:
        # Use asyncio.wait_for to apply a timeout to the connection attempt
        reader, writer = await asyncio.wait_for(asyncio.open_connection(ip, port), timeout)
        print(f"Network connection established to {ip}:{port}")
        return reader, writer
    except asyncio.TimeoutError:
        print(f"Connection attempt to {ip}:{port} timed out after {timeout} seconds.")
        return None, None
    except Exception as e:
        print(f"Failed to connect to {ip}:{port}: {e}")
        return None, None


def close_serial_connection(serial_connection):
    """
        Function to close the serial connection.
        :param serial_connection: Connection established using serial.
    """
    serial_connection.close()
    print("Serial connection closed.")


async def close_network_connection(writer):
    """
        Asynchronously close the network connection.
        :param writer: StreamWriter object from the async connection.
    """
    writer.close()
    await writer.wait_closed()
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


async def start_reading_mode(reader, writer, inv_type=0x00, inv_param=0):
    """
        Asynchronously sends a command to start the RFID reading mode and continuously reads responses.
        :param reader: For reading the response from the rfid reader.
        :param writer: Connection established.
    """
    command_bytes = [0xCF, 0xFF, 0x00, 0x01, 0x05, inv_type] + list(inv_param.to_bytes(4, byteorder='little'))
    crc16 = crc16_cal(bytes(command_bytes))  # Assuming crc16_cal is defined elsewhere
    command_bytes += [(crc16 >> 8) & 0xFF, crc16 & 0xFF]
    command = bytes(command_bytes)
    print(f'Sending Command in hexadecimal format: {binascii.hexlify(command)}')
    writer.write(command)
    await writer.drain()


async def stop_reading_mode(writer):
    """
        Asynchronously sends a command to stop the RFID reading mode.
    """
    command_bytes = [0xCF, 0xFF, 0x00, 0x02, 0x00]
    crc16 = crc16_cal(bytes(command_bytes))
    command_bytes += [(crc16 >> 8) & 0xFF, crc16 & 0xFF]
    command = bytes(command_bytes)
    writer.write(command)
    await writer.drain()
