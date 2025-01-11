"""Support for Easun Inverter sensors."""
from datetime import timedelta
import logging
from typing import Optional

from homeassistant.components.sensor import (
    SensorEntity,
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
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from easunpy.isolar import ISolar

_LOGGER = logging.getLogger(__name__)
SCAN_INTERVAL = timedelta(seconds=30)

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

    async def async_update_data():
        """Fetch data from the inverter."""
        try:
            battery_data = isolar.get_battery_data()
            pv_data = isolar.get_pv_data()
            grid_data = isolar.get_grid_data()
            output_data = isolar.get_output_data()
            return {
                "battery": battery_data,
                "pv": pv_data,
                "grid": grid_data,
                "output": output_data,
            }
        except Exception as err:
            raise UpdateFailed(f"Error fetching data: {err}")

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name="easun_inverter",
        update_method=async_update_data,
        update_interval=SCAN_INTERVAL,
    )

    await coordinator.async_config_entry_first_refresh()

    entities = [
        EasunSensor(coordinator, "battery_voltage", "Battery Voltage", ELECTRIC_POTENTIAL_VOLT, "battery", "voltage"),
        EasunSensor(coordinator, "battery_current", "Battery Current", ELECTRIC_CURRENT_AMPERE, "battery", "current"),
        EasunSensor(coordinator, "battery_power", "Battery Power", POWER_WATT, "battery", "power"),
        EasunSensor(coordinator, "battery_soc", "Battery State of Charge", PERCENTAGE, "battery", "soc"),
        EasunSensor(coordinator, "battery_temperature", "Battery Temperature", TEMP_CELSIUS, "battery", "temperature"),
        EasunSensor(coordinator, "pv_total_power", "PV Total Power", POWER_WATT, "pv", "total_power"),
        EasunSensor(coordinator, "pv_charging_power", "PV Charging Power", POWER_WATT, "pv", "charging_power"),
        EasunSensor(coordinator, "pv_charging_current", "PV Charging Current", ELECTRIC_CURRENT_AMPERE, "pv", "charging_current"),
        EasunSensor(coordinator, "pv1_voltage", "PV1 Voltage", ELECTRIC_POTENTIAL_VOLT, "pv", "pv1_voltage"),
        EasunSensor(coordinator, "pv1_current", "PV1 Current", ELECTRIC_CURRENT_AMPERE, "pv", "pv1_current"),
        EasunSensor(coordinator, "pv1_power", "PV1 Power", POWER_WATT, "pv", "pv1_power"),
        EasunSensor(coordinator, "pv2_voltage", "PV2 Voltage", ELECTRIC_POTENTIAL_VOLT, "pv", "pv2_voltage"),
        EasunSensor(coordinator, "pv2_current", "PV2 Current", ELECTRIC_CURRENT_AMPERE, "pv", "pv2_current"),
        EasunSensor(coordinator, "pv2_power", "PV2 Power", POWER_WATT, "pv", "pv2_power"),
        EasunSensor(coordinator, "grid_voltage", "Grid Voltage", ELECTRIC_POTENTIAL_VOLT, "grid", "voltage"),
        EasunSensor(coordinator, "grid_power", "Grid Power", POWER_WATT, "grid", "power"),
        EasunSensor(coordinator, "grid_frequency", "Grid Frequency", FREQUENCY_HERTZ, "grid", "frequency"),
        EasunSensor(coordinator, "output_voltage", "Output Voltage", ELECTRIC_POTENTIAL_VOLT, "output", "voltage"),
        EasunSensor(coordinator, "output_current", "Output Current", ELECTRIC_CURRENT_AMPERE, "output", "current"),
        EasunSensor(coordinator, "output_power", "Output Power", POWER_WATT, "output", "power"),
        EasunSensor(coordinator, "output_apparent_power", "Output Apparent Power", POWER_WATT, "output", "apparent_power"),
        EasunSensor(coordinator, "output_load_percentage", "Output Load Percentage", PERCENTAGE, "output", "load_percentage"),
        EasunSensor(coordinator, "output_frequency", "Output Frequency", FREQUENCY_HERTZ, "output", "frequency"),
    ]
    
    add_entities(entities, True)
    _LOGGER.debug("Easun Inverter sensors added")

class EasunSensor(SensorEntity):
    """Representation of an Easun Inverter sensor."""

    def __init__(self, coordinator, id, name, unit, data_type, data_attr):
        """Initialize the sensor."""
        self.coordinator = coordinator
        self._id = id
        self._name = name
        self._unit = unit
        self._data_type = data_type
        self._data_attr = data_attr
        self._state = None
        self.async_on_remove(coordinator.async_add_listener(self.async_write_ha_state))

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
        data = self.coordinator.data.get(self._data_type)
        if data:
            return getattr(data, self._data_attr)
        return None

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        return self._unit

    @property
    def should_poll(self):
        """No need to poll. Coordinator notifies entity of updates."""
        return False
