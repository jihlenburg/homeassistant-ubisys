"""Button platform for Ubisys Zigbee integration.

Provides a calibration button entity for easy access to the calibration service.
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
        """Handle the button press - trigger calibration."""
        _LOGGER.info("Calibration button pressed for device: %s", self._device_ieee)

        # Find the cover entity ID for this device
        from homeassistant.helpers import entity_registry as er

        entity_registry = er.async_get(self.hass)
        entries = er.async_entries_for_config_entry(
            entity_registry, self._config_entry.entry_id
        )

        cover_entity_id = None
        for entry in entries:
            if entry.domain == "cover":
                cover_entity_id = entry.entity_id
                break

        if not cover_entity_id:
            _LOGGER.error(
                "Could not find cover entity for device: %s", self._device_ieee
            )
            return

        # Call the calibration service
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
