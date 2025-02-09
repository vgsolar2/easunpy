"""Support for Easun Inverter sensors."""
from datetime import datetime, timedelta
import logging
import asyncio

from homeassistant.components.sensor import SensorEntity
from homeassistant.const import (
    UnitOfPower,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfTemperature,
    UnitOfFrequency,
    UnitOfEnergy,
    PERCENTAGE,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.event import async_track_time_interval

from easunpy.async_isolar import AsyncISolar

_LOGGER = logging.getLogger(__name__)

class AccumulatorSensor(SensorEntity):
    """Represents an accumulating energy sensor that integrates power over time."""

    def __init__(self, data_collector, id, name, unit, data_type, data_attr, power_filter=None):
        """Initialize the accumulator sensor."""
        self._data_collector = data_collector
        self._id = id
        self._name = name
        self._unit = unit
        self._state = 0.0  # Total energy accumulated in kWh
        self._data_type = data_type
        self._data_attr = data_attr
        self._last_update = datetime.now()
        self._power_filter = power_filter  # Function to filter power values

    async def async_update(self) -> None:
        """Integrate power over time to compute accumulated energy (kWh)."""
        now = datetime.now()
        elapsed_hours = (now - self._last_update).total_seconds() / 3600
        self._last_update = now

        data = self._data_collector.get_data(self._data_type)
        if data:
            power = getattr(data, self._data_attr)
            _LOGGER.error(f"{self._name} from {self._data_type}.{self._data_attr} is {power}W")
            
            # Apply power filter if one is set
            if self._power_filter is not None:
                power = self._power_filter(power)
            
            self._state += (power * elapsed_hours) / 1000  # Convert W to kWh
            _LOGGER.error(f"{self._name}: Accumulated {self._state} kWh from {power}W")

    @property
    def name(self):
        """Return the name of the sensor."""
        return f"Easun {self._name}"

    @property
    def unique_id(self):
        """Return a unique ID."""
        return f"easun_inverter_{self._id}"

    @property
    def state(self):
        """Return the state of the sensor."""
        return round(self._state, 3)  # Keep 3 decimal places

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        return self._unit

    def reset(self):
        """Reset the accumulator at midnight."""
        _LOGGER.info(f"Resetting {self._name} accumulator to 0 kWh")
        self._state = 0.0

class DataCollector:
    """Centralized data collector for Easun Inverter."""

    def __init__(self, isolar):
        self._isolar = isolar
        self._data = {}
        self._lock = asyncio.Lock()

    async def update_data(self):
        """Fetch all data from the inverter asynchronously using bulk request."""
        async with self._lock:
            try:
                battery, pv, grid, output, status = await self._isolar.get_all_data()
                self._data['battery'] = battery
                self._data['pv'] = pv
                self._data['grid'] = grid
                self._data['output'] = output
                self._data['system'] = status
                _LOGGER.debug("DataCollector updated all data in bulk")
            except Exception as e:
                _LOGGER.error(f"Error updating data in bulk: {str(e)}")

    def get_data(self, data_type):
        """Get data for a specific type."""
        return self._data.get(data_type)

class EasunSensor(SensorEntity):
    """Representation of an Easun Inverter sensor."""

    def __init__(self, data_collector, id, name, unit, data_type, data_attr, value_converter=None):
        """Initialize the sensor."""
        self._data_collector = data_collector
        self._id = id
        self._name = name
        self._unit = unit
        self._data_type = data_type
        self._data_attr = data_attr
        self._state = None
        self._value_converter = value_converter

    def update(self) -> None:
        """Fetch new state data for the sensor."""
        data = self._data_collector.get_data(self._data_type)
        if data:
            value = getattr(data, self._data_attr)
            if self._value_converter is not None:
                value = self._value_converter(value)
            self._state = value
            _LOGGER.debug(f"Sensor {self._name} updated with state: {self._state}")
        else:
            _LOGGER.error(f"Failed to get {self._data_type} data")

    @property
    def name(self):
        """Return the name of the sensor."""
        return f"Easun {self._name}"

    @property
    def unique_id(self):
        """Return a unique ID."""
        return f"easun_inverter_{self._id}"

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        return self._unit

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Easun Inverter sensors."""
    _LOGGER.debug("Setting up Easun Inverter sensors")
    
    scan_interval = config_entry.options.get(
        "scan_interval",
        config_entry.data.get("scan_interval", 30)
    )
    
    inverter_ip = config_entry.data.get("inverter_ip")
    local_ip = config_entry.data.get("local_ip")
    
    if not inverter_ip or not local_ip:
        _LOGGER.error("Missing inverter IP or local IP in config entry")
        return
    
    isolar = AsyncISolar(inverter_ip=inverter_ip, local_ip=local_ip)
    data_collector = DataCollector(isolar)
    
    # Schedule periodic updates
    is_updating = False

    async def update_data_collector(now):
        """Update data collector."""
        nonlocal is_updating
        if is_updating:
            _LOGGER.debug("Update already in progress, skipping this cycle")
            return

        _LOGGER.debug("Starting data collector update")
        is_updating = True
        try:
            await data_collector.update_data()
        finally:
            is_updating = False
            _LOGGER.debug("Data collector update finished")

    async_track_time_interval(
        hass, 
        update_data_collector, 
        timedelta(seconds=scan_interval)
    )

    def charging_only(power):
        """Filter to only include positive power values (charging)."""
        return power if power > 0 else 0

    def discharging_only(power):
        """Filter to only include negative power values (discharging)."""
        return abs(power) if power < 0 else 0

    def frequency_converter(value):
        """Convert frequency from centihz to hz."""
        return value / 100 if value is not None else None

    entities = [
        EasunSensor(data_collector, "battery_voltage", "Battery Voltage", UnitOfElectricPotential.VOLT, "battery", "voltage"),
        EasunSensor(data_collector, "battery_current", "Battery Current", UnitOfElectricCurrent.AMPERE, "battery", "current"),
        EasunSensor(data_collector, "battery_power", "Battery Power", UnitOfPower.WATT, "battery", "power"),
        EasunSensor(data_collector, "battery_soc", "Battery State of Charge", PERCENTAGE, "battery", "soc"),
        EasunSensor(data_collector, "battery_temperature", "Battery Temperature", UnitOfTemperature.CELSIUS, "battery", "temperature"),
        EasunSensor(data_collector, "pv_total_power", "PV Total Power", UnitOfPower.WATT, "pv", "total_power"),
        EasunSensor(data_collector, "pv_charging_power", "PV Charging Power", UnitOfPower.WATT, "pv", "charging_power"),
        EasunSensor(data_collector, "pv_charging_current", "PV Charging Current", UnitOfElectricCurrent.AMPERE, "pv", "charging_current"),
        EasunSensor(data_collector, "pv1_voltage", "PV1 Voltage", UnitOfElectricPotential.VOLT, "pv", "pv1_voltage"),
        EasunSensor(data_collector, "pv1_current", "PV1 Current", UnitOfElectricCurrent.AMPERE, "pv", "pv1_current"),
        EasunSensor(data_collector, "pv1_power", "PV1 Power", UnitOfPower.WATT, "pv", "pv1_power"),
        EasunSensor(data_collector, "pv2_voltage", "PV2 Voltage", UnitOfElectricPotential.VOLT, "pv", "pv2_voltage"),
        EasunSensor(data_collector, "pv2_current", "PV2 Current", UnitOfElectricCurrent.AMPERE, "pv", "pv2_current"),
        EasunSensor(data_collector, "pv2_power", "PV2 Power", UnitOfPower.WATT, "pv", "pv2_power"),
        EasunSensor(data_collector, "grid_voltage", "Grid Voltage", UnitOfElectricPotential.VOLT, "grid", "voltage"),
        EasunSensor(data_collector, "grid_power", "Grid Power", UnitOfPower.WATT, "grid", "power"),
        EasunSensor(data_collector, "grid_frequency", "Grid Frequency", UnitOfFrequency.HERTZ, "grid", "frequency", frequency_converter),
        EasunSensor(data_collector, "output_voltage", "Output Voltage", UnitOfElectricPotential.VOLT, "output", "voltage"),
        EasunSensor(data_collector, "output_current", "Output Current", UnitOfElectricCurrent.AMPERE, "output", "current"),
        EasunSensor(data_collector, "output_power", "Output Power", UnitOfPower.WATT, "output", "power"),
        EasunSensor(data_collector, "output_apparent_power", "Output Apparent Power", UnitOfPower.WATT, "output", "apparent_power"),
        EasunSensor(data_collector, "output_load_percentage", "Output Load Percentage", PERCENTAGE, "output", "load_percentage"),
        EasunSensor(data_collector, "output_frequency", "Output Frequency", UnitOfFrequency.HERTZ, "output", "frequency", frequency_converter),
        # EasunSensor(data_collector, "operating_mode", "Operating Mode", None, "system", "mode_name"),
    ]
    
    # Add accumulators for daily energy tracking
    accumulator_sensors = [
        AccumulatorSensor(data_collector, "pv_energy_accumulator", "PV Energy Accumulator", 
                         UnitOfPower.KILO_WATT, "pv", "total_power"),
        AccumulatorSensor(data_collector, "battery_charge_energy_accumulator", 
                         "Battery Charge Energy Accumulator", UnitOfPower.KILO_WATT, 
                         "battery", "power", charging_only),
        AccumulatorSensor(data_collector, "battery_discharge_energy_accumulator", 
                         "Battery Discharge Energy Accumulator", UnitOfPower.KILO_WATT, 
                         "battery", "power", discharging_only),
        AccumulatorSensor(data_collector, "grid_energy_accumulator", "Grid Energy Accumulator", 
                         UnitOfPower.KILO_WATT, "grid", "power"),
    ]
    
    entities.extend(accumulator_sensors)    
    add_entities(entities, True)
    
    # Schedule daily reset at midnight
    async def reset_accumulators(now):
        """Reset all accumulator sensors at midnight."""
        for sensor in accumulator_sensors:
            sensor.reset()

    midnight = datetime.combine(datetime.today() + timedelta(days=1), datetime.min.time())
    time_until_midnight = (midnight - datetime.now()).total_seconds()

    async_track_time_interval(hass, reset_accumulators, timedelta(seconds=time_until_midnight))
    _LOGGER.debug("Easun Inverter sensors added")