"""Cover platform for Ubisys integration."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.cover import (
    ATTR_CURRENT_POSITION,
    ATTR_CURRENT_TILT_POSITION,
    ATTR_POSITION,
    ATTR_TILT_POSITION,
    CoverEntity,
    CoverEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_state_change_event

from .const import (
    CONF_SHADE_TYPE,
    CONF_ZHA_ENTITY_ID,
    DOMAIN,
    SHADE_TYPE_TO_FEATURES,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Ubisys cover from a config entry."""
    zha_entity_id = config_entry.data[CONF_ZHA_ENTITY_ID]
    shade_type = config_entry.data[CONF_SHADE_TYPE]

    # Get the ZHA entity
    entity_registry = er.async_get(hass)
    entity_entry = entity_registry.async_get(zha_entity_id)

    if entity_entry is None:
        _LOGGER.error("ZHA entity %s not found in registry", zha_entity_id)
        return

    # Create the wrapper entity
    async_add_entities(
        [UbisysCover(hass, config_entry, zha_entity_id, shade_type, entity_entry)],
        True,
    )


class UbisysCover(CoverEntity):
    """Representation of a Ubisys cover entity.

    This wrapper entity filters the supported features based on the shade type
    and delegates all operations to the underlying ZHA cover entity.
    """

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        zha_entity_id: str,
        shade_type: str,
        entity_entry: er.RegistryEntry,
    ) -> None:
        """Initialize the Ubisys cover."""
        self.hass = hass
        self._config_entry = config_entry
        self._zha_entity_id = zha_entity_id
        self._shade_type = shade_type
        self._entity_entry = entity_entry

        # Set supported features based on shade type
        self._attr_supported_features = SHADE_TYPE_TO_FEATURES.get(
            shade_type, CoverEntityFeature(0)
        )

        # Set unique ID based on ZHA entity unique ID
        self._attr_unique_id = f"{entity_entry.unique_id}_ubisys"

        # Set device info to link to the same device as ZHA entity
        self._attr_device_info = {
            "identifiers": entity_entry.device_id and {(DOMAIN, entity_entry.device_id)},
        }

        # Initialize state attributes
        self._attr_is_closed: bool | None = None
        self._attr_is_opening: bool | None = None
        self._attr_is_closing: bool | None = None
        self._attr_current_cover_position: int | None = None
        self._attr_current_cover_tilt_position: int | None = None
        self._attr_available = False

        # Track state changes of the underlying ZHA entity
        self._unsubscribe_state_listener = None

    async def async_added_to_hass(self) -> None:
        """Register state listener when entity is added."""
        await super().async_added_to_hass()

        # Subscribe to state changes of the ZHA entity
        self._unsubscribe_state_listener = async_track_state_change_event(
            self.hass, [self._zha_entity_id], self._async_state_changed_listener
        )

        # Set initial state
        await self._async_update_from_zha()

    async def async_will_remove_from_hass(self) -> None:
        """Unregister state listener when entity is removed."""
        if self._unsubscribe_state_listener:
            self._unsubscribe_state_listener()
            self._unsubscribe_state_listener = None
        await super().async_will_remove_from_hass()

    @callback
    def _async_state_changed_listener(self, event) -> None:
        """Handle state changes of the underlying ZHA entity."""
        self.hass.async_create_task(self._async_update_from_zha())

    async def _async_update_from_zha(self) -> None:
        """Update state from the underlying ZHA entity."""
        zha_state = self.hass.states.get(self._zha_entity_id)

        if zha_state is None or zha_state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            self._attr_available = False
        else:
            self._attr_available = True
            self._attr_is_closed = zha_state.state == "closed"
            self._attr_is_opening = zha_state.attributes.get("is_opening")
            self._attr_is_closing = zha_state.attributes.get("is_closing")
            self._attr_current_cover_position = zha_state.attributes.get(
                ATTR_CURRENT_POSITION
            )
            self._attr_current_cover_tilt_position = zha_state.attributes.get(
                ATTR_CURRENT_TILT_POSITION
            )

        self.async_write_ha_state()

    @property
    def name(self) -> str:
        """Return the name of the entity."""
        zha_state = self.hass.states.get(self._zha_entity_id)
        if zha_state:
            return f"Ubisys {zha_state.attributes.get('friendly_name', 'Cover')}"
        return "Ubisys Cover"

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
        if not (self._attr_supported_features & CoverEntityFeature.OPEN):
            _LOGGER.warning("Open operation not supported for shade type %s", self._shade_type)
            return

        await self.hass.services.async_call(
            "cover",
            "open_cover",
            {"entity_id": self._zha_entity_id},
            blocking=True,
        )

    async def async_close_cover(self, **kwargs: Any) -> None:
        """Close the cover."""
        if not (self._attr_supported_features & CoverEntityFeature.CLOSE):
            _LOGGER.warning("Close operation not supported for shade type %s", self._shade_type)
            return

        await self.hass.services.async_call(
            "cover",
            "close_cover",
            {"entity_id": self._zha_entity_id},
            blocking=True,
        )

    async def async_stop_cover(self, **kwargs: Any) -> None:
        """Stop the cover."""
        if not (self._attr_supported_features & CoverEntityFeature.STOP):
            _LOGGER.warning("Stop operation not supported for shade type %s", self._shade_type)
            return

        await self.hass.services.async_call(
            "cover",
            "stop_cover",
            {"entity_id": self._zha_entity_id},
            blocking=True,
        )

    async def async_set_cover_position(self, **kwargs: Any) -> None:
        """Move the cover to a specific position."""
        if not (self._attr_supported_features & CoverEntityFeature.SET_POSITION):
            _LOGGER.warning("Set position not supported for shade type %s", self._shade_type)
            return

        position = kwargs.get(ATTR_POSITION)
        if position is None:
            return

        await self.hass.services.async_call(
            "cover",
            "set_cover_position",
            {"entity_id": self._zha_entity_id, ATTR_POSITION: position},
            blocking=True,
        )

    async def async_open_cover_tilt(self, **kwargs: Any) -> None:
        """Open the cover tilt."""
        if not (self._attr_supported_features & CoverEntityFeature.OPEN_TILT):
            _LOGGER.warning("Open tilt not supported for shade type %s", self._shade_type)
            return

        await self.hass.services.async_call(
            "cover",
            "open_cover_tilt",
            {"entity_id": self._zha_entity_id},
            blocking=True,
        )

    async def async_close_cover_tilt(self, **kwargs: Any) -> None:
        """Close the cover tilt."""
        if not (self._attr_supported_features & CoverEntityFeature.CLOSE_TILT):
            _LOGGER.warning("Close tilt not supported for shade type %s", self._shade_type)
            return

        await self.hass.services.async_call(
            "cover",
            "close_cover_tilt",
            {"entity_id": self._zha_entity_id},
            blocking=True,
        )

    async def async_stop_cover_tilt(self, **kwargs: Any) -> None:
        """Stop the cover tilt."""
        if not (self._attr_supported_features & CoverEntityFeature.STOP_TILT):
            _LOGGER.warning("Stop tilt not supported for shade type %s", self._shade_type)
            return

        await self.hass.services.async_call(
            "cover",
            "stop_cover_tilt",
            {"entity_id": self._zha_entity_id},
            blocking=True,
        )

    async def async_set_cover_tilt_position(self, **kwargs: Any) -> None:
        """Move the cover tilt to a specific position."""
        if not (self._attr_supported_features & CoverEntityFeature.SET_TILT_POSITION):
            _LOGGER.warning("Set tilt position not supported for shade type %s", self._shade_type)
            return

        tilt_position = kwargs.get(ATTR_TILT_POSITION)
        if tilt_position is None:
            return

        await self.hass.services.async_call(
            "cover",
            "set_cover_tilt_position",
            {"entity_id": self._zha_entity_id, ATTR_TILT_POSITION: tilt_position},
            blocking=True,
        )
