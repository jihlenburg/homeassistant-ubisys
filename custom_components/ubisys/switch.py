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

    # Find the ZHA switch entity
    zha_entity_id = await _find_zha_switch_entity(hass, device_id)
    if not zha_entity_id:
        _LOGGER.error(
            "Could not find ZHA switch entity for device %s (%s)",
            device_id,
            device_ieee,
        )
        return

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


async def _find_zha_switch_entity(hass: HomeAssistant, device_id: str) -> str | None:
    """Find the ZHA switch entity for a device."""
    entity_registry = er.async_get(hass)
    entities = er.async_entries_for_device(entity_registry, device_id)
    for entry in entities:
        if entry.platform == "zha" and entry.domain == "switch":
            return cast(str, entry.entity_id)
    return None


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
        zha_state = self.hass.states.get(self._zha_entity_id)
        if not zha_state:
            _LOGGER.warning("ZHA entity %s not found for sync", self._zha_entity_id)
            return
        self._attr_is_on = zha_state.state == "on"
        self.async_write_ha_state()

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.hass.services.async_call(
            "switch", "turn_on", {"entity_id": self._zha_entity_id}, blocking=True
        )

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.hass.services.async_call(
            "switch", "turn_off", {"entity_id": self._zha_entity_id}, blocking=True
        )
