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
    UnitOfApparentPower,
    UnitOfEnergy,
    PERCENTAGE,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.event import async_track_time_interval

from . import DOMAIN  # Import DOMAIN from __init__.py
from easunpy.async_isolar import AsyncISolar

_LOGGER = logging.getLogger(__name__)


class DataCollector:
    """Centralized data collector for Easun Inverter."""

    def __init__(self, isolar):
        self._isolar = isolar
        self._data = {}
        self._lock = asyncio.Lock()
        self._consecutive_failures = 0
        self._max_consecutive_failures = 5
        self._last_update_start = None
        self._last_successful_update = None
        self._update_timeout = 30
        self._sensors = []
        _LOGGER.info(f"DataCollector initialized with model: {self._isolar.model}")

    def register_sensor(self, sensor):
        """Register a sensor to be updated when data is refreshed."""
        self._sensors.append(sensor)
        _LOGGER.debug(f"Registered sensor: {sensor.name}")

    async def is_update_stuck(self) -> bool:
        """Check if the update process is stuck."""
        if self._last_update_start is None:
            return False
        
        time_since_update = (datetime.now() - self._last_update_start).total_seconds()
        return time_since_update > self._update_timeout

    async def update_data(self):
        """Fetch all data from the inverter asynchronously using bulk request."""
        if not await self._lock.acquire():
            _LOGGER.warning("Could not acquire lock for update")
            return

        try:
            # Create a task for the actual data collection
            update_task = asyncio.create_task(self._do_update())
            
            # Wait for the task with timeout
            try:
                await asyncio.wait_for(update_task, timeout=self._update_timeout)
                # Update all registered sensors after successful data fetch
                for sensor in self._sensors:
                    sensor.update_from_collector()
                _LOGGER.debug("Updated all registered sensors")
            except asyncio.TimeoutError:
                _LOGGER.error("Update timed out, cancelling task")
                update_task.cancel()
                try:
                    await update_task
                except asyncio.CancelledError:
                    _LOGGER.debug("Update task cancelled successfully")
                raise Exception("Update timed out")
            
        finally:
            self._lock.release()

    async def _do_update(self):
        """Actual update implementation."""
        try:
            _LOGGER.debug(f"Starting data update using model: {self._isolar.model}")
            battery, pv, grid, output, status = await self._isolar.get_all_data()
            if all(x is None for x in (battery, pv, grid, output, status)):
                raise Exception("No data received from inverter")
            
            self._data['battery'] = battery
            self._data['pv'] = pv
            self._data['grid'] = grid
            self._data['output'] = output
            self._data['system'] = status
            self._consecutive_failures = 0
            self._last_successful_update = datetime.now()  # Update timestamp on success
            _LOGGER.debug("DataCollector updated all data in bulk")
        except Exception as e:
            self._consecutive_failures += 1
            delay = min(30, 2 ** self._consecutive_failures)  # Exponential backoff, max 5 minutes
            _LOGGER.error(f"Error updating data in bulk (attempt {self._consecutive_failures}): {str(e)}")
            _LOGGER.warning(f"Will retry with increased delay of {delay} seconds")
            await asyncio.sleep(delay)
            raise

    def get_data(self, data_type):
        """Get data for a specific type."""
        return self._data.get(data_type)

    @property
    def last_update(self):
        """Get the timestamp of the last successful update."""
        return self._last_successful_update

    async def update_model(self, model: str):
        """Update the inverter model."""
        _LOGGER.info(f"Updating inverter model to: {model}")
        self._isolar.update_model(model)

