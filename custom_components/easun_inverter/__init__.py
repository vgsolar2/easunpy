"""The Easun ISolar Inverter integration."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
import homeassistant.helpers.config_validation as cv
import logging
from easunpy.modbusclient import create_request 
from datetime import datetime
import json
import os
from aiofiles import open as async_open
from aiofiles.os import makedirs
import asyncio
from easunpy.async_isolar import AsyncISolar
from easunpy.utils import get_local_ip

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
    inverter_ip = entry.data["inverter_ip"]
    model = entry.data.get("model", "ISOLAR_SMG_II_11K")  # Default to original model if not specified
    
    # Get the local IP address
    local_ip = get_local_ip()
    
    # Create API instance
    api = AsyncISolar(inverter_ip=inverter_ip, local_ip=local_ip, model=model)
    
    if entry.version == 1:
        if not await async_migrate_entry(hass, entry):
            return False
            
    _LOGGER.debug("Setting up Easun ISolar Inverter from config entry")
    
    # Initialize domain data
    hass.data.setdefault(DOMAIN, {})
    
    async def handle_register_scan(call: ServiceCall) -> None:
        """Handle the register scan service."""
        start = call.data.get("start_register", 0)
        count = call.data.get("register_count", 5)
        
        # Get the coordinator from the entry we stored in sensor.py
        entry_data = hass.data[DOMAIN].get(entry.entry_id)
        if not entry_data or "coordinator" not in entry_data:
            _LOGGER.error("No coordinator found. Is the integration set up?")
            return
            
        coordinator = entry_data["coordinator"]
        inverter = coordinator._isolar
        
        _LOGGER.debug(f"Starting register scan from {start} for {count} registers")
        
        # Create register groups in chunks of 10
        register_groups = []
        for chunk_start in range(start, start + count, 10):
            chunk_size = min(10, start + count - chunk_start)  # Handle last chunk
            register_groups.append((chunk_start, chunk_size))
        
        # Read all registers in bulk
        results = []
        try:
            responses = await inverter._read_registers_bulk(register_groups, "Int")
            if responses:
                for group_idx, response in enumerate(responses):
                    if response:  # Check if we got values for this group
                        chunk_start = register_groups[group_idx][0]
                        for i, value in enumerate(response):
                            if value != 0:  # Only store non-zero values
                                reg = chunk_start + i
                                results.append({
                                    "register": reg,
                                    "hex": f"0x{reg:04x}",
                                    "value": value,
                                    "raw": f"Register {reg}: {value}"
                                })
        except Exception as e:
            _LOGGER.error(f"Error reading registers: {e}")
        
        # Store results in hass.data for the sensor
        scan_data = {
            "timestamp": datetime.now().isoformat(),
            "results": results,
            "start_register": start,
            "count": count
        }
        hass.data[DOMAIN]["last_scan"] = scan_data
        
        # Save to www folder
        www_dir = hass.config.path("www")
        try:
            if not os.path.exists(www_dir):
                await makedirs(www_dir)
            
            filename = os.path.join(www_dir, "easun_register_scan.json")
            async with async_open(filename, 'w') as f:
                await f.write(json.dumps(scan_data, indent=2))
            _LOGGER.info(f"Scan complete. Found {len(results)} registers with values")
        except Exception as e:
            _LOGGER.error(f"Error saving scan results: {e}")

    async def handle_device_scan(call: ServiceCall) -> None:
        """Handle the device ID scan service."""
        start_id = call.data.get("start_id", 0)
        end_id = call.data.get("end_id", 5)
        
        entry_data = hass.data[DOMAIN].get(entry.entry_id)
        if not entry_data or "coordinator" not in entry_data:
            _LOGGER.error("No coordinator found. Is the integration set up?")
            return
            
        coordinator = entry_data["coordinator"]
        inverter = coordinator._isolar
        
        _LOGGER.debug(f"Starting device scan from ID {start_id} to {end_id}")
        
        results = []
        
        for device_id in range(start_id, end_id + 1):
            try:
                # Create request
                request = [create_request(
                    inverter._get_next_transaction_id(),
                    0x0001, device_id, 0x03,
                    0x0115,
                    1
                )]
                
                # Send request and get raw response
                responses = await inverter.client.send_bulk(request)
                _LOGGER.debug(f"Responses: {responses}")
                response_hex = responses[0] if responses else None
                
                result = {
                    "device_id": device_id,
                    "hex": f"0x{device_id:02x}",
                    "request": request,
                    "response": response_hex,
                }
        
                ERROR_RESPONSE = "00010002ff04"  # Protocol error response
                
                if response_hex: 
                    if response_hex[4:] == ERROR_RESPONSE:
                        result["status"] = "Protocol Error"
                        _LOGGER.debug(f"Device 0x{device_id:02x} gave protocol error: {response_hex}")
                    else:
                        result["status"] = "Valid Response"
                        _LOGGER.debug(f"Device 0x{device_id:02x} gave valid response: {response_hex}")
                else:
                    _LOGGER.debug(f"Device 0x{device_id:02x} gave no response")
                    result["status"] = "No Response"
                
                results.append(result)
                
            except Exception as e:
                _LOGGER.debug(f"Error with device ID {device_id:02x}: {e}")
                results.append({
                    "device_id": device_id,
                    "hex": f"0x{device_id:02x}",
                    "status": f"Error: {str(e)}",
                    "request": request if 'request' in locals() else None,
                    "response": None
                })
            
            await asyncio.sleep(0.1)  # Small delay between requests
        
        # Store results
        scan_data = {
            "timestamp": datetime.now().isoformat(),
            "results": results,
            "start_id": start_id,
            "end_id": end_id
        }
        hass.data[DOMAIN]["device_scan"] = scan_data
        
        # Log summary
        valid_responses = [r for r in results if r["status"] == "Valid Response"]
        _LOGGER.info(f"Device scan complete. Found {len(valid_responses)} valid responses")
        for r in valid_responses:
            _LOGGER.info(f"Device {r['hex']}: Request={r['request']}, Response={r['response']}, Decoded={r.get('decoded')}")

    # Register both services
    hass.services.async_register(DOMAIN, "register_scan", handle_register_scan)
    hass.services.async_register(DOMAIN, "device_scan", handle_device_scan)
    
    # Forward the setup to the sensor platform
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.debug("Unloading Easun ISolar Inverter config entry")
    
    # Unload the sensor platform
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    
    return unload_ok 