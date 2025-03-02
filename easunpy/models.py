from dataclasses import dataclass
from enum import Enum
import datetime
from typing import Dict

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
class RegisterMap:
    """Defines the register mapping for different inverter models."""
    operation_mode: int
    
    # Battery registers
    battery_voltage: int
    battery_current: int
    battery_power: int
    battery_soc: int
    battery_temperature: int
    
    # PV registers
    pv_total_power: int
    pv_charging_power: int
    pv_charging_current: int
    pv_temperature: int
    pv1_voltage: int
    pv1_current: int
    pv1_power: int
    pv2_voltage: int
    pv2_current: int
    pv2_power: int
    
    # Grid registers
    grid_voltage: int
    grid_current: int
    grid_power: int
    grid_frequency: int
    
    # Output registers
    output_voltage: int
    output_current: int
    output_power: int
    output_apparent_power: int
    output_load_percentage: int
    output_frequency: int
    
    # Time and energy registers
    time_registers: int  # Starting register for year, month, day, hour, min, sec
    pv_energy_today: int
    pv_energy_total: int

# Define known inverter models
REGISTER_MAPS = {
    "ISOLAR_SMG_II_11K": RegisterMap(
        operation_mode=201,
        battery_voltage=277,
        battery_current=278,
        battery_power=279,
        battery_soc=280,
        battery_temperature=281,
        pv_total_power=302,
        pv_charging_power=303,
        pv_charging_current=304,
        pv_temperature=305,
        pv1_voltage=351,
        pv1_current=352,
        pv1_power=353,
        pv2_voltage=389,
        pv2_current=390,
        pv2_power=391,
        grid_voltage=338,
        grid_current=339,
        grid_power=340,
        grid_frequency=607,
        output_voltage=346,
        output_current=347,
        output_power=348,
        output_apparent_power=349,
        output_load_percentage=350,
        output_frequency=607,
        time_registers=696,
        pv_energy_today=702,
        pv_energy_total=703
    ),
    "ISOLAR_SMG_II_6K": RegisterMap(
        operation_mode=201,
        battery_voltage=215,
        battery_current=216,
        battery_power=217,
        battery_soc=229,
        battery_temperature=226,  # Using DCDC temperature as equivalent
        pv_total_power=223,
        pv_charging_power=224,
        pv_charging_current=234,
        pv_temperature=227,  # Using inverter temperature as equivalent
        pv1_voltage=219,
        pv1_current=220,
        pv1_power=223,
        pv2_voltage=0,  # This model might not support PV2
        pv2_current=0,
        pv2_power=0,
        grid_voltage=202,
        grid_current=0,  # Not available in this model
        grid_power=204,
        grid_frequency=203,
        output_voltage=210,
        output_current=211,
        output_power=213,
        output_apparent_power=214,
        output_load_percentage=225,
        output_frequency=212,
        time_registers=0,  # This model might not support time registers
        pv_energy_today=0,  # This model might not support energy tracking
        pv_energy_total=0
    )
}