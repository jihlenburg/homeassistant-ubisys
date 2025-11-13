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
from typing import TYPE_CHECKING, Any

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_HOMEASSISTANT_STARTED, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er

try:
    from homeassistant.helpers.device_registry import (
        async_track_device_registry_updated_event,
    )
except Exception:  # Older HA versions may not provide this helper
    async_track_device_registry_updated_event = None
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from .const import (
    DOMAIN,
    MANUFACTURER,
    OPTION_VERBOSE_INFO_LOGGING,
    OPTION_VERBOSE_INPUT_LOGGING,
    SERVICE_CALIBRATE,
    SERVICE_CONFIGURE_D1_BALLAST,
    SERVICE_CONFIGURE_D1_INPUTS,
    SERVICE_CONFIGURE_D1_PHASE_MODE,
    SUPPORTED_MODELS,
    get_device_type,
)
from .d1_config import (
    async_configure_ballast,
    async_configure_inputs,
    async_configure_phase_mode,
)
from .ha_typing import HAEvent
from .ha_typing import callback as _typed_callback
from .helpers import is_verbose_info_logging
from .input_monitor import (
    async_setup_input_monitoring,
    async_unload_input_monitoring,
)
from .j1_calibration import async_calibrate_j1, async_tune_j1

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

# ZHA integration constants
# Note: ZHA does not emit dispatcher signals for device additions.
# Instead, we query the device registry after startup to discover devices.


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Ubisys integration.

    This function is called once when the integration is loaded. It:
    1. Registers all device-specific services
    2. Sets up device discovery listener

    Service Registration:
        - J1 services: calibrate_cover (window covering calibration)
        - D1 services: configure_d1_phase_mode, configure_d1_ballast, configure_d1_inputs
        - S1 services: configure_s1_input (physical switch input configuration)

    Why Register Services Here:
        Services are registered at integration level (not per-device) because:
        - Multiple devices of the same type share the same services
        - Services are stateless and operate on entity_id parameter
        - Simpler to register once vs per-device registration

    Discovery Setup:
        We wait until EVENT_HOMEASSISTANT_STARTED before setting up discovery
        to ensure ZHA integration is fully loaded and ready.

    Service Registration Order:
        Services are registered in device-type order (J1, D1, S1) for consistency
        and easier debugging. The order doesn't affect functionality but helps
        maintain code organization.
    """
    # Initialize integration data storage
    # This dictionary will hold per-device config entry data and shared resources
    # like calibration locks and input monitors
    hass.data.setdefault(DOMAIN, {})

    # Register J1 calibration service
    _LOGGER.debug("Registering J1 calibration service: %s", SERVICE_CALIBRATE)
    hass.services.async_register(
        DOMAIN,
        SERVICE_CALIBRATE,
        async_calibrate_j1,
        schema=vol.Schema(
            {
                vol.Required("entity_id"): cv.entity_ids,
                vol.Optional("test_mode", default=False): cv.boolean,
            }
        ),
    )
    # Advanced J1 tuning
    try:
        from .const import SERVICE_TUNE_J1_ADVANCED

        _LOGGER.debug(
            "Registering J1 advanced tuning service: %s", SERVICE_TUNE_J1_ADVANCED
        )
        hass.services.async_register(
            DOMAIN,
            SERVICE_TUNE_J1_ADVANCED,
            async_tune_j1,
            schema=vol.Schema(
                {
                    vol.Required("entity_id"): cv.entity_ids,
                    vol.Optional("turnaround_guard_time"): cv.positive_int,
                    vol.Optional("inactive_power_threshold"): cv.positive_int,
                    vol.Optional("startup_steps"): cv.positive_int,
                    vol.Optional("additional_steps"): vol.All(
                        vol.Coerce(int), vol.Range(min=0, max=100)
                    ),
                    vol.Optional("input_actions"): cv.string,
                }
            ),
        )
    except Exception:
        _LOGGER.debug("Unable to register J1 tuning service", exc_info=True)

    # Register D1 configuration services
    _LOGGER.debug(
        "Registering D1 phase mode service: %s", SERVICE_CONFIGURE_D1_PHASE_MODE
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_CONFIGURE_D1_PHASE_MODE,
        async_configure_phase_mode,
        schema=vol.Schema(
            {
                vol.Required("entity_id"): cv.entity_ids,
                vol.Required("phase_mode"): vol.In(["automatic", "forward", "reverse"]),
            }
        ),
    )

    _LOGGER.debug("Registering D1 ballast service: %s", SERVICE_CONFIGURE_D1_BALLAST)
    hass.services.async_register(
        DOMAIN,
        SERVICE_CONFIGURE_D1_BALLAST,
        async_configure_ballast,
        schema=vol.Schema(
            {
                vol.Required("entity_id"): cv.entity_ids,
                vol.Optional("min_level"): vol.All(
                    vol.Coerce(int), vol.Range(min=1, max=254)
                ),
                vol.Optional("max_level"): vol.All(
                    vol.Coerce(int), vol.Range(min=1, max=254)
                ),
            }
        ),
    )

    # D1 inputs are configured via Options Flow presets (micro-code). Service removed.

    # Note: S1 input configuration is now done via Config Flow UI
    # (Settings → Devices & Services → Ubisys → Configure)

    # Gate registration info to reduce noise
    _LOGGER.log(
        logging.INFO if is_verbose_info_logging(hass) else logging.DEBUG,
        "Registered Ubisys services",
    )

    # Set up discovery listener and input monitoring after Home Assistant starts
    # Why wait for EVENT_HOMEASSISTANT_STARTED?
    # - ZHA integration must be fully initialized before we can:
    #   1. Query device registry for ZHA devices
    #   2. Access device information and attributes
    #   3. Subscribe to ZHA events for input monitoring
    # - Setting up too early would cause errors or miss devices
    # - This is a common pattern for integrations that depend on other integrations
    @_typed_callback
    def async_setup_after_start(event: object) -> None:
        """Set up discovery and input monitoring when Home Assistant starts."""
        # Scan device registry for Ubisys devices (query-based discovery)
        # Note: ZHA doesn't emit device addition dispatcher signals, so we
        # query the device registry instead of listening for events
        hass.async_create_task(async_discover_devices(hass))

        # Also subscribe to device registry updates to discover devices paired
        # after startup without requiring a restart.
        @_typed_callback
        def _device_registry_listener(event: HAEvent) -> None:
            try:
                action = event.data.get("action")
                if action != "create":
                    return
                device_id = event.data.get("device_id")
                if not device_id:
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
            _LOGGER.debug(
                "Device registry update listener helper not available; skipping"
            )

        # Set up input monitoring for all already-configured devices
        # This handles devices that were configured before this startup
        # (e.g., after a Home Assistant restart)
        # Note: We create async tasks to avoid blocking startup
        for entry in hass.config_entries.async_entries(DOMAIN):
            hass.async_create_task(async_setup_input_monitoring(hass, entry.entry_id))

    # Register the startup callback
    # This ensures ZHA is ready before we try to interact with it
    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, async_setup_after_start)

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Ubisys device from a config entry.

    This is called when a device is discovered or configured manually.
    It creates our wrapper entities and hides the underlying ZHA entities.
    """
    _LOGGER.debug("Setting up Ubisys config entry: %s", entry.entry_id)

    # Store entry data in integration storage
    # This makes device info (IEEE, model, etc.) accessible to platforms
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = entry.data

    # Set up platforms (cover for J1, light for D1, button for calibration)
    # This creates the actual entities that users interact with
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Hide the original ZHA entity to prevent duplicates
    # We create wrapper entities that delegate to ZHA, so we hide ZHA's
    # entities to avoid confusion (e.g., two "Bedroom Blind" entities)
    await _hide_zha_entity(hass, entry)

    # Track options updates to refresh verbose flags
    entry.async_on_unload(entry.add_update_listener(_options_update_listener))

    # Recompute verbose flags across entries
    _recompute_verbose_flags(hass)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.debug("Unloading Ubisys config entry: %s", entry.entry_id)

    # Unhide the original ZHA entity
    await _unhide_zha_entity(hass, entry)

    # Unload input monitoring
    await async_unload_input_monitoring(hass)

    # Unload platforms
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
        _recompute_verbose_flags(hass)

    return bool(unload_ok)


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migrate old entry."""
    _LOGGER.debug("Migrating Ubisys entry from version %s", entry.version)

    if entry.version == 1:
        # Migration from version 1 to 2 (if needed in future)
        pass

    return True


async def _hide_zha_entity(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Hide the original ZHA entity to prevent duplicate entities.

    This sets the entity's disabled_by and hidden_by flags so it won't
    appear in the UI while we use our wrapper entity instead.

    Domain Detection:
        The domain to hide is determined by device type:
        - J1 (window covering): Hide ZHA cover entity
        - D1 (dimmer): Hide ZHA light entity
        - Future devices: Hide appropriate entity domain

    Why Hide Instead of Delete:
        We hide rather than delete the ZHA entity because:
        - User might want to uninstall our integration and revert to ZHA
        - Preserves ZHA's excellent Zigbee communication
        - Easy to unhide on integration removal
    """
    entity_registry = er.async_get(hass)
    device_ieee = entry.data.get("device_ieee")
    model = entry.data.get("model", "")

    if not device_ieee:
        _LOGGER.warning("No device IEEE in config entry, cannot hide ZHA entity")
        return

    # Determine which domain to hide based on device type
    device_type = get_device_type(model)

    if device_type == "window_covering":
        domain_to_hide = "cover"
    elif device_type == "dimmer":
        domain_to_hide = "light"
    else:
        _LOGGER.warning(
            "Unknown device type '%s' for model '%s', cannot determine domain to hide",
            device_type,
            model,
        )
        return

    _LOGGER.debug(
        "Hiding ZHA %s entity for device type %s (model %s)",
        domain_to_hide,
        device_type,
        model,
    )

    # Find the ZHA entity for this device
    zha_entities = er.async_entries_for_config_entry(
        entity_registry, entry.data.get("zha_config_entry_id", "")
    )

    for entity_entry in zha_entities:
        # Look for matching platform and domain
        if (
            entity_entry.platform == "zha"
            and entity_entry.domain == domain_to_hide
            and entity_entry.device_id == entry.data.get("device_id")
        ):
            _LOGGER.debug(
                "Hiding ZHA %s entity: %s (%s)",
                domain_to_hide,
                entity_entry.entity_id,
                entity_entry.unique_id,
            )

            entity_registry.async_update_entity(
                entity_entry.entity_id,
                disabled_by=er.RegistryEntryDisabler.INTEGRATION,
                hidden_by=er.RegistryEntryHider.INTEGRATION,
            )


