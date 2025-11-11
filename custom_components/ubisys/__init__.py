"""Ubisys Zigbee Integration for Home Assistant.

This integration provides enhanced support for Ubisys Zigbee devices,
starting with the J1 window covering controller. It creates wrapper
entities with feature filtering based on shade type and provides
calibration services.

Architecture:
- Listens for ZHA device discovery
- Auto-triggers config flow for supported devices
- Creates wrapper entities with filtered features
- Hides original ZHA entities to prevent duplicates
- Registers calibration service

Supported Devices:
- Ubisys J1 Window Covering Controller
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_HOMEASSISTANT_STARTED, Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from .calibration import async_calibrate_j1
from .const import DOMAIN, MANUFACTURER, SERVICE_CALIBRATE, SUPPORTED_MODELS

if TYPE_CHECKING:
    from homeassistant.helpers.typing import ConfigType

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.COVER, Platform.BUTTON]

# ZHA signals
ZHA_DEVICE_ADDED = "zha_device_added"


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Ubisys integration."""
    hass.data.setdefault(DOMAIN, {})

    # Register calibration service
    hass.services.async_register(
        DOMAIN,
        SERVICE_CALIBRATE,
        async_calibrate_j1,
    )

    # Set up discovery listener after Home Assistant starts
    @callback
    def setup_discovery(event):
        """Set up discovery when Home Assistant starts."""
        async_setup_discovery(hass)

    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, setup_discovery)

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Ubisys device from a config entry."""
    _LOGGER.debug("Setting up Ubisys config entry: %s", entry.entry_id)

    # Store entry data
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = entry.data

    # Set up platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Hide the original ZHA entity to prevent duplicates
    await _hide_zha_entity(hass, entry)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.debug("Unloading Ubisys config entry: %s", entry.entry_id)

    # Unhide the original ZHA entity
    await _unhide_zha_entity(hass, entry)

    # Unload platforms
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migrate old entry."""
    _LOGGER.debug("Migrating Ubisys entry from version %s", entry.version)

    if entry.version == 1:
        # Migration from version 1 to 2 (if needed in future)
        pass

    return True


async def _hide_zha_entity(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Hide the original ZHA cover entity to prevent duplicate entities.

    This sets the entity's disabled_by and hidden_by flags so it won't
    appear in the UI while we use our wrapper entity instead.
    """
    entity_registry = er.async_get(hass)
    device_ieee = entry.data.get("device_ieee")

    if not device_ieee:
        _LOGGER.warning("No device IEEE in config entry, cannot hide ZHA entity")
        return

    # Find the ZHA cover entity for this device
    zha_entities = er.async_entries_for_config_entry(
        entity_registry, entry.data.get("zha_config_entry_id", "")
    )

    for entity_entry in zha_entities:
        # Look for cover platform entities matching our device
        if (
            entity_entry.platform == "zha"
            and entity_entry.domain == "cover"
            and entity_entry.device_id == entry.data.get("device_id")
        ):
            _LOGGER.debug(
                "Hiding ZHA cover entity: %s (%s)",
                entity_entry.entity_id,
                entity_entry.unique_id,
            )

            entity_registry.async_update_entity(
                entity_entry.entity_id,
                disabled_by=er.RegistryEntryDisabler.INTEGRATION,
                hidden_by=er.RegistryEntryHider.INTEGRATION,
            )


async def _unhide_zha_entity(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Unhide the original ZHA cover entity when unloading integration.

    This restores the original ZHA entity when the integration is removed.
    """
    entity_registry = er.async_get(hass)
    device_ieee = entry.data.get("device_ieee")

    if not device_ieee:
        _LOGGER.warning("No device IEEE in config entry, cannot unhide ZHA entity")
        return

    # Find the ZHA cover entity for this device
    zha_entities = er.async_entries_for_config_entry(
        entity_registry, entry.data.get("zha_config_entry_id", "")
    )

    for entity_entry in zha_entities:
        # Look for cover platform entities matching our device
        if (
            entity_entry.platform == "zha"
            and entity_entry.domain == "cover"
            and entity_entry.device_id == entry.data.get("device_id")
            and entity_entry.disabled_by == er.RegistryEntryDisabler.INTEGRATION
        ):
            _LOGGER.debug(
                "Unhiding ZHA cover entity: %s (%s)",
                entity_entry.entity_id,
                entity_entry.unique_id,
            )

            entity_registry.async_update_entity(
                entity_entry.entity_id,
                disabled_by=None,
                hidden_by=None,
            )


@callback
def async_setup_discovery(hass: HomeAssistant) -> None:
    """Set up device discovery listener for Ubisys devices.

    This function should be called after Home Assistant has started.
    It listens for ZHA device additions and triggers config flow for
    supported Ubisys devices.
    """

    @callback
    def device_added_listener(device) -> None:
        """Handle ZHA device added event."""
        # Check if this is a supported Ubisys device
        if device.manufacturer != MANUFACTURER:
            return

        if device.model not in SUPPORTED_MODELS:
            _LOGGER.debug(
                "Unsupported Ubisys model discovered: %s (supported: %s)",
                device.model,
                SUPPORTED_MODELS,
            )
            return

        _LOGGER.info(
            "Discovered supported Ubisys device: %s %s (IEEE: %s)",
            device.manufacturer,
            device.model,
            device.ieee,
        )

        # Get device registry to find device_id
        device_registry = dr.async_get(hass)
        device_entry = device_registry.async_get_device(
            identifiers={(  # type: ignore[arg-type]
                "zha",
                str(device.ieee),
            )}
        )

        if not device_entry:
            _LOGGER.warning(
                "Could not find device entry for %s %s",
                device.manufacturer,
                device.model,
            )
            return

        # Check if already configured
        for entry in hass.config_entries.async_entries(DOMAIN):
            if entry.data.get("device_ieee") == str(device.ieee):
                _LOGGER.debug(
                    "Device %s already configured, skipping discovery",
                    device.ieee,
                )
                return

        # Trigger discovery config flow
        hass.async_create_task(
            hass.config_entries.flow.async_init(
                DOMAIN,
                context={"source": "zha"},
                data={
                    "device_ieee": str(device.ieee),
                    "device_id": device_entry.id,
                    "manufacturer": device.manufacturer,
                    "model": device.model,
                    "name": device_entry.name or f"{device.manufacturer} {device.model}",
                },
            )
        )

    # Register the listener
    async_dispatcher_connect(hass, ZHA_DEVICE_ADDED, device_added_listener)
    _LOGGER.debug("Ubisys device discovery listener registered")


@callback
def async_remove_discovery(hass: HomeAssistant) -> None:
    """Remove device discovery listener."""
    # Note: async_dispatcher_connect doesn't provide a way to unregister,
    # so we rely on the listener callback being garbage collected when
    # the integration is unloaded
    pass
