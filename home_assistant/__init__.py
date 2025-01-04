"""The Easun Inverter integration."""
from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
import logging

_LOGGER = logging.getLogger(__name__)

DOMAIN = "easun_inverter"

async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the Easun Inverter component."""
    hass.data.setdefault(DOMAIN, {})
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Easun Inverter from a config entry."""
    _LOGGER.debug("Setting up Easun Inverter from config entry")
    
    # Forward the setup to the sensor platform
    hass.async_create_task(
        hass.config_entries.async_forward_entry_setup(entry, "sensor")
    )
    
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, ["sensor"]) 