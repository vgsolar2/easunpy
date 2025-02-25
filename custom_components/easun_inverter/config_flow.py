"""Config flow for Easun Inverter integration."""
from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult
from homeassistant.core import callback

from . import DOMAIN
from easunpy.discover import discover_device
from easunpy.utils import get_local_ip

DEFAULT_SCAN_INTERVAL = 30  # Default to 30 seconds

class EasunInverterConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Easun Inverter."""

    VERSION = 3  # Increment version to trigger migration

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return OptionsFlowHandler(config_entry)

    async def async_step_user(
        self, user_input: dict[str, any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            # Validate the input data
            inverter_ip = user_input.get("inverter_ip")
            local_ip = user_input.get("local_ip")
            scan_interval = user_input.get("scan_interval", DEFAULT_SCAN_INTERVAL)
            
            if not inverter_ip or not local_ip:
                errors["base"] = "missing_ip"
            else:
                return self.async_create_entry(title="Easun Inverter", data=user_input)

        # Attempt to discover the IPs
        inverter_ip = discover_device()
        local_ip = get_local_ip()

        if not inverter_ip or not local_ip:
            errors["base"] = "discovery_failed"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required("inverter_ip", default=inverter_ip): str,
                vol.Required("local_ip", default=local_ip): str,
                vol.Optional("scan_interval", default=DEFAULT_SCAN_INTERVAL): vol.All(
                    vol.Coerce(int),
                    vol.Range(min=1, max=3600)
                ),
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
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
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