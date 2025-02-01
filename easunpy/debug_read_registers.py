import asyncio
import logging
import time
from easunpy.async_isolar import AsyncISolar
from easunpy.discover import discover_device
from easunpy.utils import get_local_ip
from easunpy.modbusclient import create_request

# Configure logging to output to the console
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

async def debug_read_registers(inverter_ip: str, local_ip: str):
    inverter = AsyncISolar(inverter_ip, local_ip)
    
    # Define test cases - PV data registers
    test_cases = [
        (302, 4),   # PV general
        (351, 3),   # PV1 data
        (389, 3),   # PV2 data
    ]
    
    # Test regular sequential reads
    logging.info("\n=== Testing sequential reads ===")
    sequential_start = time.time()
    for start_register, count in test_cases:
        try:
            logging.info(f"Testing read from register {start_register} with count {count}")
            start_time = time.time()
            values = await inverter._read_registers(start_register, count)
            duration = time.time() - start_time
            logging.info(f"Read values: {values}")
            logging.info(f"Individual read time: {duration:.4f} seconds")
        except Exception as e:
            logging.error(f"Error reading registers {start_register}-{start_register + count - 1}: {str(e)}")
    sequential_total = time.time() - sequential_start
    logging.info(f"Total time for sequential reads: {sequential_total:.4f} seconds")

    await asyncio.sleep(5)
    
    # Test bulk reads
    logging.info("\n=== Testing bulk reads ===")
    try:
        # Create requests for the same PV data registers
        bulk_requests = [
            create_request(0x0777, 0x0001, 0x01, 0x03, start, count)
            for start, count in test_cases
        ]
        
        bulk_start = time.time()
        responses = await inverter.client.send_bulk(bulk_requests)
        bulk_total = time.time() - bulk_start
        
        logging.info(f"Bulk read responses: {responses}")
        logging.info(f"Total time for bulk reads: {bulk_total:.4f} seconds")
        
        # Show comparison
        logging.info("\n=== Performance Comparison ===")
        logging.info(f"Sequential reads total time: {sequential_total:.4f} seconds")
        logging.info(f"Bulk reads total time: {bulk_total:.4f} seconds")
        logging.info(f"Time saved with bulk reads: {(sequential_total - bulk_total):.4f} seconds")
        logging.info(f"Performance improvement: {((sequential_total - bulk_total) / sequential_total * 100):.1f}%")
        
    except Exception as e:
        logging.error(f"Error during bulk read test: {str(e)}")

if __name__ == "__main__":
    local_ip = get_local_ip()
    print("Discovering inverter IP...")
    device_ip = discover_device()
    if device_ip:
        inverter_ip = device_ip
        print(f"Discovered inverter IP: {inverter_ip}")
        asyncio.run(debug_read_registers(inverter_ip, local_ip))
    else:
        print("Error: Could not discover inverter IP") 