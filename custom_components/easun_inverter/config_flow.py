"""Config flow for Easun Inverter integration."""
from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult
from homeassistant.core import callback
import logging
from homeassistant.helpers.event import async_track_time_interval
from datetime import timedelta

from . import DOMAIN
from easunpy.discover import discover_device
from easunpy.utils import get_local_ip
from easunpy.models import MODEL_CONFIGS

DEFAULT_SCAN_INTERVAL = 30  # Default to 30 seconds
_LOGGER = logging.getLogger(__name__)

class EasunInverterConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Easun Inverter."""

    VERSION = 4

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return OptionsFlowHandler(config_entry)

    async def async_step_user(self, user_input=None):
        """Handle a flow initialized by the user."""
        errors = {}

        if user_input is not None:
            # Validate the input data
            inverter_ip = user_input.get("inverter_ip")
            local_ip = user_input.get("local_ip")
            scan_interval = user_input.get("scan_interval", DEFAULT_SCAN_INTERVAL)
            model = user_input.get("model")  # Get model from input
            
            _LOGGER.debug(f"Processing user input with model: {model}")
            
            if not inverter_ip or not local_ip:
                errors["base"] = "missing_ip"
            else:
                entry_data = {
                    "inverter_ip": inverter_ip,
                    "local_ip": local_ip,
                    "scan_interval": scan_interval,
                    "model": model,
                }
                _LOGGER.debug(f"Creating entry with data: {entry_data}")
                return self.async_create_entry(
                    title=f"Easun Inverter ({inverter_ip})",
                    data=entry_data,
                )

        # Attempt to discover the IPs
        inverter_ip = discover_device()
        local_ip = get_local_ip()

        if not inverter_ip or not local_ip:
            errors["base"] = "discovery_failed"

        # Add model selection to the form
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required("inverter_ip", default=inverter_ip): str,
                vol.Required("local_ip", default=local_ip): str,
                vol.Optional("scan_interval", default=DEFAULT_SCAN_INTERVAL): vol.All(
                    vol.Coerce(int),
                    vol.Range(min=1, max=3600)
                ),
                vol.Required("model", default="ISOLAR_SMG_II_11K"): vol.In(list(MODEL_CONFIGS.keys())),
            }),
            errors=errors
        )

class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options."""

    def __init__(self, config_entry):
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        if user_input is not None:
            _LOGGER.debug(f"Updating config entry with new input: {user_input}")
            
            # Get the entry data
            entry_data = self.hass.data[DOMAIN].get(self.config_entry.entry_id, {})
            coordinator = entry_data.get("coordinator")
            
            # Check if coordinator exists
            if coordinator:
                # Check if model has changed
                if user_input["model"] != self.config_entry.data.get("model"):
                    await coordinator.update_model(user_input["model"])
                
                # Update scan interval without reloading
                if "update_listener" in entry_data:
                    entry_data["update_listener"]()
                    entry_data.pop("update_listener")
                
                # Set up new scan interval
                new_interval = user_input["scan_interval"]
                
                # Create new update listener with new interval
                update_listener = async_track_time_interval(
                    self.hass,
                    entry_data.get("update_function"),
                    timedelta(seconds=new_interval)
                )
                entry_data["update_listener"] = update_listener
                entry_data["scan_interval"] = new_interval
                
                _LOGGER.debug(f"Updated scan interval to {new_interval} seconds")
            
            # Update the config entry with new data
            self.hass.config_entries.async_update_entry(
                self.config_entry,
                data={
                    **self.config_entry.data,
                    "inverter_ip": user_input["inverter_ip"],
                    "local_ip": user_input["local_ip"],
                    "model": user_input["model"],
                },
                options={
                    "scan_interval": user_input["scan_interval"],
                }
            )
            _LOGGER.debug(f"Updated config entry data: {self.config_entry.data}")
            
            # Only reload if IP or model changed (scan interval handled separately)
            if (user_input["inverter_ip"] != self.config_entry.data.get("inverter_ip") or
                user_input["local_ip"] != self.config_entry.data.get("local_ip")):
                _LOGGER.debug("IP address changed, reloading integration")
                self.hass.async_create_task(
                    self.hass.config_entries.async_reload(self.config_entry.entry_id)
                )
            
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Required(
                    "inverter_ip",
                    default=self.config_entry.data.get("inverter_ip")
                ): str,
                vol.Required(
                    "local_ip",
                    default=self.config_entry.data.get("local_ip")
                ): str,
                vol.Required(
                    "model",
                    default=self.config_entry.data.get("model", "ISOLAR_SMG_II_11K")
                ): vol.In(list(MODEL_CONFIGS.keys())),
                vol.Optional(
                    "scan_interval",
                    default=self.config_entry.options.get(
                        "scan_interval", 
                        self.config_entry.data.get("scan_interval", DEFAULT_SCAN_INTERVAL)
                    )
                ): vol.All(
                    vol.Coerce(int),
                    vol.Range(min=1, max=3600)
                ),
            })
        ) 