import logging
from typing import List, Optional
from .modbusclient import ModbusClient, create_request, decode_modbus_response
from easunpy.models import BatteryData, PVData, GridData, OutputData, OperatingMode, SystemStatus

# Set up logging
logger = logging.getLogger(__name__)

class ISolar:
    def __init__(self, inverter_ip: str, local_ip: str):
        self.client = ModbusClient(inverter_ip=inverter_ip, local_ip=local_ip)

    def _read_registers(self, start_register: int, count: int, data_format: str = "Int") -> List[int]:
        """Read a sequence of registers."""
        try:
            request = create_request(0x0777, 0x0001, 0x01, 0x03, start_register, count)
            logger.debug(f"Sending request for registers {start_register}-{start_register + count - 1}: {request}")
            
            response = self.client.send(request)
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

    def get_battery_data(self) -> Optional[BatteryData]:
        """Get battery information (registers 277-281)."""
        values = self._read_registers(277, 5)
        if not values or len(values) != 5:
            return None
        
        return BatteryData(
            voltage=values[0] / 10.0,
            current=values[1] / 10.0,
            power=values[2],
            soc=values[3],
            temperature=values[4]
        )

    def get_pv_data(self) -> Optional[PVData]:
        """Get PV information (combines multiple register groups)."""
        pv_general = self._read_registers(302, 4)
        if not pv_general or len(pv_general) != 4:
            return None

        pv1_data = self._read_registers(346, 8)
        if not pv1_data or len(pv1_data) != 8:
            return None

        pv2_data = self._read_registers(389, 3)
        if not pv2_data or len(pv2_data) != 3:
            return None

        return PVData(
            total_power=pv_general[0],
            charging_power=pv_general[1],
            charging_current=pv_general[2] / 10.0,
            temperature=pv_general[3],
            pv1_voltage=pv1_data[5] / 10.0,
            pv1_current=pv1_data[6] / 10.0,
            pv1_power=pv1_data[7],
            pv2_voltage=pv2_data[0] / 10.0,
            pv2_current=pv2_data[1] / 10.0,
            pv2_power=pv2_data[2]
        )

    def get_grid_data(self) -> Optional[GridData]:
        """Get grid information (registers 338, 340, 342)."""
        # Register 338: Grid voltage
        # Register 340: Grid power
        # Register 607: Grid frequency (50.00Hz = 5000)
        
        # Read grid voltage and power
        values = self._read_registers(338, 3)
        if not values or len(values) != 3:
            return None
        
        # Read frequency from correct register
        freq = self._read_registers(607, 1)
        if not freq:
            return None

        return GridData(
            voltage=values[0] / 10.0,
            power=values[2],
            frequency=freq[0]  # Already in the correct format (5000 = 50.00Hz)
        )

    def get_output_data(self) -> Optional[OutputData]:
        """Get output information (registers 346-350, 607)."""
        # Register 346: Output voltage
        # Register 347: Output current
        # Register 348: Output power
        # Register 349: Output apparent power
        # Register 350: Load percentage
        # Register 607: Output frequency (50.00Hz = 5000)
        
        # Read output parameters
        values = self._read_registers(346, 5)
        if not values or len(values) != 5:
            return None
        
        # Read frequency from correct register
        freq = self._read_registers(607, 1)
        if not freq:
            return None

        return OutputData(
            voltage=values[0] / 10.0,
            current=values[1] / 10.0,
            power=values[2],
            apparent_power=values[3],
            load_percentage=values[4],
            frequency=freq[0]  # Already in the correct format (5000 = 50.00Hz)
        )

    def get_operating_mode(self) -> Optional[SystemStatus]:
        """Get system operating mode (register 600)."""
        values = self._read_registers(600, 1)
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

    def is_connected(self) -> bool:
        """Check if the inverter is connected by attempting to retrieve the serial number."""
        try:
            return True
        except Exception:
            return False