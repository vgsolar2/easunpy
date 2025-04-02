from dataclasses import dataclass, field
from enum import Enum
import datetime
from typing import Dict, Optional, Callable, Any

@dataclass
class BatteryData:
    voltage: float
    current: float
    power: int
    soc: int
    temperature: int

@dataclass
class PVData:
    total_power: int
    charging_power: int
    charging_current: int
    temperature: int
    pv1_voltage: float
    pv1_current: int
    pv1_power: int
    pv2_voltage: float
    pv2_current: int
    pv2_power: int
    pv_generated_today: int
    pv_generated_total: int

@dataclass
class GridData:
    voltage: float
    power: int
    frequency: int

@dataclass
class OutputData:
    voltage: float
    current: float
    power: int
    apparent_power: int
    load_percentage: int
    frequency: int

class OperatingMode(Enum):
    SUB = 2
    SBU = 3

@dataclass
class SystemStatus:
    operating_mode: OperatingMode
    mode_name: str 
    inverter_time: datetime.datetime

@dataclass
class RegisterConfig:
    """Configuration for a single register."""
    address: int
    scale_factor: float = 1.0  # Default scale factor is 1.0 (no scaling)
    processor: Optional[Callable[[int], Any]] = None  # Optional custom processor function

@dataclass
class ModelConfig:
    """Complete configuration for an inverter model."""
    name: str
    register_map: Dict[str, RegisterConfig] = field(default_factory=dict)
    
    # Helper method to get a register address
    def get_address(self, register_name: str) -> Optional[int]:
        config = self.register_map.get(register_name)
        return config.address if config else None
    
    # Helper method to get a register's scale factor
    def get_scale_factor(self, register_name: str) -> float:
        config = self.register_map.get(register_name)
        return config.scale_factor if config else 1.0
    
    # Helper method to process a register value
    def process_value(self, register_name: str, value: int) -> Any:
        config = self.register_map.get(register_name)
        if not config:
            return value
        
        # Apply custom processor if available
        if config.processor:
            return config.processor(value)
        
        # Otherwise apply scale factor
        return value * config.scale_factor

# Define model configurations
ISOLAR_SMG_II_11K = ModelConfig(
    name="ISOLAR_SMG_II_11K",
    register_map={
        "operation_mode": RegisterConfig(201),
        "battery_voltage": RegisterConfig(277, 0.1),
        "battery_current": RegisterConfig(278, 0.1),
        "battery_power": RegisterConfig(279),
        "battery_soc": RegisterConfig(280),
        "battery_temperature": RegisterConfig(281),
        "pv_total_power": RegisterConfig(302),
        "pv_charging_power": RegisterConfig(303),
        "pv_charging_current": RegisterConfig(304, 0.1),
        "pv_temperature": RegisterConfig(305),
        "pv1_voltage": RegisterConfig(351, 0.1),
        "pv1_current": RegisterConfig(352, 0.1),
        "pv1_power": RegisterConfig(353),
        "pv2_voltage": RegisterConfig(389, 0.1),
        "pv2_current": RegisterConfig(390, 0.1),
        "pv2_power": RegisterConfig(391),
        "grid_voltage": RegisterConfig(338, 0.1),
        "grid_current": RegisterConfig(339, 0.1),
        "grid_power": RegisterConfig(340),
        "grid_frequency": RegisterConfig(607),
        "output_voltage": RegisterConfig(346, 0.1),
        "output_current": RegisterConfig(347, 0.1),
        "output_power": RegisterConfig(348),
        "output_apparent_power": RegisterConfig(349),
        "output_load_percentage": RegisterConfig(350),
        "output_frequency": RegisterConfig(607),
        "time_register_0": RegisterConfig(696, processor=int),  # Year
        "time_register_1": RegisterConfig(697, processor=int),  # Month
        "time_register_2": RegisterConfig(698, processor=int),  # Day
        "time_register_3": RegisterConfig(699, processor=int),  # Hour
        "time_register_4": RegisterConfig(700, processor=int),  # Minute
        "time_register_5": RegisterConfig(701, processor=int),  # Second
        "pv_energy_today": RegisterConfig(702, 0.01),
        "pv_energy_total": RegisterConfig(703, 0.01),
    }
)

ISOLAR_SMG_II_6K = ModelConfig(
    name="ISOLAR_SMG_II_6K",
    register_map={
        "operation_mode": RegisterConfig(201),
        "battery_voltage": RegisterConfig(215, 0.1),
        "battery_current": RegisterConfig(216, 0.1),
        "battery_power": RegisterConfig(217),
        "battery_soc": RegisterConfig(229),
        "battery_temperature": RegisterConfig(226),  # Using DCDC temperature
        "pv_total_power": RegisterConfig(223),
        "pv_charging_power": RegisterConfig(224),
        "pv_charging_current": RegisterConfig(234, 0.1),
        "pv_temperature": RegisterConfig(227),  # Using inverter temperature
        "pv1_voltage": RegisterConfig(219, 0.1),
        "pv1_current": RegisterConfig(220, 0.1),
        "pv1_power": RegisterConfig(223),
        "pv2_voltage": RegisterConfig(0),  # Not supported
        "pv2_current": RegisterConfig(0),  # Not supported
        "pv2_power": RegisterConfig(0),    # Not supported
        "grid_voltage": RegisterConfig(202, 0.1),
        "grid_current": RegisterConfig(0),  # Not available
        "grid_power": RegisterConfig(204),
        "grid_frequency": RegisterConfig(203),
        "output_voltage": RegisterConfig(210, 0.1),
        "output_current": RegisterConfig(211, 0.1),
        "output_power": RegisterConfig(213),
        "output_apparent_power": RegisterConfig(214),
        "output_load_percentage": RegisterConfig(225, 0.01),
        "output_frequency": RegisterConfig(212),
        "time_register_0": RegisterConfig(696, processor=int),  # Year
        "time_register_1": RegisterConfig(697, processor=int),  # Month
        "time_register_2": RegisterConfig(698, processor=int),  # Day
        "time_register_3": RegisterConfig(699, processor=int),  # Hour
        "time_register_4": RegisterConfig(700, processor=int),  # Minute
        "time_register_5": RegisterConfig(701, processor=int),  # Second
        "pv_energy_today": RegisterConfig(0),  # Not supported
        "pv_energy_total": RegisterConfig(0),  # Not supported
    }
)

# Dictionary of all supported models
MODEL_CONFIGS = {
    "ISOLAR_SMG_II_11K": ISOLAR_SMG_II_11K,
    "ISOLAR_SMG_II_6K": ISOLAR_SMG_II_6K,
}