async def _unhide_zha_entity(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Unhide the original ZHA entity when unloading integration.

    This restores the original ZHA entity when the integration is removed,
    allowing the user to revert back to using ZHA directly.

    Domain Detection:
        Same logic as _hide_zha_entity - determines domain based on device type.
    """
    entity_registry = er.async_get(hass)
    device_ieee = entry.data.get("device_ieee")
    model = entry.data.get("model", "")

    if not device_ieee:
        _LOGGER.warning("No device IEEE in config entry, cannot unhide ZHA entity")
        return

    # Determine which domain to unhide based on device type
    device_type = get_device_type(model)

    if device_type == "window_covering":
        domain_to_unhide = "cover"
    elif device_type == "dimmer":
        domain_to_unhide = "light"
    else:
        _LOGGER.warning(
            "Unknown device type '%s' for model '%s', cannot determine domain to unhide",
            device_type,
            model,
        )
        return

    _LOGGER.debug(
        "Unhiding ZHA %s entity for device type %s (model %s)",
        domain_to_unhide,
        device_type,
        model,
    )

    # Find the ZHA entity for this device
    zha_entities = er.async_entries_for_config_entry(
        entity_registry, entry.data.get("zha_config_entry_id", "")
    )

    for entity_entry in zha_entities:
        # Look for matching platform and domain
        if (
            entity_entry.platform == "zha"
            and entity_entry.domain == domain_to_unhide
            and entity_entry.device_id == entry.data.get("device_id")
            and entity_entry.disabled_by == er.RegistryEntryDisabler.INTEGRATION
        ):
            _LOGGER.debug(
                "Unhiding ZHA %s entity: %s (%s)",
                domain_to_unhide,
                entity_entry.entity_id,
                entity_entry.unique_id,
            )

            entity_registry.async_update_entity(
                entity_entry.entity_id,
                disabled_by=None,
                hidden_by=None,
            )


async def async_discover_devices(hass: HomeAssistant) -> None:
    """Scan device registry for Ubisys devices and trigger config flow.

    This function queries the Home Assistant device registry for ZHA devices
    from Ubisys and automatically triggers the config flow for any that aren't
    already configured.

    Why Query Instead of Listen:
        ZHA doesn't emit dispatcher signals when devices are added. The only
        signals ZHA provides are for entity additions ("zha_add_entities"),
        not device additions. Therefore, we use a query-based approach that
        scans the device registry on startup.

    Trade-offs:
        - Pro: Reliable, works with devices paired before integration installed
        - Pro: Handles restarts (rescans on every HA startup)
        - Con: Won't auto-discover devices paired after startup (user must
          manually add via config flow UI or restart HA)

    This approach is sufficient because:
        1. Most users install integration after pairing devices with ZHA
        2. Manual config flow is always available
        3. Restart triggers re-scan (common workflow after pairing new device)
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


def _recompute_verbose_flags(hass: HomeAssistant) -> None:
    """Recompute and store global verbose logging flags from all entries."""
    info = any(
        entry.options.get(OPTION_VERBOSE_INFO_LOGGING, False)
        for entry in hass.config_entries.async_entries(DOMAIN)
    )
    per_input = any(
        entry.options.get(OPTION_VERBOSE_INPUT_LOGGING, False)
        for entry in hass.config_entries.async_entries(DOMAIN)
    )
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN]["verbose_info_logging"] = info
    hass.data[DOMAIN]["verbose_input_logging"] = per_input


async def _options_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update by recomputing verbose flags."""
    _recompute_verbose_flags(hass)


# Config is entry-only; no YAML configuration
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)
