"""Device discovery and event monitoring for Ubisys integration.

This module handles:
- Automatic discovery of Ubisys devices paired with ZHA
- Monitoring device registry for new/removed devices
- Monitoring entity registry to ensure wrapper entities work correctly
"""

from __future__ import annotations

import logging

from homeassistant.const import EVENT_HOMEASSISTANT_STARTED
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er

try:
    from homeassistant.helpers.device_registry import (
        async_track_device_registry_updated_event,
    )
except Exception:  # Older HA versions may not provide this helper
    async_track_device_registry_updated_event = None

from .const import DOMAIN, MANUFACTURER, SUPPORTED_MODELS
from .entity_management import async_cleanup_orphaned_entities
from .ha_typing import HAEvent
from .helpers import is_verbose_info_logging
from .input_monitor import async_setup_input_monitoring

_LOGGER = logging.getLogger(__name__)


async def async_discover_devices(hass: HomeAssistant) -> None:
    """Scan device registry for Ubisys devices and trigger config flow.

    This function queries the Home Assistant device registry for ZHA devices
    from Ubisys and automatically triggers the config flow for any that aren't
    already configured.
    """
    _LOGGER.debug("Scanning device registry for Ubisys devices...")

    # Get device registry
    device_registry = dr.async_get(hass)

    # Track discovery statistics
    found_count = 0
    configured_count = 0
    triggered_count = 0

    # Scan all devices in registry
    for device_entry in device_registry.devices.values():
        # Skip devices without identifiers
        if not device_entry.identifiers:
            continue

        # Check if this is a ZHA device
        zha_identifier = None
        for identifier_domain, identifier_value in device_entry.identifiers:
            if identifier_domain == "zha":
                zha_identifier = identifier_value
                break

        if not zha_identifier:
            continue

        # Check if it's a Ubisys device
        if device_entry.manufacturer != MANUFACTURER:
            continue

        # Extract model (remove any parenthetical suffixes)
        model = device_entry.model
        if model and "(" in model:
            model = model.split("(")[0].strip()

        # Check if it's a supported model
        if model not in SUPPORTED_MODELS:
            _LOGGER.debug(
                "Found unsupported Ubisys device: %s (supported: %s)",
                model,
                SUPPORTED_MODELS,
            )
            continue

        found_count += 1
        _LOGGER.debug(
            "Found Ubisys device: %s %s (IEEE: %s, ID: %s)",
            device_entry.manufacturer,
            model,
            zha_identifier,
            device_entry.id,
        )

        # Check if already configured
        already_configured = False
        for entry in hass.config_entries.async_entries(DOMAIN):
            if entry.data.get("device_ieee") == str(zha_identifier):
                configured_count += 1
                already_configured = True
                _LOGGER.debug(
                    "Device %s already configured (entry: %s)",
                    zha_identifier,
                    entry.title,
                )
                break

        if already_configured:
            continue

        # Trigger discovery config flow
        triggered_count += 1
        _LOGGER.log(
            logging.INFO if is_verbose_info_logging(hass) else logging.DEBUG,
            "Auto-discovering Ubisys device: %s %s (IEEE: %s)",
            device_entry.manufacturer,
            model,
            zha_identifier,
        )

        hass.async_create_task(
            hass.config_entries.flow.async_init(
                DOMAIN,
                context={"source": "zha"},
                data={
                    "device_ieee": str(zha_identifier),
                    "device_id": device_entry.id,
                    "manufacturer": device_entry.manufacturer,
                    "model": model,
                    "name": device_entry.name or f"{device_entry.manufacturer} {model}",
                },
            )
        )

    _LOGGER.log(
        logging.INFO if is_verbose_info_logging(hass) else logging.DEBUG,
        "Device discovery complete: %d Ubisys devices found, "
        "%d already configured, %d new config flows triggered",
        found_count,
        configured_count,
        triggered_count,
    )


def async_setup_discovery(hass: HomeAssistant) -> None:
    """Set up discovery and monitoring when Home Assistant starts."""

    @callback  # type: ignore[misc]
    def async_setup_after_start(event: object) -> None:  # type: ignore[misc]
        """Set up discovery and input monitoring when Home Assistant starts."""
        hass.async_create_task(async_discover_devices(hass))

        # Set up input monitoring for all already-configured devices
        for entry in hass.config_entries.async_entries(DOMAIN):
            hass.async_create_task(async_setup_input_monitoring(hass, entry.entry_id))

    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, async_setup_after_start)

    _async_setup_discovery_listeners(hass)


