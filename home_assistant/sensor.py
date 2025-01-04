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

from easunpy.isolar import ISolar

_LOGGER = logging.getLogger(__name__)
SCAN_INTERVAL = timedelta(seconds=30)

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Easun Inverter sensors."""
    _LOGGER.debug("Setting up Easun Inverter sensors")
    inverter_ip = config_entry.data.get("inverter_ip")
    local_ip = config_entry.data.get("local_ip")
    
    if not inverter_ip or not local_ip:
        _LOGGER.error("Missing inverter IP or local IP in config entry")
        return
    
    isolar = ISolar(inverter_ip=inverter_ip, local_ip=local_ip)
    _LOGGER.debug(f"ISolar instance created with IP: {inverter_ip}")

    # Ensure that the ISolar instance is connected and ready
    if not isolar.is_connected():
        _LOGGER.error("Failed to connect to ISolar inverter")
        return

    entities = [
        EasunSensor(isolar, "battery_voltage", "Battery Voltage", ELECTRIC_POTENTIAL_VOLT, "battery", "voltage"),
        # Add other sensors as needed
    ]
    
    async_add_entities(entities, True)
    _LOGGER.debug("Easun Inverter sensors added")

class EasunSensor(SensorEntity):
    """Representation of an Easun Inverter sensor."""

    def __init__(self, isolar, id, name, unit, data_type, data_attr):
        """Initialize the sensor."""
        self._isolar = isolar
        self._id = id
        self._name = name
        self._unit = unit
        self._data_type = data_type
        self._data_attr = data_attr
        self._state = None
        self.update()  # Fetch initial data

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

    async def async_update(self) -> None:
        """Fetch new state data for the sensor."""
        _LOGGER.debug(f"Updating sensor {self._name}")
        try:
            if self._data_type == "battery":
                data = await self._isolar.get_battery_data()
            elif self._data_type == "pv":
                data = await self._isolar.get_pv_data()
            elif self._data_type == "grid":
                data = await self._isolar.get_grid_data()
            elif self._data_type == "output":
                data = await self._isolar.get_output_data()

            if data:
                self._state = getattr(data, self._data_attr)
                _LOGGER.debug(f"Sensor {self._name} updated with state: {self._state}")
            else:
                _LOGGER.error(f"Failed to get {self._data_type} data")
        except Exception as e:
            _LOGGER.error(f"Error updating sensor {self._name}: {str(e)}")
