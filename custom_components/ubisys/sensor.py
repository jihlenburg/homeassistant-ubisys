"""Sensor platform for Ubisys: last input event timestamp/details.

Creates one sensor per device that updates when a physical input event occurs.
Useful for UX and diagnostics (e.g., visible in UI).
"""

from __future__ import annotations

import datetime as dt
import logging
from typing import Any, Deque
from collections import deque

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, SIGNAL_INPUT_EVENT, CONF_DEVICE_IEEE

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    device_ieee = config_entry.data[CONF_DEVICE_IEEE]

    sensor = UbisysLastInputEventSensor(hass, config_entry, device_ieee)
    async_add_entities([sensor])


class UbisysLastInputEventSensor(SensorEntity):
    """Shows the last physical input event time for a Ubisys device."""

    _attr_has_entity_name = True
    _attr_name = "Last Input Event"
    _attr_icon = "mdi:clock-outline"

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, device_ieee: str) -> None:
        self.hass = hass
        self._entry = entry
        self._device_ieee = device_ieee
        self._device_id = entry.data.get("device_id")
        self._attr_unique_id = f"{device_ieee}_last_input"
        self._attr_device_info = {"identifiers": {(DOMAIN, device_ieee)}}
        self._attr_extra_state_attributes = {}
        self._history: Deque[dict[str, Any]] = deque(maxlen=10)
        self._unsubscribe: Any | None = None

    async def async_added_to_hass(self) -> None:
        # Subscribe to per-device dispatcher signal from input_monitor
        signal = f"{SIGNAL_INPUT_EVENT}_{self._device_id}"

        @callback
        def _handle_event(event_data: dict[str, Any]) -> None:
            # Update state to current UTC ISO; keep rich attributes for UX
            now = dt.datetime.now(dt.timezone.utc).isoformat()
            self._attr_native_value = now
            summary = {
                "ts": now,
                "input": event_data.get("input_number"),
                "press": event_data.get("press_type"),
                "cmd": event_data.get("command"),
            }
            self._history.appendleft(summary)
            self._attr_extra_state_attributes = {
                "device_ieee": event_data.get("device_ieee"),
                "model": event_data.get("model"),
                "last": summary,
                "history": list(self._history),
            }
            self.async_write_ha_state()

        self._unsubscribe = async_dispatcher_connect(self.hass, signal, _handle_event)

    async def async_will_remove_from_hass(self) -> None:
        if self._unsubscribe:
            self._unsubscribe()
            self._unsubscribe = None
