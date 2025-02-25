from dataclasses import dataclass
from enum import Enum
import datetime

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