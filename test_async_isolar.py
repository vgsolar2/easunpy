import asyncio
import logging
from easunpy.async_isolar import AsyncISolar
from easunpy.utils import get_local_ip
from easunpy.discover import discover_device

async def test_get_all_data():
    # Discover local IP
    local_ip = get_local_ip()
    if not local_ip:
        print("Error: Could not determine local IP address")
        return
    
    # Discover inverter IP
    print("Discovering inverter IP...")
    inverter_ip = discover_device()
    if not inverter_ip:
        print("Error: Could not discover inverter IP")
        return
    
    # Initialize the AsyncISolar instance
    inverter = AsyncISolar(inverter_ip, local_ip, model="ISOLAR_SMG_II_11K")
    
    try:
        # Call the get_all_data method
        battery, pv, grid, output, status = await inverter.get_all_data()
        
        # Print the results
        print("Battery Data:", battery)
        print("PV Data:", pv)
        print("Grid Data:", grid)
        print("Output Data:", output)
        print("System Status:", status)
        
    except Exception as e:
        # Print any exceptions that occur
        print(f"An error occurred: {e}")
        import traceback
        print("\nFull traceback:")
        traceback.print_exc()

if __name__ == "__main__":
    # Configure logging to see debug output
    logging.basicConfig(level=logging.DEBUG)
    
    # Run the test
    asyncio.run(test_get_all_data()) 