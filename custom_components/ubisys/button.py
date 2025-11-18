"""Button platform for Ubisys Zigbee integration.

Provides a calibration button entity for easy access to the calibration service.

Button → Service Pattern:

This module demonstrates the "button → service" pattern, where a button entity
serves as a user-friendly UI wrapper around a more complex service.

Why Use This Pattern:

1. User Experience:
   - Button: One-click calibration from device page
   - Service: Requires Developer Tools → Services (advanced users only)
   - Button is more discoverable and easier to use

2. Flexibility:
   - Users who prefer UI: Click button on device page
   - Users who prefer automation: Call service from automation
   - Both approaches work, catering to different user preferences

3. Separation of Concerns:
   - Button entity (button.py): UI presentation, entity lifecycle
   - Service handler (j1_calibration.py): Calibration logic, error handling
   - This keeps button code simple (just delegates to service)

How It Works:

1. Button entity is created for J1 devices during platform setup
2. User clicks "Calibrate" button on device page in Home Assistant UI
3. async_press() method is called
4. Button finds associated cover entity ID
5. Button calls calibrate_j1 service with cover entity ID
6. Service handler performs actual calibration workflow
7. User sees progress/results via notifications and entity states

Alternative Approaches Considered:

A. Put calibration logic directly in button:
   - Pro: Simpler structure (no service needed)
   - Con: Can't trigger from automations or scripts
   - Con: Can't call from Developer Tools for debugging
   - Verdict: Too limiting

B. Service only (no button):
   - Pro: Simpler code (one less file)
   - Con: Poor user experience (requires Developer Tools knowledge)
   - Con: Not discoverable for average users
   - Verdict: Too developer-focused

C. Both button and service (current approach):
   - Pro: Best of both worlds (UI + automation)
   - Pro: Button delegates to service (DRY principle)
   - Con: Slight code duplication (entity lookup)
   - Verdict: Best balance of usability and flexibility
"""

from __future__ import annotations

import logging

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_DEVICE_IEEE, DOMAIN, SERVICE_CALIBRATE
from .helpers import is_verbose_info_logging

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Ubisys button from config entry.

    Only creates calibration buttons for J1/J1-R window covering devices.
    Other device types (D1 dimmers, S1 switches) don't have motors to calibrate.
    """
    device_ieee = config_entry.data[CONF_DEVICE_IEEE]
    model = config_entry.data.get("model", "J1")

    # Only create calibration buttons for J1/J1-R window covering models
    # Calibration is motor-specific: learns travel limits via stall detection
    # D1 devices are dimmers (no motor, no calibration needed)
    # S1 devices are switches (no motor, no calibration needed)
    # Both D1/S1 have input configuration via services, but not calibration
    from .const import WINDOW_COVERING_MODELS

    if model not in WINDOW_COVERING_MODELS:
        _LOGGER.debug(
            "Skipping calibration buttons for non-window-covering device: model=%s (ieee=%s)",
            model,
            device_ieee,
        )
        return

    _LOGGER.log(
        logging.INFO if is_verbose_info_logging(hass) else logging.DEBUG,
        "Creating Ubisys calibration buttons for J1 device: %s",
        device_ieee,
    )

    button = UbisysCalibrationButton(
        hass=hass,
        config_entry=config_entry,
        device_ieee=device_ieee,
    )
    health = UbisysHealthCheckButton(
        hass=hass,
        config_entry=config_entry,
        device_ieee=device_ieee,
    )

    async_add_entities([button, health])


class UbisysCalibrationButton(ButtonEntity):
    """Button entity to trigger calibration."""

    _attr_has_entity_name = True
    _attr_name = "Calibrate"
    _attr_icon = "mdi:tune"

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        device_ieee: str,
    ) -> None:
        """Initialize the calibration button."""
        self.hass = hass
        self._config_entry = config_entry
        self._device_ieee = device_ieee

        # Set unique ID
        self._attr_unique_id = f"{device_ieee}_calibrate"

        # Set device info to link to the same device as the cover
        self._attr_device_info = {
            "identifiers": {(DOMAIN, device_ieee)},
        }

        _LOGGER.debug("Initialized UbisysCalibrationButton: ieee=%s", device_ieee)

    async def async_press(self) -> None:
        """Handle the calibration button press.

        Delegates to the ubisys.calibrate_j1 service for the device's cover entity.
        """
        from homeassistant.helpers import entity_registry as er

        _LOGGER.log(
            logging.INFO if is_verbose_info_logging(self.hass) else logging.DEBUG,
            "Calibration button pressed for device: %s",
            self._device_ieee,
        )

        entity_registry = er.async_get(self.hass)
        entries = er.async_entries_for_config_entry(
            entity_registry, self._config_entry.entry_id
        )
        cover_entity_id = next(
            (e.entity_id for e in entries if e.domain == "cover"), None
        )
        if not cover_entity_id:
            _LOGGER.error(
                "Could not find cover entity for device: %s", self._device_ieee
            )
            return

        try:
            await self.hass.services.async_call(
                DOMAIN,
                SERVICE_CALIBRATE,
                {"entity_id": cover_entity_id},
                blocking=False,
            )
            _LOGGER.log(
                logging.INFO if is_verbose_info_logging(self.hass) else logging.DEBUG,
                "Calibration service called for: %s",
                cover_entity_id,
            )
        except Exception as err:
            _LOGGER.error("Failed to call calibration service: %s", err)


class UbisysHealthCheckButton(ButtonEntity):
    """Button entity to run a read-only J1 health check (test_mode)."""

    _attr_has_entity_name = True
    _attr_name = "Health Check"
    _attr_icon = "mdi:heart-pulse"

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        device_ieee: str,
    ) -> None:
        self.hass = hass
        self._config_entry = config_entry
        self._device_ieee = device_ieee
        self._attr_unique_id = f"{device_ieee}_health_check"
        self._attr_device_info = {"identifiers": {(DOMAIN, device_ieee)}}

    async def async_press(self) -> None:
        """Run a read-only health check (test_mode)."""
        from homeassistant.helpers import entity_registry as er

        entity_registry = er.async_get(self.hass)
        entries = er.async_entries_for_config_entry(
            entity_registry, self._config_entry.entry_id
        )
        cover_entity_id = next(
            (e.entity_id for e in entries if e.domain == "cover"), None
        )
        if not cover_entity_id:
            return
        await self.hass.services.async_call(
            DOMAIN,
            SERVICE_CALIBRATE,
            {"entity_id": cover_entity_id, "test_mode": True},
            blocking=False,
        )
