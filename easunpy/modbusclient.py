import socket
import struct
import time
import logging  # Import logging

import pandas as pd
from easunpy.crc import crc16_modbus

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ModbusClient:
    def __init__(self, inverter_ip: str, local_ip: str, port: int = 8899):
        self.inverter_ip = inverter_ip
        self.local_ip = local_ip
        self.port = port
        self.request_id = 0  # Add request ID counter

    def send_udp_discovery(self) -> bool:
        """Perform UDP discovery to initialize the inverter communication."""
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp_sock:
            udp_message = f"set>server={self.local_ip}:{self.port};"
            try:
                logger.debug(f"Sending UDP discovery message to {self.inverter_ip}:58899")
                udp_sock.sendto(udp_message.encode(), (self.inverter_ip, 58899))
                response, _ = udp_sock.recvfrom(1024)
                return True
            except socket.timeout:
                logger.error("UDP discovery timed out")
                return False
            except Exception as e:
                logger.error(f"Error sending UDP discovery message: {e}")
                return False

    def send(self, hex_command: str, retry_count: int = 2) -> str:
        """Send a Modbus TCP command."""
        command_bytes = bytes.fromhex(hex_command)
        logger.info(f"Sending command: {hex_command}")

        for attempt in range(retry_count):
            logger.debug(f"Attempt {attempt + 1} of {retry_count}")
            
            if not self.send_udp_discovery():
                logger.info("UDP discovery failed")
                time.sleep(1)
                continue

            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as tcp_server:
                tcp_server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                tcp_server.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, struct.pack('ii', 1, 0))
                
                try:
                    # Attempt to bind to the local IP and port
                    logger.debug(f"Binding to {self.local_ip}:{self.port}")
                    tcp_server.bind((self.local_ip, self.port))
                    tcp_server.listen(1)

                    logger.debug("Waiting for client connection...")
                    client_sock, addr = tcp_server.accept()
                    logger.info(f"Client connected from {addr}")
                    
                    with client_sock:
                        logger.debug("Sending command bytes...")
                        client_sock.sendall(command_bytes)

                        logger.debug("Waiting for response...")
                        response = client_sock.recv(1024)
                        
                        if len(response) >= 6:
                            expected_length = int.from_bytes(response[4:6], 'big') + 6
                            
                            while len(response) < expected_length:
                                chunk = client_sock.recv(1024)
                                if not chunk:
                                    break
                                response += chunk

                        response_hex = response.hex()
                        logger.info(f"Received response: {response_hex}")
                        return response_hex

                except socket.timeout:
                    logger.info("Socket timeout")
                    time.sleep(1)
                    continue
                except Exception as e:
                    logger.error(f"Error: {str(e)}")
                    time.sleep(1)
                    continue

        logger.info("All retry attempts failed")
        return ""

def run_single_request(inverter_ip: str, local_ip: str, request: str):
    """
    Sends a single Modbus request to the inverter.
    """
    inverter = ModbusClient(inverter_ip=inverter_ip, local_ip=local_ip)
    response = inverter.send(request)
    return response

# Función para crear la solicitud completa
def create_request(transaction_id: int, protocol_id: int, unit_id: int, function_code: int,
                   register_address: int, register_offset: int) -> str:
    """
    Create a Modbus command with the correct length and CRC for the RTU packet.
    """
    # Construir el paquete RTU
    rtu_packet = bytearray([
        unit_id,
        function_code,
        (register_address >> 8) & 0xFF, register_address & 0xFF,
        (register_offset >> 8) & 0xFF, register_offset & 0xFF
    ])

    # Calcular el CRC para el paquete RTU
    crc = crc16_modbus(rtu_packet)
    crc_low = crc & 0xFF
    crc_high = (crc >> 8) & 0xFF

    # Agregar CRC al paquete RTU
    rtu_packet.extend([crc_low, crc_high])
    
    # Campo adicional `FF04`
    rtu_packet = bytearray([0xFF, 0x04]) + rtu_packet
    
    # Calcular la longitud total (incluye solo RTU) + TCP
    length = len(rtu_packet)
    
    # Construir el comando completo
    command = bytearray([
        (transaction_id >> 8) & 0xFF, transaction_id & 0xFF,  # Transaction ID
        (protocol_id >> 8) & 0xFF, protocol_id & 0xFF,        # Protocol ID
        (length >> 8) & 0xFF, length & 0xFF                  # Longitud
    ]) + rtu_packet

    return command.hex()

def decode_modbus_response(response: str, register_count: int=1, data_format: str="Int"):
    """
    Decodes a Modbus TCP response using the provided format.
    :param request: Hexadecimal string of the Modbus request.
    :param response: Hexadecimal string of the Modbus response.
    :return: Dictionary with register addresses and their values.
    """
    # Extract common fields from response
    req_id = response[:8]
    length_hex = response[8:12]
    length = int(length_hex, 16)
    
    # Extract RTU payload
    rtu_payload = response[12:12 + length * 2]

    # Decode RTU Payload
    extra_field = rtu_payload[:2]
    device_address = rtu_payload[2:4]
    function_code = rtu_payload[4:6]
    num_data_bytes = int(rtu_payload[8:10], 16)
    data_bytes = rtu_payload[10:10 + num_data_bytes * 2]
    # Decode the register values and pair with addresses
    values = []
    for i, _ in enumerate(range(register_count)):
        if data_format == "Int":
            # Handle signed 16-bit integers
            value = int(data_bytes[i * 4:(i + 1) * 4], 16)
            # If the highest bit is set (value >= 32768), it's negative
            if value >= 32768:  # 0x8000
                value -= 65536  # 0x10000
        elif data_format == "UnsignedInt":
            # Handle unsigned 16-bit integers (0 to 65535)
            value = int(data_bytes[i * 4:(i + 1) * 4], 16)
        elif data_format == "Float":
            value = struct.unpack('f', bytes.fromhex(data_bytes[i * 4:(i + 1) * 4]))[0]
        else:
            raise ValueError(f"Unsupported data format: {data_format}")
        values.append(value)

    return values

def get_registers_from_request(request: str) -> list:
    """
    Extracts register addresses from a Modbus request
    :param request: Hexadecimal string of the Modbus request
    :return: List of register addresses
    """
    rtu_payload = request[12:]  # Skip TCP header
    register_address = int(rtu_payload[8:12], 16)  # Get register address from RTU payload
    register_count = int(rtu_payload[12:16], 16)  # Get number of registers
    
    registers = []
    for i in range(register_count):
        registers.append(register_address + i)
        
    return registers
