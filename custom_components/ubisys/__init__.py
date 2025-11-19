"""Ubisys Zigbee Integration for Home Assistant.

This integration provides enhanced support for Ubisys Zigbee devices with
manufacturer-specific features not exposed by standard ZHA integration.

Device Support:
    - J1/J1-R: Window covering controllers with calibration support
    - D1/D1-R: Universal dimmers with phase control and ballast configuration
    - S1/S1-R: Power switches with input configuration
    - S2/S2-R: Power switches (planned)

Architecture:
    This integration follows a multi-device architecture:
    - Device-specific modules (j1_calibration.py for J1, d1_config.py for D1)
    - Shared configuration (input_config.py for D1/S1 input configuration via UI)
    - Shared utilities (helpers.py for common operations)
    - Centralized constants (const.py for all device types)

How It Works:
    1. Scans device registry on startup for Ubisys devices paired with ZHA
    2. Auto-triggers config flow for discovered supported devices
    3. Creates wrapper entities (covers for J1, lights for D1, switches for S1)
    4. Hides original ZHA entities to prevent duplicates
    5. Registers device-specific services:
       - J1: calibrate_cover (calibration workflow)
       - D1: configure_d1_phase_mode, configure_d1_ballast, configure_d1_inputs
       - S1: Input configuration via Config Flow UI (Settings → Devices → Configure)

Why Wrapper Entities:
    We create wrapper entities that delegate to ZHA because:
    - ZHA provides excellent Zigbee communication
    - We add Ubisys-specific features and metadata
    - J1 needs feature filtering based on shade type
    - D1 needs device identification for configuration services
    - S1/D1 input configuration managed via Config Flow UI

See Also:
    - j1_calibration.py: J1-specific calibration logic
    - d1_config.py: D1-specific configuration services (phase mode, ballast, inputs)
    - input_config.py: Shared D1/S1 input configuration micro-code generation
    - config_flow.py: UI-based configuration for all devices
    - helpers.py: Shared utilities for all device types
    - const.py: Device categorization and constants
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv

from .const import (
    DOMAIN,
    EVENT_UBISYS_CALIBRATION_COMPLETE,
    EVENT_UBISYS_INPUT,
)
from .discovery import async_setup_discovery
from .entity_management import (
    async_cleanup_orphaned_entities,
    async_cleanup_orphaned_ubisys_device,
    async_ensure_device_entry,
    async_ensure_zha_entity_enabled,
    async_hide_zha_entity,
    async_unhide_zha_entity,
    async_untrack_zha_entities,
    options_update_listener,
    recompute_verbose_flags,
)
from .input_monitor import (
    async_setup_input_monitoring,
    async_unload_input_monitoring,
)
from .services import async_setup_services

if TYPE_CHECKING:
    from homeassistant.helpers.typing import ConfigType

_LOGGER = logging.getLogger(__name__)

# Platforms to set up for this integration
# Cover: J1 window covering controllers
# Light: D1 universal dimmers
# Button: Calibration button for J1 devices
PLATFORMS: list[Platform] = [
    Platform.COVER,
    Platform.LIGHT,
    Platform.SWITCH,
    Platform.SENSOR,
    Platform.BUTTON,
]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Ubisys integration.

    This function is called once when the integration is loaded. It:
    1. Registers all device-specific services
    2. Sets up device discovery listener
    """
    # Initialize integration data storage
    hass.data.setdefault(DOMAIN, {})

    # Register services
    async_setup_services(hass)

    # Set up discovery and listeners
    async_setup_discovery(hass)

    # Register logbook event descriptions
    try:
        from homeassistant.components import logbook

        logbook.async_describe_event(
            hass,
            DOMAIN,
            EVENT_UBISYS_CALIBRATION_COMPLETE,
            lambda event: (
                f"Ubisys calibration completed "
                f"({event.data.get('shade_type', 'unknown')}) "
                f"in {event.data.get('duration_s', '?')}s"
            ),
        )
        logbook.async_describe_event(
            hass,
            DOMAIN,
            EVENT_UBISYS_INPUT,
            lambda event: (
                f"Ubisys input {event.data.get('press_type', 'unknown')} "
                f"on input {event.data.get('input_number', '?')}"
            ),
        )
        _LOGGER.debug("Registered logbook event descriptions")
    except Exception as err:
        # Logbook integration might not be available - this is non-critical
        _LOGGER.debug("Could not register logbook descriptions: %s", err)

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Ubisys device from a config entry."""
    _LOGGER.debug("Setting up Ubisys config entry: %s", entry.entry_id)

    # Store entry data in integration storage
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = entry.data

    device_ieee = entry.data["device_ieee"]

    # BUGFIX: Clean up orphaned entities from previous configurations
    orphaned_count = await async_cleanup_orphaned_entities(hass, device_ieee)
    if orphaned_count > 0:
        _LOGGER.info(
            "Cleaned up %d orphaned entities for device %s",
            orphaned_count,
            device_ieee,
        )

    # BUGFIX: Explicitly create/restore device entry
    await async_ensure_device_entry(hass, entry)

    # Set up platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Hide the original ZHA entity to prevent duplicates
    await async_hide_zha_entity(hass, entry)

    # Ensure ZHA entity stays enabled (but hidden) for wrapper delegation
    await async_ensure_zha_entity_enabled(hass, entry)

    # Set up input monitoring (idempotent)
    hass.async_create_task(async_setup_input_monitoring(hass, entry.entry_id))

    # Track options updates to refresh verbose flags
    entry.async_on_unload(entry.add_update_listener(options_update_listener))

    # Recompute verbose flags across entries
    recompute_verbose_flags(hass)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.debug("Unloading Ubisys config entry: %s", entry.entry_id)

    # Unhide the original ZHA entity
    await async_unhide_zha_entity(hass, entry)

    # Remove tracked ZHA entities for this config entry
    async_untrack_zha_entities(hass, entry)

    # Unload input monitoring
    await async_unload_input_monitoring(hass)

    # Unload platforms
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
        recompute_verbose_flags(hass)

        # Clean up any remaining orphaned entities for this device
        device_ieee = entry.data.get("device_ieee")
        if device_ieee:
            orphaned_count = await async_cleanup_orphaned_entities(hass, device_ieee)
            if orphaned_count > 0:
                _LOGGER.debug(
                    "Cleaned up %d orphaned entities during unload",
                    orphaned_count,
                )

    return bool(unload_ok)


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migrate old entry."""
    _LOGGER.debug("Migrating Ubisys entry from version %s", entry.version)

    if entry.version == 1:
        # Migration from version 1 to 2 (if needed in future)
        pass

    return True


# Config is entry-only; no YAML configuration
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)
