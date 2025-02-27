import logging
from typing import List, Optional
from .async_modbusclient import AsyncModbusClient
from .modbusclient import create_request, decode_modbus_response
from .isolar import BatteryData, PVData, GridData, OutputData, SystemStatus, OperatingMode
import datetime

# Set up logging
logger = logging.getLogger(__name__)

class AsyncISolar:
    def __init__(self, inverter_ip: str, local_ip: str):
        self.client = AsyncModbusClient(inverter_ip=inverter_ip, local_ip=local_ip)

    async def _read_registers_bulk(self, register_groups: list[tuple[int, int]], data_format: str = "Int") -> list[Optional[list[int]]]:
        """Read multiple groups of registers in a single connection."""
        try:
            # Create requests for each register group
            requests = [
                create_request(0x0777, 0x0001, 0x01, 0x03, start, count)
                for start, count in register_groups
            ]
            
            logger.debug(f"Sending bulk request for register groups: {register_groups}")
            responses = await self.client.send_bulk(requests)
             
            # Initialize results array with None values
            decoded_groups = [None] * len(register_groups)
            
            # Process each response individually
            for i, (response, (_, count)) in enumerate(zip(responses, register_groups)):
                try:
                    if response:  # Only decode if we got a response
                        decoded = decode_modbus_response(response, count, data_format)
                        logger.debug(f"Decoded values for group {i}: {decoded}")
                        decoded_groups[i] = decoded
                    else:
                        logger.warning(f"No response for register group {register_groups[i]}")
                except Exception as e:
                    logger.warning(f"Failed to decode register group {register_groups[i]}: {e}")
                    # Keep None for this group
                
            return decoded_groups
            
        except Exception as e:
            logger.error(f"Error reading register groups: {str(e)}")
            return [None] * len(register_groups)

    async def get_all_data(self) -> tuple[Optional[BatteryData], Optional[PVData], Optional[GridData], Optional[OutputData], Optional[SystemStatus]]:
        """Get all inverter data in a single bulk request."""
        register_groups = [
            (201, 1),  # Mode
            
            # Battery data (277-281)
            (277, 5),  # voltage, current, power, soc, temperature
            
            # PV data
            (302, 4),  # PV general: total_power, charging_power, charging_current, temperature
            (351, 3),  # PV1: voltage, current, power
            (389, 3),  # PV2: voltage, current, power
            
            # Grid data
            (338, 3),  # voltage, current, power
            
            # Output data
            (346, 5),  # voltage, current, power, apparent_power, load_percentage
            
            # Frequency (used by both grid and output)
            (607, 1),  # frequency
            
            (696, 10), # Time, PV generated today and total.
            
        ]
        
        results = await self._read_registers_bulk(register_groups)
        
        # Unpack results, handling None values
        mode = results[0] if results else None
        battery_data = results[1] if results else None
        pv_general = results[2] if results else None
        pv1_data = results[3] if results else None
        pv2_data = results[4] if results else None
        grid_data = results[5] if results else None
        output_data = results[6] if results else None
        freq = results[7] if results else None
        others = results[8] if results else None

        # Create BatteryData if we have the data
        battery = None
        if battery_data and len(battery_data) == 5:
            try:
                battery = BatteryData(
                    voltage=battery_data[0] / 10.0,
                    current=battery_data[1] / 10.0,
                    power=battery_data[2],
                    soc=battery_data[3],
                    temperature=battery_data[4]
                )
            except Exception as e:
                logger.warning(f"Failed to create BatteryData: {e}")

        # Create PVData if we have the required data
        pv = None
        if any([pv_general, pv1_data, pv2_data]):  # Create PV object if we have any PV data
            try:
                pv = PVData(
                    total_power=pv_general[0] if pv_general else None,
                    charging_power=pv_general[1] if pv_general else None,
                    charging_current=(pv_general[2] / 10.0) if pv_general else None,
                    temperature=pv_general[3] if pv_general else None,
                    pv1_voltage=(pv1_data[0] / 10.0) if pv1_data else None,
                    pv1_current=(pv1_data[1] / 10.0) if pv1_data else None,
                    pv1_power=pv1_data[2] if pv1_data else None,
                    pv2_voltage=(pv2_data[0] / 10.0) if pv2_data else None,
                    pv2_current=(pv2_data[1] / 10.0) if pv2_data else None,
                    pv2_power=pv2_data[2] if pv2_data else None,
                    pv_generated_today=(others[6] / 100.0) if others else None,
                    pv_generated_total=(others[7] / 100.0) if others else None
                )
            except Exception as e:
                logger.warning(f"Failed to create PVData: {e}")

        # Create GridData if we have the data
        grid = None
        if grid_data or freq:
            try:
                grid = GridData(
                    voltage=(grid_data[0] / 10.0) if grid_data else None,
                    power=grid_data[2] if grid_data else None,
                    frequency=freq[0] if freq else None
                )
            except Exception as e:
                logger.warning(f"Failed to create GridData: {e}")

        # Create OutputData if we have the data
        output = None
        if output_data or freq:
            try:
                output = OutputData(
                    voltage=(output_data[0] / 10.0) if output_data else None,
                    current=(output_data[1] / 10.0) if output_data else None,
                    power=output_data[2] if output_data else None,
                    apparent_power=output_data[3] if output_data else None,
                    load_percentage=output_data[4] if output_data else None,
                    frequency=freq[0] if freq else None
                )
            except Exception as e:
                logger.warning(f"Failed to create OutputData: {e}")

        # Create SystemStatus
        status = None
        try:
            inverter_timestamp = None
            if others:
                try:
                    year, month, day, hour, minute, second = others[:6]
                    inverter_timestamp = datetime.datetime(year, month, day, hour, minute, second)
                except Exception as e:
                    logger.warning(f"Failed to create timestamp: {e}")

            if mode:
                mode_value = mode[0]
                try:
                    op_mode = OperatingMode(mode_value)
                    status = SystemStatus(
                        operating_mode=op_mode,
                        mode_name=op_mode.name,
                        inverter_time=inverter_timestamp
                    )
                except ValueError:
                    status = SystemStatus(
                        operating_mode=OperatingMode.FAULT,
                        mode_name=f"UNKNOWN ({mode_value})",
                        inverter_time=inverter_timestamp
                    )
        except Exception as e:
            logger.warning(f"Failed to create SystemStatus: {e}")

        return battery, pv, grid, output, status 