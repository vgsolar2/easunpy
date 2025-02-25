"""The Easun Inverter integration."""
from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
import logging
from homeassistant.helpers.typing import ConfigType

_LOGGER = logging.getLogger(__name__)

DOMAIN = "easun_inverter"

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

async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Easun Inverter component."""
    _LOGGER.debug("Setting up Easun Inverter component")
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Easun Inverter from a config entry."""
    if entry.version == 1:
        # Migrate data from version 1 to version 2
        if not await async_migrate_entry(hass, entry):
            return False
            
    _LOGGER.debug("Setting up Easun Inverter from config entry")
    
    # Forward the setup to the sensor platform
    await hass.config_entries.async_forward_entry_setup(entry, "sensor")
    
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.debug("Unloading Easun Inverter config entry")
    
    # Unload the sensor platform
    unload_ok = await hass.config_entries.async_forward_entry_unload(entry, "sensor")
    
    return unload_ok 