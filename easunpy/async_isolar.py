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

    async def _read_registers_bulk(self, register_groups: list[tuple[int, int]], data_format: str = "Int") -> list[list[int]]:
        """Read multiple groups of registers in a single connection."""
        try:
            # Create requests for each register group
            requests = [
                create_request(0x0777, 0x0001, 0x01, 0x03, start, count)
                for start, count in register_groups
            ]
            
            logger.debug(f"Sending bulk request for register groups: {register_groups}")
            responses = await self.client.send_bulk(requests)
             
            if not responses or len(responses) != len(register_groups):
                logger.warning(f"Incomplete or no responses received for bulk request. ${len(responses)} != ${len(register_groups)}")
                return []
            
            # Decode each response
            decoded_groups = []
            for response, (_, count) in zip(responses, register_groups):
                decoded = decode_modbus_response(response, count, data_format)
                logger.debug(f"Decoded values: {decoded}")
                decoded_groups.append(decoded)
                
            return decoded_groups
            
        except Exception as e:
            logger.error(f"Error reading register groups: {str(e)}")
            return []

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
        if not results or len(results) != len(register_groups):
            return None, None, None, None, None
            
        mode, battery_data, pv_general, pv1_data, pv2_data, grid_data, output_data, freq, others = results
        
        # Extract time data and create a timestamp
        try:
            year = others[0]
            month = others[1]
            day = others[2]
            hour = others[3]
            minute = others[4]
            second = others[5]
            inverter_timestamp = datetime.datetime(year, month, day, hour, minute, second)
        except ValueError as e:
            logger.error(f"Error creating timestamp: {e}")
            inverter_timestamp = None
        
        # Create BatteryData
        battery = None
        if len(battery_data) == 5:
            battery = BatteryData(
                voltage=battery_data[0] / 10.0,
                current=battery_data[1] / 10.0,
                power=battery_data[2],
                soc=battery_data[3],
                temperature=battery_data[4]
            )
            
        # Create PVData
        pv = None
        if len(pv_general) == 4 and len(pv1_data) == 3 and len(pv2_data) == 3:
            pv = PVData(
                total_power=pv_general[0],
                charging_power=pv_general[1],
                charging_current=pv_general[2] / 10.0,
                temperature=pv_general[3],
                pv1_voltage=pv1_data[0] / 10.0,
                pv1_current=pv1_data[1] / 10.0,
                pv1_power=pv1_data[2],
                pv2_voltage=pv2_data[0] / 10.0,
                pv2_current=pv2_data[1] / 10.0,
                pv2_power=pv2_data[2],
                pv_generated_today=others[6] / 100.0,
                pv_generated_total=others[7] / 100.0
            )
        
        # Create GridData
        grid = None
        if len(grid_data) == 3 and len(freq) == 1:
            grid = GridData(
                voltage=grid_data[0] / 10.0,
                power=grid_data[2],
                frequency=freq[0]
            )
            
        # Create OutputData
        output = None
        if len(output_data) == 5 and len(freq) == 1:
            output = OutputData(
                voltage=output_data[0] / 10.0,
                current=output_data[1] / 10.0,
                power=output_data[2],
                apparent_power=output_data[3],
                load_percentage=output_data[4],
                frequency=freq[0]
            )

        # Create SystemStatus - improved error handling
        status = None
        try:
            mode_value = mode[0]
            logger.debug(f"Raw mode value: {mode_value}")
            try:
                op_mode = OperatingMode(mode_value)
                status = SystemStatus(
                    operating_mode=op_mode,
                    mode_name=op_mode.name,
                    inverter_time=inverter_timestamp
                )
            except ValueError:
                logger.warning(f"Unknown operating mode value: {mode_value}")
                status = SystemStatus(
                    operating_mode=OperatingMode.FAULT,
                    mode_name=f"UNKNOWN ({mode_value})",
                    inverter_time=inverter_timestamp
                )
        except Exception as e:
            logger.error(f"Error processing system status: {e}")
            status = None
        
        return battery, pv, grid, output, status 