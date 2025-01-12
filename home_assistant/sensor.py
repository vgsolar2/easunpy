"""Support for Easun Inverter sensors."""
from datetime import timedelta
import logging
from typing import Optional

from homeassistant.components.sensor import (
    SensorEntity,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.const import (
    PERCENTAGE,
    POWER_WATT,
    ELECTRIC_CURRENT_AMPERE,
    ELECTRIC_POTENTIAL_VOLT,
    TEMP_CELSIUS,
    FREQUENCY_HERTZ,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.event import async_track_time_interval

from easunpy.isolar import ISolar

_LOGGER = logging.getLogger(__name__)
SCAN_INTERVAL = timedelta(seconds=60)

class DataCollector:
    """Centralized data collector for Easun Inverter."""

    def __init__(self, isolar):
        self._isolar = isolar
        self._data = {}

    def update_data(self):
        """Fetch all data from the inverter."""
        try:
            self._data['battery'] = self._isolar.get_battery_data()
            self._data['pv'] = self._isolar.get_pv_data()
            self._data['grid'] = self._isolar.get_grid_data()
            self._data['output'] = self._isolar.get_output_data()
            _LOGGER.debug("DataCollector updated all data")
        except Exception as e:
            _LOGGER.error(f"Error updating data: {str(e)}")

    def get_data(self, data_type):
        """Get data for a specific type."""
        return self._data.get(data_type)

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Easun Inverter sensors asynchronously."""
    _LOGGER.debug("Setting up Easun Inverter sensors")
    inverter_ip = config_entry.data.get("inverter_ip")
    local_ip = config_entry.data.get("local_ip")
    
    if not inverter_ip or not local_ip:
        _LOGGER.error("Missing inverter IP or local IP in config entry")
        return
    
    isolar = ISolar(inverter_ip=inverter_ip, local_ip=local_ip)
    _LOGGER.debug(f"ISolar instance created with IP: {inverter_ip}")

    data_collector = DataCollector(isolar)
    
    # Schedule periodic updates every 30 seconds
    async def update_data_collector(now):
        """Update data collector."""
        _LOGGER.debug("Updating data collector")
        data_collector.update_data()

    async_track_time_interval(hass, update_data_collector, timedelta(seconds=30))


    entities = [
        EasunSensor(data_collector, "battery_voltage", "Battery Voltage", ELECTRIC_POTENTIAL_VOLT, "battery", "voltage"),
        EasunSensor(data_collector, "battery_current", "Battery Current", ELECTRIC_CURRENT_AMPERE, "battery", "current"),
        EasunSensor(data_collector, "battery_power", "Battery Power", POWER_WATT, "battery", "power"),
        EasunSensor(data_collector, "battery_soc", "Battery State of Charge", PERCENTAGE, "battery", "soc"),
        EasunSensor(data_collector, "battery_temperature", "Battery Temperature", TEMP_CELSIUS, "battery", "temperature"),
        EasunSensor(data_collector, "pv_total_power", "PV Total Power", POWER_WATT, "pv", "total_power"),
        EasunSensor(data_collector, "pv_charging_power", "PV Charging Power", POWER_WATT, "pv", "charging_power"),
        EasunSensor(data_collector, "pv_charging_current", "PV Charging Current", ELECTRIC_CURRENT_AMPERE, "pv", "charging_current"),
        EasunSensor(data_collector, "pv1_voltage", "PV1 Voltage", ELECTRIC_POTENTIAL_VOLT, "pv", "pv1_voltage"),
        EasunSensor(data_collector, "pv1_current", "PV1 Current", ELECTRIC_CURRENT_AMPERE, "pv", "pv1_current"),
        EasunSensor(data_collector, "pv1_power", "PV1 Power", POWER_WATT, "pv", "pv1_power"),
        EasunSensor(data_collector, "pv2_voltage", "PV2 Voltage", ELECTRIC_POTENTIAL_VOLT, "pv", "pv2_voltage"),
        EasunSensor(data_collector, "pv2_current", "PV2 Current", ELECTRIC_CURRENT_AMPERE, "pv", "pv2_current"),
        EasunSensor(data_collector, "pv2_power", "PV2 Power", POWER_WATT, "pv", "pv2_power"),
        EasunSensor(data_collector, "grid_voltage", "Grid Voltage", ELECTRIC_POTENTIAL_VOLT, "grid", "voltage"),
        EasunSensor(data_collector, "grid_power", "Grid Power", POWER_WATT, "grid", "power"),
        EasunSensor(data_collector, "grid_frequency", "Grid Frequency", FREQUENCY_HERTZ, "grid", "frequency"),
        EasunSensor(data_collector, "output_voltage", "Output Voltage", ELECTRIC_POTENTIAL_VOLT, "output", "voltage"),
        EasunSensor(data_collector, "output_current", "Output Current", ELECTRIC_CURRENT_AMPERE, "output", "current"),
        EasunSensor(data_collector, "output_power", "Output Power", POWER_WATT, "output", "power"),
        EasunSensor(data_collector, "output_apparent_power", "Output Apparent Power", POWER_WATT, "output", "apparent_power"),
        EasunSensor(data_collector, "output_load_percentage", "Output Load Percentage", PERCENTAGE, "output", "load_percentage"),
        EasunSensor(data_collector, "output_frequency", "Output Frequency", FREQUENCY_HERTZ, "output", "frequency"),
    ]
    
    add_entities(entities, True)
    _LOGGER.debug("Easun Inverter sensors added")

class EasunSensor(SensorEntity):
    """Representation of an Easun Inverter sensor."""

    def __init__(self, data_collector, id, name, unit, data_type, data_attr):
        """Initialize the sensor."""
        self._data_collector = data_collector
        self._id = id
        self._name = name
        self._unit = unit
        self._data_type = data_type
        self._data_attr = data_attr
        self._state = None

    def update(self) -> None:
        """Fetch new state data for the sensor."""
        _LOGGER.debug(f"Updating sensor {self._name}")
        data = self._data_collector.get_data(self._data_type)
        if data:
            self._state = getattr(data, self._data_attr)
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