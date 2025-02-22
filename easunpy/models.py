from dataclasses import dataclass
from enum import Enum

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
    STANDBY = 0
    GRID = 1
    BATTERY = 2
    FAULT = 3
    HYBRID = 4
    CHARGING = 5
    BYPASS = 6
    UPS = 7

@dataclass
class SystemStatus:
    operating_mode: OperatingMode
    mode_name: str 