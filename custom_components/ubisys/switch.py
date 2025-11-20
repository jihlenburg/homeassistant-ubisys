"""Switch platform for Ubisys Zigbee integration.

Wrapper around ZHA switch entity to attach Ubisys metadata and maintain
stable entity IDs. Delegates operations to the underlying ZHA entity.
"""

from __future__ import annotations

import logging
from typing import Any, cast

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_state_change_event

from .const import CONF_DEVICE_ID, CONF_DEVICE_IEEE, DOMAIN
from .ha_typing import callback as _typed_callback
from .helpers import is_verbose_info_logging

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Ubisys switch from config entry."""
    device_ieee = config_entry.data[CONF_DEVICE_IEEE]
    device_id = config_entry.data[CONF_DEVICE_ID]
    model = config_entry.data.get("model", "S1")

    # Only create switch entities for S1/S1-R switch models
    # J1 devices are covers, D1 devices are lights
    from .const import SWITCH_MODELS

    if model not in SWITCH_MODELS:
        _LOGGER.debug(
            "Skipping switch entity for non-switch device: model=%s (ieee=%s)",
            model,
            device_ieee,
        )
        return

    # Find the ZHA switch entity (or predict entity ID if not found yet)
    zha_entity_id = await _find_zha_switch_entity(hass, device_id, device_ieee)

    # Note: ZHA entity auto-enable is handled centrally in __init__.py

    _LOGGER.log(
        logging.INFO if is_verbose_info_logging(hass) else logging.DEBUG,
        "Creating Ubisys switch wrapper for %s (ZHA entity: %s)",
        device_ieee,
        zha_entity_id,
    )

    switch = UbisysSwitch(
        hass=hass,
        config_entry=config_entry,
        zha_entity_id=zha_entity_id,
        device_ieee=device_ieee,
    )
    async_add_entities([switch])


async def _find_zha_switch_entity(
    hass: HomeAssistant, device_id: str, device_ieee: str
) -> str:
    """Find the ZHA switch entity for a device.

    If the ZHA entity doesn't exist yet (e.g., during startup race condition),
    this function predicts the entity ID. The wrapper entity will mark itself
    as unavailable and automatically recover when ZHA creates its entity.

    Args:
        hass: Home Assistant instance
        device_id: Device registry ID
        device_ieee: Device IEEE address for logging and prediction

    Returns:
        ZHA switch entity ID (either found or predicted)
    """
    entity_registry = er.async_get(hass)
    entities = er.async_entries_for_device(entity_registry, device_id)

    for entry in entities:
        if entry.platform == "zha" and entry.domain == "switch":
            _LOGGER.debug(
                "Found ZHA switch entity %s for device %s",
                entry.entity_id,
                device_ieee,
            )
            return cast(str, entry.entity_id)

    # ZHA entity not found - predict entity ID
    # This handles startup race condition where Ubisys loads before ZHA
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

    predicted_entity_id = f"switch.{predicted_name}"

    _LOGGER.warning(
        "ZHA switch entity not found for device %s (%s). "
        "Predicting entity ID as %s. "
        "Wrapper entity will be unavailable until ZHA entity appears.",
        device_id,
        device_ieee,
        predicted_entity_id,
    )

    return predicted_entity_id


class UbisysSwitch(SwitchEntity):
    """Wrapper switch entity that delegates to ZHA switch entity."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        zha_entity_id: str,
        device_ieee: str,
    ) -> None:
        self.hass = hass
        self._config_entry = config_entry
        self._zha_entity_id = zha_entity_id
        self._device_ieee = device_ieee
        self._attr_unique_id = f"{device_ieee}_switch"
        self._attr_device_info = {"identifiers": {(DOMAIN, device_ieee)}}
        self._attr_is_on: bool | None = None

        # ZHA entity availability tracking (for graceful degradation)
        # This allows wrapper entity to handle startup race conditions
        # where ZHA hasn't created its entity yet
        self._zha_entity_available = False

        _LOGGER.debug(
            "Initialized UbisysSwitch: ieee=%s, zha_entity=%s",
            device_ieee,
            zha_entity_id,
        )

    async def async_added_to_hass(self) -> None:
        await self._sync_state_from_zha()
        self.async_on_remove(
            async_track_state_change_event(
                self.hass, [self._zha_entity_id], self._handle_zha_state_change
            )
        )

    @_typed_callback
    def _handle_zha_state_change(self, event: object) -> None:
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

        self._attr_is_on = zha_state.state == "on"
        self.async_write_ha_state()

    @property
    def available(self) -> bool:
        """Return if entity is available.

        Wrapper entity is only available when the underlying ZHA entity exists
        and is available. This handles startup race conditions where Ubisys loads
        before ZHA has created its switch entity.

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
        """Return entity-specific state attributes."""
        attrs = {
            "zha_entity_id": self._zha_entity_id,
            "integration": "ubisys",
        }

        # Add availability info for debugging
        if not self._zha_entity_available:
            attrs["unavailable_reason"] = "ZHA entity not found or unavailable"

        return attrs

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.hass.services.async_call(
            "switch", "turn_on", {"entity_id": self._zha_entity_id}, blocking=True
        )

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.hass.services.async_call(
            "switch", "turn_off", {"entity_id": self._zha_entity_id}, blocking=True
        )
