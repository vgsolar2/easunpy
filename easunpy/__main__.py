"""Command-line interface for EasunPy"""

import socket
from .inverter import ModbusInverter 

def get_local_ip(target_ip):
    """Get the local IP address that would be used to reach the target IP"""
    try:
        # Create a dummy connection to determine the local IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect((target_ip, 1))  # Port number doesn't matter here
        local_ip = s.getsockname()[0]
        s.close()
        print("Local IP:",local_ip)
        return local_ip
    except Exception:
        print("ERROR: Failed to get local IP address")
        return '0.0.0.0'  # Fallback to default

def main():
    inverter = ModbusInverter()
    local_ip = get_local_ip('192.168.1.129')
    # Read a parameter
    inverter.run('BatteryVoltage', '192.168.1.129',local_ip=local_ip)  # Will return the decoded value

    # Or read an enum parameter
    inverter.run('BatteryType', '192.168.1.129', local_ip=local_ip)     # Will return the string representation

if __name__ == '__main__':
    main() 