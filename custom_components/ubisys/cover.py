"""Cover platform for Ubisys Zigbee integration.

This module provides wrapper cover entities that delegate to ZHA cover entities
while filtering features based on shade type.
"""

from __future__ import annotations

import logging
from typing import Any, cast

from homeassistant.components.cover import (
    ATTR_POSITION,
    ATTR_TILT_POSITION,
    CoverEntity,
    CoverEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
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
from .ha_typing import callback as _typed_callback
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

    # Get shade_type from options (preferred) or data (fallback)
    # Default to "roller" if missing (for backward compatibility with older config entries)
    shade_type = config_entry.options.get(
        CONF_SHADE_TYPE, config_entry.data.get(CONF_SHADE_TYPE, "roller")
    )
    model = config_entry.data.get("model", "J1")

    # Only create cover entities for J1/J1-R window covering models
    # D1 devices are lights, S1 devices are switches
    from .const import WINDOW_COVERING_MODELS

    if model not in WINDOW_COVERING_MODELS:
        _LOGGER.debug(
            "Skipping cover entity for non-window-covering device: model=%s (ieee=%s)",
            model,
            device_ieee,
        )
        return

    # Find the ZHA cover entity (or predict entity ID if not found yet)
    zha_entity_id = await _find_zha_cover_entity(hass, device_id, device_ieee)

    # Note: ZHA entity auto-enable is now handled centrally in __init__.py
    # via _ensure_zha_entity_enabled() after _hide_zha_entity()
    # This architectural change (v1.3.5) centralizes the logic instead of
    # duplicating it across cover/light/switch platforms

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


async def _find_zha_cover_entity(
    hass: HomeAssistant, device_id: str, device_ieee: str
) -> str:
    """Find the ZHA cover entity for a device.

    If the ZHA entity doesn't exist yet (e.g., during startup race condition),
    this function predicts the entity ID. The wrapper entity will mark itself
    as unavailable and automatically recover when ZHA creates its entity.

    Args:
        hass: Home Assistant instance
        device_id: Device registry ID
        device_ieee: Device IEEE address for logging and prediction

    Returns:
        ZHA cover entity ID (either found or predicted)
    """
    entity_registry = er.async_get(hass)

    # Find all entities for this device
    entities = er.async_entries_for_device(entity_registry, device_id)

    for entity_entry in entities:
        if entity_entry.platform == "zha" and entity_entry.domain == "cover":
            _LOGGER.debug(
                "Found ZHA cover entity %s for device %s",
                entity_entry.entity_id,
                device_ieee,
            )
            return cast(str, entity_entry.entity_id)

    # ZHA entity not found - predict entity ID
    # This handles startup race condition where Ubisys loads before ZHA
    # ZHA typically creates entity IDs like: cover.{device_name}
    # We'll use the IEEE as fallback for prediction
    from homeassistant.helpers import device_registry as dr

    device_registry = dr.async_get(hass)
    device = device_registry.async_get(device_id)

    if device and device.name_by_user:
        predicted_name = device.name_by_user.lower().replace(" ", "_")
    elif device and device.name:
        predicted_name = device.name.lower().replace(" ", "_")
    else:
        # Fallback: use IEEE address
        predicted_name = f"ubisys_{device_ieee.replace(':', '_')}"

    predicted_entity_id = f"cover.{predicted_name}"

    _LOGGER.warning(
        "ZHA cover entity not found for device %s (%s). "
        "Predicting entity ID as %s. "
        "Wrapper entity will be unavailable until ZHA entity appears.",
        device_id,
        device_ieee,
        predicted_entity_id,
    )

    return predicted_entity_id


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

        # ZHA entity availability tracking (for graceful degradation)
        # This allows wrapper entity to handle startup race conditions
        # where ZHA hasn't created its entity yet
        self._zha_entity_available = False

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

        # Note: Entity registry listener removed in v1.3.5
        # Auto-enable logic now centralized in __init__.py

    @_typed_callback
    def _handle_zha_state_change(self, event: object) -> None:
        """Handle ZHA entity state change."""
        self.hass.async_create_task(self._sync_state_from_zha())

    async def _sync_state_from_zha(self) -> None:
        """Sync state from ZHA entity.

        Handles graceful degradation when ZHA entity doesn't exist yet
        (startup race condition) or becomes unavailable.
        """
        zha_state = self.hass.states.get(self._zha_entity_id)

        if zha_state is None:
            # ZHA entity not found - handle gracefully
            if self._zha_entity_available:
                # Entity was available before, now it's gone
                _LOGGER.warning(
                    "ZHA entity %s disappeared for device %s",
                    self._zha_entity_id,
                    self._device_ieee,
                )
            else:
                # Entity never existed (likely startup race condition)
                _LOGGER.debug(
                    "ZHA entity %s not found for sync (device: %s). "
                    "Wrapper will be unavailable until ZHA entity appears.",
                    self._zha_entity_id,
                    self._device_ieee,
                )

            self._zha_entity_available = False
            self.async_write_ha_state()
            return

        # ZHA entity exists - check if it just appeared
        if not self._zha_entity_available:
            _LOGGER.info(
                "ZHA entity %s became available for device %s. "
                "Wrapper entity is now operational.",
                self._zha_entity_id,
                self._device_ieee,
            )
            self._zha_entity_available = True

        # Update state attributes from ZHA entity
        self._attr_is_closed = zha_state.state == "closed"
        self._attr_is_closing = zha_state.attributes.get("is_closing")
        self._attr_is_opening = zha_state.attributes.get("is_opening")
        self._attr_current_cover_position = zha_state.attributes.get("current_position")
        self._attr_current_cover_tilt_position = zha_state.attributes.get(
            "current_tilt_position"
        )

        self.async_write_ha_state()

    @property
    def available(self) -> bool:
        """Return if entity is available.

        Wrapper entity is only available when the underlying ZHA entity exists
        and is available. This handles startup race conditions where Ubisys loads
        before ZHA has created its cover entity.

        Returns:
            True if ZHA entity exists and is available, False otherwise
        """
        zha_state = self.hass.states.get(self._zha_entity_id)

        if zha_state is None:
            # ZHA entity doesn't exist yet (startup race condition)
            return False

        # Check if ZHA entity is available (not unavailable/unknown)
        from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN

        if zha_state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            return False

        return True

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return entity specific state attributes."""
        attrs = {
            "shade_type": self._shade_type,
            "zha_entity_id": self._zha_entity_id,
            "integration": "ubisys",
        }

        # Add availability info for debugging
        if not self._zha_entity_available:
            attrs["unavailable_reason"] = "ZHA entity not found or unavailable"

        return attrs

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
        if not (self._attr_supported_features & CoverEntityFeature.OPEN_TILT):
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
        if not (self._attr_supported_features & CoverEntityFeature.CLOSE_TILT):
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
        if not (self._attr_supported_features & CoverEntityFeature.STOP_TILT):
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
        if not (self._attr_supported_features & CoverEntityFeature.SET_TILT_POSITION):
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
