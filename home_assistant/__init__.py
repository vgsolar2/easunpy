"""The Easun Inverter integration."""
from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
import logging
from homeassistant.helpers.typing import ConfigType

_LOGGER = logging.getLogger(__name__)

DOMAIN = "easun_inverter"

async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Easun Inverter component."""
    _LOGGER.debug("Setting up Easun Inverter component")
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Easun Inverter from a config entry."""
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