"""The Ubisys integration."""

from __future__ import annotations

import logging

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ENTITY_ID, Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import entity_registry as er

from .const import (
    ATTR_ENTITY_ID,
    CONF_ZHA_ENTITY_ID,
    DOMAIN,
    SERVICE_CALIBRATE,
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.COVER]

# Service schema for calibration
CALIBRATE_SERVICE_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_ENTITY_ID): cv.entity_id,
    }
)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Ubisys from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = entry.data

    # Forward setup to platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register services
    async def async_handle_calibrate(call: ServiceCall) -> None:
        """Handle the calibrate service call."""
        entity_id = call.data[CONF_ENTITY_ID]

        # Find the config entry for this entity
        entity_registry = er.async_get(hass)
        entity_entry = entity_registry.async_get(entity_id)

        if entity_entry is None:
            _LOGGER.error("Entity %s not found", entity_id)
            return

        # Get the ZHA entity ID from the config entry
        config_entry = None
        for entry_id, entry_data in hass.data[DOMAIN].items():
            if isinstance(entry_data, dict) and entry_data.get(CONF_ZHA_ENTITY_ID):
                # Check if this is the right config entry
                entries = hass.config_entries.async_entries(DOMAIN)
                for cfg_entry in entries:
                    if cfg_entry.entry_id == entry_id:
                        # Get the Ubisys entity from this config entry
                        ubisys_entity_id = f"cover.ubisys_{entity_entry.original_name or 'cover'}"
                        if entity_id == ubisys_entity_id or entity_entry.config_entry_id == entry_id:
                            config_entry = cfg_entry
                            break
                if config_entry:
                    break

        if config_entry is None:
            _LOGGER.error("Config entry not found for entity %s", entity_id)
            return

        zha_entity_id = config_entry.data.get(CONF_ZHA_ENTITY_ID)
        shade_type = config_entry.data.get("shade_type")

        if not zha_entity_id:
            _LOGGER.error("ZHA entity ID not found in config entry")
            return

        _LOGGER.info(
            "Starting calibration for %s (ZHA entity: %s, shade type: %s)",
            entity_id,
            zha_entity_id,
            shade_type,
        )

        # Call the calibration python_script
        await hass.services.async_call(
            "python_script",
            "ubisys_j1_calibrate",
            {
                "entity_id": zha_entity_id,
                "shade_type": shade_type,
            },
            blocking=False,
        )

    # Register the calibrate service
    hass.services.async_register(
        DOMAIN,
        SERVICE_CALIBRATE,
        async_handle_calibrate,
        schema=CALIBRATE_SERVICE_SCHEMA,
    )

    # Listen for config entry updates
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # Unload platforms
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

        # Unregister services if no more entries
        if not hass.data[DOMAIN]:
            hass.services.async_remove(DOMAIN, SERVICE_CALIBRATE)

    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)