def _async_setup_discovery_listeners(hass: HomeAssistant) -> None:
    """Set up listeners for device and entity registry updates."""

    # Also subscribe to device registry updates to discover devices paired
    # after startup without requiring a restart.
    @callback  # type: ignore[misc]
    def _device_registry_listener(event: HAEvent) -> None:  # type: ignore[misc]
        try:
            action = event.data.get("action")
            device_id = event.data.get("device_id")

            if not device_id:
                return

            # Handle device removal - cleanup orphaned entities
            if action == "remove":
                # Find the IEEE address for this device from our config entries
                # (device is already deleted, so we can't query device registry)
                ieee = None
                for entry in hass.config_entries.async_entries(DOMAIN):
                    if entry.data.get("device_id") == device_id:
                        ieee = entry.data.get("device_ieee")
                        break

                if ieee:
                    # Cleanup orphaned entities for this device (run in background)
                    hass.async_create_task(async_cleanup_orphaned_entities(hass, ieee))

                    _LOGGER.log(
                        (
                            logging.INFO
                            if is_verbose_info_logging(hass)
                            else logging.DEBUG
                        ),
                        "Device %s removed, cleaning up orphaned entities for IEEE %s",
                        device_id,
                        ieee,
                    )
                return

            # Handle device creation - auto-discovery
            if action != "create":
                return

            dev_reg = dr.async_get(hass)
            device = dev_reg.async_get(device_id)
            if not device or device.manufacturer != MANUFACTURER:
                return
            # Basic model normalization (strip parentheses suffix)
            model = device.model.split("(")[0].strip() if device.model else ""
            if model not in SUPPORTED_MODELS:
                return
            # Trigger config flow if not already configured
            for entry in hass.config_entries.async_entries(DOMAIN):
                if entry.data.get("device_ieee") == str(
                    next(
                        (idv for (idd, idv) in device.identifiers if idd == "zha"),
                        "",
                    )
                ):
                    return
            _LOGGER.log(
                logging.INFO if is_verbose_info_logging(hass) else logging.DEBUG,
                "Auto-discovering newly added Ubisys device: %s %s",
                device.manufacturer,
                model,
            )
            hass.async_create_task(async_discover_devices(hass))
        except Exception:  # best-effort listener
            _LOGGER.debug(
                "Device registry listener encountered an error", exc_info=True
            )

    if async_track_device_registry_updated_event is not None:
        async_track_device_registry_updated_event(hass, _device_registry_listener)
    else:
        _LOGGER.debug("Device registry update listener helper not available; skipping")

    # Register integration-level entity registry listener
    @callback  # type: ignore[misc]
    def _entity_registry_listener(event: HAEvent) -> None:  # type: ignore[misc]
        """Monitor entity registry updates and re-enable tracked ZHA entities."""
        try:
            # Only process entity updates (not create/remove)
            if event.data.get("action") != "update":
                return

            entity_id = event.data.get("entity_id")
            if not entity_id:
                return

            # Check if this is a tracked ZHA entity
            tracked = hass.data.get(DOMAIN, {}).get("tracked_zha_entities", set())
            if entity_id not in tracked:
                return

            # Check if entity was disabled by integration
            entity_reg = er.async_get(hass)
            entity_entry = entity_reg.async_get(entity_id)

            if (
                entity_entry
                and entity_entry.disabled_by == er.RegistryEntryDisabler.INTEGRATION
            ):
                _LOGGER.debug(
                    "Tracked ZHA entity %s was disabled by integration. "
                    "Re-enabling to maintain wrapper functionality.",
                    entity_id,
                )
                try:
                    entity_reg.async_update_entity(
                        entity_id,
                        disabled_by=None,
                    )
                except Exception as err:
                    _LOGGER.error(
                        "Failed to re-enable tracked ZHA entity %s: %s",
                        entity_id,
                        err,
                    )
        except Exception:  # best-effort listener
            _LOGGER.debug(
                "Entity registry listener encountered an error", exc_info=True
            )

    # Subscribe to entity registry updates
    hass.bus.async_listen(er.EVENT_ENTITY_REGISTRY_UPDATED, _entity_registry_listener)
