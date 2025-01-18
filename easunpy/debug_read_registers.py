import asyncio
import logging
import time
from easunpy.async_isolar import AsyncISolar

# Configure logging to output to the console
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

async def debug_read_registers(inverter_ip: str, local_ip: str):
    inverter = AsyncISolar(inverter_ip, local_ip)
    
    # Define different register ranges to test
    test_cases = [
        (338, 10),  # Example: Read 10 registers starting from 338
        (302, 10),  # Example: Read 10 registers starting from 302
        (277, 10),  # Example: Read 10 registers starting from 277
        # Add more test cases as needed
    ]
    
    for start_register, count in test_cases:
        try:
            logging.error(f"Testing read from register {start_register} with count {count}")
            start_time = time.time()  # Record start time
            values = await inverter._read_registers(start_register, count)
            end_time = time.time()  # Record end time
            duration = end_time - start_time
            logging.error(f"Read values: {values}")
            logging.error(f"Time taken: {duration:.4f} seconds")
        except Exception as e:
            logging.error(f"Error reading registers {start_register}-{start_register + count - 1}: {str(e)}")

if __name__ == "__main__":
    # Replace with actual IP addresses
    inverter_ip = "192.168.1.128"
    local_ip = "192.168.1.132"
    
    asyncio.run(debug_read_registers(inverter_ip, local_ip)) 