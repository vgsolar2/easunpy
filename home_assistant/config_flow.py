"""Config flow for Easun Inverter integration."""
from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult

from . import DOMAIN

class EasunInverterConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Easun Inverter."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors = {}
        if user_input is not None:
            # Validate the input data
            inverter_ip = user_input.get("inverter_ip")
            local_ip = user_input.get("local_ip")
            
            if not inverter_ip or not local_ip:
                errors["base"] = "missing_ip"
            else:
                return self.async_create_entry(title="Easun Inverter", data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required("inverter_ip"): str,
                vol.Required("local_ip"): str,
            }),
            errors=errors
        ) 