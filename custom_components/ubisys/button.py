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

from .const import CONF_DEVICE_IEEE, DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Ubisys button from config entry."""
    device_ieee = config_entry.data[CONF_DEVICE_IEEE]

    _LOGGER.info("Creating Ubisys calibration button for device: %s", device_ieee)

    button = UbisysCalibrationButton(
        hass=hass,
        config_entry=config_entry,
        device_ieee=device_ieee,
    )

    async_add_entities([button])


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

        _LOGGER.debug(
            "Initialized UbisysCalibrationButton: ieee=%s",
            device_ieee,
        )

    async def async_press(self) -> None:
        """Handle the button press - trigger calibration.

        Button → Service Delegation Pattern:

        This method demonstrates the delegation pattern:
        1. Find the cover entity for this device
        2. Call the calibration service with that entity
        3. Let the service handle all the complex logic

        Why Look Up Cover Entity:
           The calibration service expects a cover entity_id as input.
           We need to find which cover entity belongs to this device.

        Entity Lookup Strategy:
           - All entities for a device share the same config_entry_id
           - We query the entity registry for all entities in this config entry
           - We filter for domain="cover" to find the J1 cover entity
           - This is guaranteed to exist (cover platform runs before button platform)

        Error Handling:
           If cover entity isn't found (shouldn't happen), we log error and return.
           The service call is non-blocking (blocking=False) so button press
           returns immediately while calibration runs in background.
        """
        _LOGGER.info("Calibration button pressed for device: %s", self._device_ieee)

        # Find the cover entity ID for this device
        # We need this because the service expects entity_id, not device_id
        from homeassistant.helpers import entity_registry as er

        entity_registry = er.async_get(self.hass)
        entries = er.async_entries_for_config_entry(
            entity_registry, self._config_entry.entry_id
        )

        # Search for the cover entity in this device's config entry
        cover_entity_id = None
        for entry in entries:
            if entry.domain == "cover":
                cover_entity_id = entry.entity_id
                break

        if not cover_entity_id:
            # This shouldn't happen (cover is created before button)
            _LOGGER.error(
                "Could not find cover entity for device: %s", self._device_ieee
            )
            return

        # Call the calibration service
        # blocking=False means we return immediately while calibration runs
        # The service handler will send progress notifications to the user
        try:
            await self.hass.services.async_call(
                DOMAIN,
                "calibrate_j1",
                {"entity_id": cover_entity_id},
                blocking=False,
            )
            _LOGGER.info("Calibration service called for: %s", cover_entity_id)
        except Exception as err:
            _LOGGER.error("Failed to call calibration service: %s", err)