class EasunSensor(SensorEntity):
    """Representation of an Easun Inverter sensor."""

    def __init__(self, data_collector, id, name, unit, data_type, data_attr, value_converter=None, entry_id=None):
        """Initialize the sensor."""
        self._data_collector = data_collector
        self._id = id
        self._name = name
        self._unit = unit
        self._data_type = data_type
        self._data_attr = data_attr
        self._state = None
        self._value_converter = value_converter
        self._available = True
        self._force_update = True  # Force update even if value hasn't changed
        self._entry_id = entry_id
        # Register this sensor with the data collector
        self._data_collector.register_sensor(self)

    def update_from_collector(self) -> None:
        """Update sensor state from data collector."""
        try:
            data = self._data_collector.get_data(self._data_type)
            if data:
                if self._data_attr == "inverter_time":
                    value = data.inverter_time.isoformat() if data.inverter_time else None
                else:
                    value = getattr(data, self._data_attr)
                if self._value_converter is not None:
                    value = self._value_converter(value)
                self._state = value
                self._available = True
                _LOGGER.debug(f"Sensor {self._name} updated with state: {self._state}")
            else:
                _LOGGER.warning(f"No {self._data_type} data available")
                self._available = False
        except Exception as e:
            _LOGGER.error(f"Error updating sensor {self._name}: {str(e)}")
            self._available = False
        
        # Trigger state update in Home Assistant
        self.async_write_ha_state()

    def update(self) -> None:
        """No-op update method as sensors are updated by the data collector."""
        pass

    @property
    def force_update(self) -> bool:
        """Return True if state updates should be forced.
        If True, a state change will be triggered anytime the state property is updated
        even if the value hasn't changed.
        """
        return self._force_update

    @property
    def extra_state_attributes(self):
        """Return additional sensor state attributes."""
        return {
            'data_type': self._data_type,
            'data_attribute': self._data_attr,
        }

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self._available

    @property
    def should_poll(self) -> bool:
        """Return False as entity should not be polled individually."""
        return False

    @property
    def name(self):
        """Return the name of the sensor."""
        if self._entry_id:
            return f"Easun {self._name} ({self._entry_id[:8]})"
        return f"Easun {self._name}"

    @property
    def unique_id(self):
        """Return a unique ID."""
        if self._entry_id:
            return f"easun_inverter_{self._entry_id}_{self._id}"
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
    model = config_entry.data.get("model")
    
    _LOGGER.info(f"Setting up sensors with model: {model}")
    
    if not inverter_ip or not local_ip:
        _LOGGER.error("Missing inverter IP or local IP in config entry")
        return
    
    isolar = AsyncISolar(inverter_ip=inverter_ip, local_ip=local_ip, model=model)
    data_collector = DataCollector(isolar)
    
    # Store the coordinator in the domain data under this entry's ID
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN].setdefault(config_entry.entry_id, {})
    hass.data[DOMAIN][config_entry.entry_id]["coordinator"] = data_collector
    
    # Create entities
    def frequency_converter(value):
        """Convert frequency from centihz to hz."""
        return value / 100 if value is not None else None

    entities = [
        EasunSensor(data_collector, "battery_voltage", "Battery Voltage", UnitOfElectricPotential.VOLT, "battery", "voltage", None, config_entry.entry_id),
        EasunSensor(data_collector, "battery_current", "Battery Current", UnitOfElectricCurrent.AMPERE, "battery", "current", None, config_entry.entry_id),
        EasunSensor(data_collector, "battery_power", "Battery Power", UnitOfPower.WATT, "battery", "power", None, config_entry.entry_id),
        EasunSensor(data_collector, "battery_soc", "Battery State of Charge", PERCENTAGE, "battery", "soc", None, config_entry.entry_id),
        EasunSensor(data_collector, "battery_temperature", "Battery Temperature", UnitOfTemperature.CELSIUS, "battery", "temperature", None, config_entry.entry_id),
        EasunSensor(data_collector, "pv_total_power", "PV Total Power", UnitOfPower.WATT, "pv", "total_power", None, config_entry.entry_id),
        EasunSensor(data_collector, "pv_charging_power", "PV Charging Power", UnitOfPower.WATT, "pv", "charging_power", None, config_entry.entry_id),
        EasunSensor(data_collector, "pv_charging_current", "PV Charging Current", UnitOfElectricCurrent.AMPERE, "pv", "charging_current", None, config_entry.entry_id),
        EasunSensor(data_collector, "pv1_voltage", "PV1 Voltage", UnitOfElectricPotential.VOLT, "pv", "pv1_voltage", None, config_entry.entry_id),
        EasunSensor(data_collector, "pv1_current", "PV1 Current", UnitOfElectricCurrent.AMPERE, "pv", "pv1_current", None, config_entry.entry_id),
        EasunSensor(data_collector, "pv1_power", "PV1 Power", UnitOfPower.WATT, "pv", "pv1_power", None, config_entry.entry_id),
        EasunSensor(data_collector, "pv2_voltage", "PV2 Voltage", UnitOfElectricPotential.VOLT, "pv", "pv2_voltage", None, config_entry.entry_id),
        EasunSensor(data_collector, "pv2_current", "PV2 Current", UnitOfElectricCurrent.AMPERE, "pv", "pv2_current", None, config_entry.entry_id),
        EasunSensor(data_collector, "pv2_power", "PV2 Power", UnitOfPower.WATT, "pv", "pv2_power", None, config_entry.entry_id),
        EasunSensor(data_collector, "pv_generated_today", "PV Generated Today", UnitOfEnergy.KILO_WATT_HOUR, "pv", "pv_generated_today", None, config_entry.entry_id),
        EasunSensor(data_collector, "pv_generated_total", "PV Generated Total", UnitOfEnergy.KILO_WATT_HOUR, "pv", "pv_generated_total", None, config_entry.entry_id),
        EasunSensor(data_collector, "grid_voltage", "Grid Voltage", UnitOfElectricPotential.VOLT, "grid", "voltage", None, config_entry.entry_id),
        EasunSensor(data_collector, "grid_power", "Grid Power", UnitOfPower.WATT, "grid", "power", None, config_entry.entry_id),
        EasunSensor(data_collector, "grid_frequency", "Grid Frequency", UnitOfFrequency.HERTZ, "grid", "frequency", frequency_converter, config_entry.entry_id),
        EasunSensor(data_collector, "output_voltage", "Output Voltage", UnitOfElectricPotential.VOLT, "output", "voltage", None, config_entry.entry_id),
        EasunSensor(data_collector, "output_current", "Output Current", UnitOfElectricCurrent.AMPERE, "output", "current", None, config_entry.entry_id),
        EasunSensor(data_collector, "output_power", "Output Power", UnitOfPower.WATT, "output", "power", None, config_entry.entry_id),
        EasunSensor(data_collector, "output_apparent_power", "Output Apparent Power", UnitOfApparentPower.VOLT_AMPERE, "output", "apparent_power", None, config_entry.entry_id),
        EasunSensor(data_collector, "output_load_percentage", "Output Load Percentage", PERCENTAGE, "output", "load_percentage", None, config_entry.entry_id),
        EasunSensor(data_collector, "output_frequency", "Output Frequency", UnitOfFrequency.HERTZ, "output", "frequency", frequency_converter, config_entry.entry_id),
        EasunSensor(data_collector, "operating_mode", "Operating Mode", None, "system", "mode_name", None, config_entry.entry_id),
        EasunSensor(data_collector, "inverter_time", "Inverter Time", None, "system", "inverter_time", None, config_entry.entry_id),
    ]
    
    add_entities(entities, False)  # Set update_before_add to False since we're managing updates separately
    
    # Schedule periodic updates
    is_updating = False

    async def update_data_collector(now):
        """Update data collector."""
        nonlocal is_updating
        
        if is_updating:
            if await data_collector.is_update_stuck():
                _LOGGER.warning("Previous update appears to be stuck, forcing a new update")
                is_updating = False
            else:
                _LOGGER.debug("Update already in progress, skipping this cycle")
                return

        _LOGGER.debug("Starting data collector update")
        is_updating = True
        data_collector._last_update_start = datetime.now()
        
        try:
            # Use wait_for here as well for extra safety
            await asyncio.wait_for(
                data_collector.update_data(),
                timeout=data_collector._update_timeout + 5  # Add a small buffer
            )
        except asyncio.TimeoutError:
            _LOGGER.error("Update operation timed out at scheduler level")
        except Exception as e:
            _LOGGER.error(f"Error updating data collector: {str(e)}")
        finally:
            is_updating = False
            data_collector._last_update_start = None
            _LOGGER.debug("Data collector update finished")

    # Store the update function in the domain data
    hass.data[DOMAIN][config_entry.entry_id]["update_function"] = update_data_collector
    hass.data[DOMAIN][config_entry.entry_id]["scan_interval"] = scan_interval
    
    # Create the update listener and store it in the domain data
    update_listener = async_track_time_interval(
        hass, 
        update_data_collector, 
        timedelta(seconds=scan_interval)
    )
    hass.data[DOMAIN][config_entry.entry_id]["update_listener"] = update_listener
    
    # Register config entry unload function to clean up resources
    config_entry.async_on_unload(
        lambda: hass.data[DOMAIN][config_entry.entry_id]["update_listener"]()
    )
    
    _LOGGER.debug("Easun Inverter sensors added")