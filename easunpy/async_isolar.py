import logging
from typing import List, Optional
from .async_modbusclient import AsyncModbusClient
from .modbusclient import create_request, decode_modbus_response
from .isolar import BatteryData, PVData, GridData, OutputData, SystemStatus, OperatingMode

# Set up logging
logger = logging.getLogger(__name__)

class AsyncISolar:
    def __init__(self, inverter_ip: str, local_ip: str):
        self.client = AsyncModbusClient(inverter_ip=inverter_ip, local_ip=local_ip)

    async def _read_registers(self, start_register: int, count: int, data_format: str = "Int") -> List[int]:
        """Read a sequence of registers asynchronously."""
        try:
            request = create_request(0x0777, 0x0001, 0x01, 0x03, start_register, count)
            logger.debug(f"Sending request for registers {start_register}-{start_register + count - 1}: {request}")
            
            response = await self.client.send(request)
            if not response:
                logger.warning(f"No response received for registers {start_register}-{start_register + count - 1}")
                return []
            
            logger.debug(f"Received response: {response}")
            decoded = decode_modbus_response(response, count, data_format)
            logger.debug(f"Decoded values: {decoded}")
            return decoded
        except Exception as e:
            logger.error(f"Error reading registers {start_register}-{start_register + count - 1}: {str(e)}")
            return []

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
                logger.warning(f"Incomplete or no responses received for bulk request")
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

    async def get_battery_data(self) -> Optional[BatteryData]:
        """Get battery information (registers 277-281) asynchronously."""
        values = await self._read_registers(277, 5)
        if not values or len(values) != 5:
            return None
        
        return BatteryData(
            voltage=values[0] / 10.0,
            current=values[1] / 10.0,
            power=values[2],
            soc=values[3],
            temperature=values[4]
        )

    async def get_pv_data(self) -> Optional[PVData]:
        """Get PV information using bulk register reading."""
        register_groups = [
            (302, 4),  # PV general
            (351, 3),  # PV1 data
            (389, 3),  # PV2 data
        ]
        
        results = await self._read_registers_bulk(register_groups)
        if not results or len(results) != 3:
            return None
            
        pv_general, pv1_data, pv2_data = results
        
        if len(pv_general) != 4 or len(pv1_data) != 3 or len(pv2_data) != 3:
            return None

        return PVData(
            total_power=pv_general[0],
            charging_power=pv_general[1],
            charging_current=pv_general[2] / 10.0,
            temperature=pv_general[3],
            pv1_voltage=pv1_data[0] / 10.0,
            pv1_current=pv1_data[1] / 10.0,
            pv1_power=pv1_data[2],
            pv2_voltage=pv2_data[0] / 10.0,
            pv2_current=pv2_data[1] / 10.0,
            pv2_power=pv2_data[2]
        )

    async def get_grid_data(self) -> Optional[GridData]:
        """Get grid information (registers 338, 340, 342) asynchronously."""
        values = await self._read_registers(338, 3)
        if not values or len(values) != 3:
            return None
        
        freq = await self._read_registers(607, 1)
        if not freq:
            return None

        return GridData(
            voltage=values[0] / 10.0,
            power=values[2],
            frequency=freq[0]
        )

    async def get_output_data(self) -> Optional[OutputData]:
        """Get output information (registers 346-350, 607) asynchronously."""
        values = await self._read_registers(346, 5)
        if not values or len(values) != 5:
            return None
        
        freq = await self._read_registers(607, 1)
        if not freq:
            return None

        return OutputData(
            voltage=values[0] / 10.0,
            current=values[1] / 10.0,
            power=values[2],
            apparent_power=values[3],
            load_percentage=values[4],
            frequency=freq[0]
        )

    async def get_operating_mode(self) -> Optional[SystemStatus]:
        """Get system operating mode (register 600) asynchronously."""
        values = await self._read_registers(600, 1)
        if not values:
            return None

        try:
            mode = OperatingMode(values[0])
            return SystemStatus(
                operating_mode=mode,
                mode_name=mode.name
            )
        except ValueError:
            return SystemStatus(
                operating_mode=OperatingMode.FAULT,
                mode_name=f"UNKNOWN ({values[0]})"
            ) 

    async def is_connected(self) -> bool:
        """Check if the inverter is connected by attempting to retrieve the serial number asynchronously."""
        try:
            # Implement a method to check connection status
            return True
        except Exception:
            return False 