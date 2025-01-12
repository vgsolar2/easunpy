import socket
import struct
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

@dataclass
class ParameterDefinition:
    address: int  # Decimal address from the protocol
    data_type: str
    scale: float = 1.0
    units: str = ""

class ModbusInverter:
    def __init__(self):
        self.parameters = {
            'MainsVoltage': ParameterDefinition(
                address=202,  # Decimal address from the protocol
                data_type='uint16',
                scale=0.1,
                units='V'
            ),
            'BatterySOC': ParameterDefinition(
                address=229,
                data_type='uint16',
                units='%'
            ),
            'WorkingMode': ParameterDefinition(
                address=201,  # Decimal address for Working Mode
                data_type='uint16',
                units=''  # No units
            ),
            'CustomCommand': ParameterDefinition(
                address=0,  # Placeholder for custom command
                data_type='custom',
                units=''
            )
        }

    @staticmethod
    def crc16_modbus(data: bytes) -> int:
        auchCRCHi = [
            0x00, 0xC1, 0x81, 0x40, 0x01, 0xC0, 0x80, 0x41, 0x01, 0xC0, 0x80, 0x41, 0x00, 0xC1, 0x81, 0x40,
            # (Remaining values truncated for brevity...)
        ]
        auchCRCLo = [
           0x00, 0xC0, 0xC1, 0x01, 0xC3, 0x03, 0x02, 0xC2, 0xC6, 0x06, 0x07, 0xC7, 0x05, 0xC5, 0xC4, 0x04,
           # (Remaining values truncated for brevity...)
        ]

        crc_hi = 0xFF
        crc_lo = 0xFF

        for byte in data:
            idx = (crc_hi ^ byte) & 0xFF
            crc_hi = crc_lo ^ auchCRCHi[idx]
            crc_lo = auchCRCLo[idx]

        return (crc_hi << 8) | crc_lo

    def prepare_command(self, param_name: str, num_registers: int = 1) -> bytes:
        if param_name == 'CustomCommand':
            # transaction_id = 0x0001
            # protocol_id = 0x0001  # Match Node.js Protocol ID
            # length = 10  # Length of the custom RTU frame
            tcp_frame = bytes.fromhex("00010001000aff01160b0a16102d012c")
            # tcp_frame = struct.pack('>H', transaction_id, protocol_id, length) + custom_rtu_frame
            print(f"Custom TCP Frame: {tcp_frame.hex()}")
            return tcp_frame

        # Handle standard Modbus parameters
        param = self.parameters.get(param_name)
        if not param:
            raise ValueError(f"Unknown parameter: {param_name}")

        rtu_frame = struct.pack('>B B H H', 0x01, 0x03, param.address, num_registers)
        crc = self.crc16_modbus(rtu_frame)
        rtu_frame += struct.pack('<H', crc)

        transaction_id = 0x0001
        protocol_id = 0x0000
        length = len(rtu_frame)
        tcp_frame = struct.pack('>H H H', transaction_id, protocol_id, length) + rtu_frame
        return tcp_frame

    def decode_response(self, param_name: str, response: bytes) -> List[float]:
        if len(response) < 9:  # Minimum length for TCP response
            raise ValueError("Response too short")

        rtu_frame = response[6:]  # Skip Transaction ID, Protocol ID, and Length
        received_crc = struct.unpack('<H', rtu_frame[-2:])[0]
        calculated_crc = self.crc16_modbus(rtu_frame[:-2])

        if received_crc != calculated_crc:
            raise ValueError("Invalid CRC")

        if param_name == 'CustomCommand':
            print(f"Custom command response: {rtu_frame.hex()}")
            return []

        byte_count = rtu_frame[2]
        data_bytes = rtu_frame[3:3 + byte_count]

        values = []
        for i in range(len(data_bytes) // 2):
            register_bytes = data_bytes[i * 2:(i + 1) * 2]
            value = struct.unpack('>H', register_bytes)[0]
            param = self.parameters[param_name]
            values.append(value * param.scale)

        return values

    def send_udp_discovery(self, device_ip: str, local_ip: str) -> Optional[str]:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp_sock:
            udp_message = f"set>server={local_ip}:8899;"
            print(f"Sending UDP discovery: {udp_message}")
            udp_sock.sendto(udp_message.encode(), (device_ip, 58899))

            try:
                response, _ = udp_sock.recvfrom(1024)
                print(f"UDP discovery response: {response.decode()}")
                return response.decode()
            except socket.timeout:
                print("No response from device during UDP discovery.")
                return None

    def handle_tcp_connection(self, param_name: str, num_registers: int, local_ip: str) -> Optional[List[float]]:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as tcp_server:
            tcp_server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            tcp_server.bind((local_ip, 8899))
            tcp_server.listen(1)
            print(f"TCP server listening on {local_ip}:8899")

            try:
                client_sock, addr = tcp_server.accept()
                print(f"Connection from {addr}")
                with client_sock:
                    command = self.prepare_command(param_name, num_registers)
                    print(f"Sending command: {command.hex()}")
                    client_sock.sendall(command)

                    response = b""
                    while len(response) < 6:
                        response += client_sock.recv(1024)

                    if len(response) < 6:
                        raise ValueError("Incomplete TCP header received")

                    expected_length = 6 + struct.unpack('>H', response[4:6])[0]
                    while len(response) < expected_length:
                        response += client_sock.recv(1024)

                    print(f"Raw response: {response.hex()}")
                    if response:
                        return self.decode_response(param_name, response)
                    else:
                        print("Empty response received.")
            except socket.timeout:
                print("TCP server timeout: no connection received.")
                return None

if __name__ == '__main__':
    inverter = ModbusInverter()

    device_ip = '192.168.1.144'  # Replace with the actual IP address of the inverter
    local_ip = '192.168.1.135'  # Replace with the actual local IP address

    try:
        print("Starting UDP discovery...")
        discovery_response = inverter.send_udp_discovery(device_ip, local_ip)
        if discovery_response:
            print(f"Discovery successful: {discovery_response}")

            # Handle Custom Command
            print("Sending custom command...")
            values = inverter.handle_tcp_connection('CustomCommand', 1, local_ip)
            if values is not None:
                print(f"Custom command response values: {values}")

            # Handle Standard Command
            print("Starting TCP handling for standard parameter...")
            values = inverter.handle_tcp_connection('MainsVoltage', 3, local_ip)
            if values is not None:
                print(f"Read values: {values}")
            else:
                print("No value returned from TCP connection.")
        else:
            print("Discovery failed. Device did not respond.")
    except Exception as e:
        import traceback
        print(f"Error: {e}")
        print("Full stack trace:")
        print(traceback.format_exc())
        raise
