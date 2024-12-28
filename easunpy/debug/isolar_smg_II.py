import csv
from itertools import islice
import time

from easunpy.modbusclient import ModbusClient, get_registers_from_request, decode_modbus_response

def run_all_requests(inverter_ip: str, local_ip: str):
    """
    Run all Modbus requests from the extracted_requests_responses.csv file.
    
    Args:
        inverter_ip (str): IP address of the inverter
        local_ip (str): Local IP address to bind to
    """
    inverter = ModbusClient(inverter_ip=inverter_ip, local_ip=local_ip)

    try:
        with open('easunpy/extracted_requests_responses.csv', 'r') as csv_file:
            csv_reader = csv.DictReader(csv_file)
            while True:
                rows = list(islice(csv_reader, 2))
                if not rows:
                    break
                
                if len(rows) != 2:
                    print("Warning: Found incomplete request/response pair at end of file")
                    break

                request_row, expected_response_row = rows
                
                if request_row['Type'] != 'Request' or expected_response_row['Type'] != 'Response':
                    print("Error: Expected Request/Response pair, got:", 
                          f"{request_row['Type']}/{expected_response_row['Type']}")
                    continue

                hex_command = request_row['Payload']
                expected_response = expected_response_row['Payload']
                
                actual_response = inverter.send(hex_command)
                if actual_response:
                    print(f"{hex_command}:{actual_response}")
                    print(get_registers_from_request(hex_command))
                    print(decode_modbus_response(actual_response, len(get_registers_from_request(hex_command)), "Int"))
                else:
                    print("No response received")
                
                # Delay between requests
                time.sleep(1)

    except FileNotFoundError:
        print("Error: 'extracted_requests_responses.csv' file not found.")
    except KeyboardInterrupt:
        print("\nOperation interrupted by user")
    except Exception as e:
        print(f"Unexpected error: {e}")

if __name__ == '__main__':
    # Example usage
    run_all_requests('192.168.1.130', '192.168.1.135')
