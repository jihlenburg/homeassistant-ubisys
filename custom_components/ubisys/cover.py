"""Cover platform for Ubisys Zigbee integration.

This module provides wrapper cover entities that delegate to ZHA cover entities
while filtering features based on shade type.
"""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.cover import (
    ATTR_POSITION,
    ATTR_TILT_POSITION,
    CoverEntity,
    CoverEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_state_change_event

from .const import (
    CONF_DEVICE_ID,
    CONF_DEVICE_IEEE,
    CONF_SHADE_TYPE,
    DOMAIN,
    SHADE_TYPE_TO_FEATURES,
)
from .helpers import is_verbose_info_logging

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Ubisys cover from config entry."""
    device_ieee = config_entry.data[CONF_DEVICE_IEEE]
    device_id = config_entry.data[CONF_DEVICE_ID]
    shade_type = config_entry.data[CONF_SHADE_TYPE]

    # Find the ZHA cover entity
    zha_entity_id = await _find_zha_cover_entity(hass, device_id)

    if not zha_entity_id:
        _LOGGER.error(
            "Could not find ZHA cover entity for device %s (%s)",
            device_id,
            device_ieee,
        )
        return

    _LOGGER.log(
        logging.INFO if is_verbose_info_logging(hass) else logging.DEBUG,
        "Creating Ubisys cover wrapper for %s (ZHA entity: %s, shade type: %s)",
        device_ieee,
        zha_entity_id,
        shade_type,
    )

    # Create wrapper entity
    cover = UbisysCover(
        hass=hass,
        config_entry=config_entry,
        zha_entity_id=zha_entity_id,
        device_ieee=device_ieee,
        shade_type=shade_type,
    )

    async_add_entities([cover])


async def _find_zha_cover_entity(hass: HomeAssistant, device_id: str) -> str | None:
    """Find the ZHA cover entity for a device."""
    entity_registry = er.async_get(hass)

    # Find all entities for this device
    entities = er.async_entries_for_device(entity_registry, device_id)

    for entity_entry in entities:
        if entity_entry.platform == "zha" and entity_entry.domain == "cover":
            return entity_entry.entity_id

    return None


class UbisysCover(CoverEntity):
    """Wrapper cover entity that delegates to ZHA with filtered features."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        zha_entity_id: str,
        device_ieee: str,
        shade_type: str,
    ) -> None:
        """Initialize the Ubisys cover."""
        self.hass = hass
        self._config_entry = config_entry
        self._zha_entity_id = zha_entity_id
        self._device_ieee = device_ieee
        self._shade_type = shade_type

        # Set unique ID
        self._attr_unique_id = f"{device_ieee}_cover"

        # Set device info
        self._attr_device_info = {
            "identifiers": {(DOMAIN, device_ieee)},
        }

        # Set filtered features based on shade type
        self._attr_supported_features = SHADE_TYPE_TO_FEATURES.get(
            shade_type, CoverEntityFeature(0)
        )

        # State tracking
        self._attr_is_closed: bool | None = None
        self._attr_is_closing: bool | None = None
        self._attr_is_opening: bool | None = None
        self._attr_current_cover_position: int | None = None
        self._attr_current_cover_tilt_position: int | None = None

        _LOGGER.debug(
            "Initialized UbisysCover: ieee=%s, zha_entity=%s, shade_type=%s, features=%s",
            device_ieee,
            zha_entity_id,
            shade_type,
            self._attr_supported_features,
        )

    async def async_added_to_hass(self) -> None:
        """Run when entity is added to hass."""
        # Initial state sync
        await self._sync_state_from_zha()

        # Track ZHA entity state changes
        self.async_on_remove(
            async_track_state_change_event(
                self.hass, [self._zha_entity_id], self._handle_zha_state_change
            )
        )

    @callback
    def _handle_zha_state_change(self, event: Any) -> None:
        """Handle ZHA entity state change."""
        self.hass.async_create_task(self._sync_state_from_zha())

    async def _sync_state_from_zha(self) -> None:
        """Sync state from ZHA entity."""
        zha_state = self.hass.states.get(self._zha_entity_id)

        if zha_state is None:
            _LOGGER.warning(
                "ZHA entity %s not found for sync",
                self._zha_entity_id,
            )
            return

        # Update state attributes
        self._attr_is_closed = zha_state.state == "closed"
        self._attr_is_closing = zha_state.attributes.get("is_closing")
        self._attr_is_opening = zha_state.attributes.get("is_opening")
        self._attr_current_cover_position = zha_state.attributes.get(
            "current_position"
        )
        self._attr_current_cover_tilt_position = zha_state.attributes.get(
            "current_tilt_position"
        )

        self.async_write_ha_state()

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return entity specific state attributes."""
        return {
            "shade_type": self._shade_type,
            "zha_entity_id": self._zha_entity_id,
            "integration": "ubisys",
        }

    async def async_open_cover(self, **kwargs: Any) -> None:
        """Open the cover."""
        _LOGGER.debug("Opening cover via ZHA entity: %s", self._zha_entity_id)
        await self.hass.services.async_call(
            "cover",
            "open_cover",
            {"entity_id": self._zha_entity_id},
            blocking=True,
        )

    async def async_close_cover(self, **kwargs: Any) -> None:
        """Close the cover."""
        _LOGGER.debug("Closing cover via ZHA entity: %s", self._zha_entity_id)
        await self.hass.services.async_call(
            "cover",
            "close_cover",
            {"entity_id": self._zha_entity_id},
            blocking=True,
        )

    async def async_stop_cover(self, **kwargs: Any) -> None:
        """Stop the cover."""
        _LOGGER.debug("Stopping cover via ZHA entity: %s", self._zha_entity_id)
        await self.hass.services.async_call(
            "cover",
            "stop_cover",
            {"entity_id": self._zha_entity_id},
            blocking=True,
        )

    async def async_set_cover_position(self, **kwargs: Any) -> None:
        """Move the cover to a specific position."""
        position = kwargs.get(ATTR_POSITION)
        _LOGGER.debug(
            "Setting cover position to %s via ZHA entity: %s",
            position,
            self._zha_entity_id,
        )
        await self.hass.services.async_call(
            "cover",
            "set_cover_position",
            {"entity_id": self._zha_entity_id, ATTR_POSITION: position},
            blocking=True,
        )

    async def async_open_cover_tilt(self, **kwargs: Any) -> None:
        """Open the cover tilt."""
        if not (
            self._attr_supported_features & CoverEntityFeature.OPEN_TILT
        ):
            _LOGGER.warning(
                "Open tilt not supported for shade type: %s", self._shade_type
            )
            return

        _LOGGER.debug("Opening cover tilt via ZHA entity: %s", self._zha_entity_id)
        await self.hass.services.async_call(
            "cover",
            "open_cover_tilt",
            {"entity_id": self._zha_entity_id},
            blocking=True,
        )

    async def async_close_cover_tilt(self, **kwargs: Any) -> None:
        """Close the cover tilt."""
        if not (
            self._attr_supported_features & CoverEntityFeature.CLOSE_TILT
        ):
            _LOGGER.warning(
                "Close tilt not supported for shade type: %s", self._shade_type
            )
            return

        _LOGGER.debug("Closing cover tilt via ZHA entity: %s", self._zha_entity_id)
        await self.hass.services.async_call(
            "cover",
            "close_cover_tilt",
            {"entity_id": self._zha_entity_id},
            blocking=True,
        )

    async def async_stop_cover_tilt(self, **kwargs: Any) -> None:
        """Stop the cover tilt."""
        if not (
            self._attr_supported_features & CoverEntityFeature.STOP_TILT
        ):
            _LOGGER.warning(
                "Stop tilt not supported for shade type: %s", self._shade_type
            )
            return

        _LOGGER.debug("Stopping cover tilt via ZHA entity: %s", self._zha_entity_id)
        await self.hass.services.async_call(
            "cover",
            "stop_cover_tilt",
            {"entity_id": self._zha_entity_id},
            blocking=True,
        )

    async def async_set_cover_tilt_position(self, **kwargs: Any) -> None:
        """Move the cover tilt to a specific position."""
        if not (
            self._attr_supported_features & CoverEntityFeature.SET_TILT_POSITION
        ):
            _LOGGER.warning(
                "Set tilt position not supported for shade type: %s", self._shade_type
            )
            return

        tilt_position = kwargs.get(ATTR_TILT_POSITION)
        _LOGGER.debug(
            "Setting cover tilt position to %s via ZHA entity: %s",
            tilt_position,
            self._zha_entity_id,
        )
        await self.hass.services.async_call(
            "cover",
            "set_cover_tilt_position",
            {
                "entity_id": self._zha_entity_id,
                ATTR_TILT_POSITION: tilt_position,
            },
            blocking=True,
        )
