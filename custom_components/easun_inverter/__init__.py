"""The Easun ISolar Inverter integration."""
from __future__ import annotations

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
import homeassistant.helpers.config_validation as cv
import logging
from homeassistant.helpers.typing import ConfigType

_LOGGER = logging.getLogger(__name__)

DOMAIN = "easun_inverter"

# List of platforms to support. There should be a matching .py file for each,
# eg. switch.py and sensor.py
PLATFORMS: list[Platform] = [Platform.SENSOR]

# Use config_entry_only_config_schema since we only support config flow
CONFIG_SCHEMA = cv.config_entry_only_config_schema("easun_inverter")

async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Migrate old entry."""
    _LOGGER.debug("Migrating from version %s", config_entry.version)

    if config_entry.version == 1:
        new_data = {**config_entry.data}
        
        # Add scan_interval with default value if it doesn't exist
        if "scan_interval" not in new_data:
            new_data["scan_interval"] = 30  # Default value
            
        # Update the entry with new data and version
        hass.config_entries.async_update_entry(
            config_entry,
            data=new_data,
            version=2
        )
        _LOGGER.info("Migration to version %s successful", 2)

    return True

async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the Easun ISolar Inverter component."""
    _LOGGER.debug("Setting up Easun ISolar Inverter component")
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Easun ISolar Inverter from a config entry."""
    if entry.version == 1:
        # Migrate data from version 1 to version 2
        if not await async_migrate_entry(hass, entry):
            return False
            
    _LOGGER.debug("Setting up Easun ISolar Inverter from config entry")
    
    # Forward the setup to the sensor platform
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.debug("Unloading Easun ISolar Inverter config entry")
    
    # Unload the sensor platform
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    
    return unload_ok 