"""Button platform for Ubisys integration."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CONF_SHADE_TYPE,
    CONF_ZHA_ENTITY_ID,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Ubisys button from a config entry."""
    zha_entity_id = config_entry.data[CONF_ZHA_ENTITY_ID]
    shade_type = config_entry.data[CONF_SHADE_TYPE]

    # Get the ZHA entity
    entity_registry = er.async_get(hass)
    entity_entry = entity_registry.async_get(zha_entity_id)

    if entity_entry is None:
        _LOGGER.error("ZHA entity %s not found in registry", zha_entity_id)
        return

    # Create the calibration button
    async_add_entities(
        [UbisysCalibrateButton(hass, config_entry, zha_entity_id, shade_type, entity_entry)],
        True,
    )


class UbisysCalibrateButton(ButtonEntity):
    """Representation of a Ubisys calibration button."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:tune-vertical"

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        zha_entity_id: str,
        shade_type: str,
        entity_entry: er.RegistryEntry,
    ) -> None:
        """Initialize the Ubisys calibration button."""
        self.hass = hass
        self._config_entry = config_entry
        self._zha_entity_id = zha_entity_id
        self._shade_type = shade_type
        self._entity_entry = entity_entry

        # Set unique ID based on ZHA entity unique ID
        self._attr_unique_id = f"{entity_entry.unique_id}_ubisys_calibrate"

        # Set device info to link to the same device as cover entity
        self._attr_device_info = {
            "identifiers": entity_entry.device_id and {(DOMAIN, entity_entry.device_id)},
        }

        # Set name
        self._attr_name = "Calibrate"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return entity specific state attributes."""
        return {
            "shade_type": self._shade_type,
            "zha_entity_id": self._zha_entity_id,
        }

    async def async_press(self) -> None:
        """Handle the button press - trigger calibration."""
        _LOGGER.info(
            "Calibration button pressed for %s (ZHA entity: %s, shade type: %s)",
            self.entity_id,
            self._zha_entity_id,
            self._shade_type,
        )

        # Call the calibration python_script
        await self.hass.services.async_call(
            "python_script",
            "ubisys_j1_calibrate",
            {
                "entity_id": self._zha_entity_id,
                "shade_type": self._shade_type,
            },
            blocking=False,
        )

        _LOGGER.info("Calibration started for %s", self._zha_entity_id)
