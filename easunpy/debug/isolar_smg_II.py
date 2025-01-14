import asyncio
import logging
import time  # Import the time module
from easunpy.async_isolar import AsyncISolar
from easunpy.discover import discover_device
from easunpy.utils import get_local_ip

async def debug_inverter_data_async():
    """
    Debug and display inverter data asynchronously.
    """
    # Set up logging for all easunpy modules
    logging.basicConfig(level=logging.DEBUG)
    logger = logging.getLogger('easunpy')
    logger.setLevel(logging.DEBUG)

    # Discover local IP
    local_ip = get_local_ip()
    if not local_ip:
        logger.error("Could not determine local IP address.")
        return

    logger.debug(f"Local IP: {local_ip}")

    # Discover inverter IP
    logger.debug("Discovering inverter IP...")
    device_ip = discover_device()
    if not device_ip:
        logger.error("No inverter IPs discovered.")
        return

    logger.debug(f"Discovered inverter IP: {device_ip}")

    # Initialize inverter
    inverter = AsyncISolar(device_ip, local_ip)
    
    # Get all the data asynchronously
    start_time = time.time()  # Start timing for battery data
    battery = await inverter.get_battery_data()
    battery_duration = time.time() - start_time
    logger.info(f"Time taken to get battery data: {battery_duration:.2f} seconds")

    start_time = time.time()  # Start timing for PV data
    pv = await inverter.get_pv_data()
    pv_duration = time.time() - start_time
    logger.info(f"Time taken to get PV data: {pv_duration:.2f} seconds")

    start_time = time.time()  # Start timing for grid data
    grid = await inverter.get_grid_data()
    grid_duration = time.time() - start_time
    logger.info(f"Time taken to get grid data: {grid_duration:.2f} seconds")

    start_time = time.time()  # Start timing for output data
    output = await inverter.get_output_data()
    output_duration = time.time() - start_time
    logger.info(f"Time taken to get output data: {output_duration:.2f} seconds")

    start_time = time.time()  # Start timing for system status
    system = await inverter.get_operating_mode()
    system_duration = time.time() - start_time
    logger.info(f"Time taken to get operating mode: {system_duration:.2f} seconds")
    
    # Display data in plain text
    print("Inverter Data Debugging:")
    
    if battery:
        print("Battery Data:")
        print(f"  Voltage: {battery.voltage}V")
        print(f"  Current: {battery.current}A")
        print(f"  Power: {battery.power}W")
        print(f"  State of Charge: {battery.soc}%")
        print(f"  Temperature: {battery.temperature}°C")
        print(f"  Retrieval Time: {battery_duration:.2f} seconds")
    
    if pv:
        print("PV Data:")
        print(f"  Total Power: {pv.total_power}W")
        print(f"  Charging Power: {pv.charging_power}W")
        print(f"  Charging Current: {pv.charging_current}A")
        print(f"  PV1 Voltage: {pv.pv1_voltage}V")
        print(f"  PV1 Current: {pv.pv1_current}A")
        print(f"  PV1 Power: {pv.pv1_power}W")
        print(f"  PV2 Voltage: {pv.pv2_voltage}V")
        print(f"  PV2 Current: {pv.pv2_current}A")
        print(f"  PV2 Power: {pv.pv2_power}W")
        print(f"  Retrieval Time: {pv_duration:.2f} seconds")
    
    if grid:
        print("Grid Data:")
        print(f"  Voltage: {grid.voltage}V")
        print(f"  Power: {grid.power}W")
        print(f"  Frequency: {grid.frequency/100:.2f}Hz")
        print(f"  Retrieval Time: {grid_duration:.2f} seconds")
    
    if output:
        print("Output Data:")
        print(f"  Voltage: {output.voltage}V")
        print(f"  Current: {output.current}A")
        print(f"  Power: {output.power}W")
        print(f"  Apparent Power: {output.apparent_power}VA")
        print(f"  Load Percentage: {output.load_percentage}%")
        print(f"  Frequency: {output.frequency/100:.2f}Hz")
        print(f"  Retrieval Time: {output_duration:.2f} seconds")
    
    if system:
        print("System Status:")
        print(f"  Operating Mode: {system.mode_name}")
        print(f"  Retrieval Time: {system_duration:.2f} seconds")

if __name__ == '__main__':
    # Run the async debug function
    asyncio.run(debug_inverter_data_async())
