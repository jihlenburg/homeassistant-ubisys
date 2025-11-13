"""Tests for Ubisys cover/light wrapper platforms using lightweight HA fakes."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, Dict, Iterable, Mapping
from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.ubisys import cover as cover_mod
from custom_components.ubisys import light as light_mod
from custom_components.ubisys import sensor as sensor_mod
from custom_components.ubisys import switch as switch_mod
from custom_components.ubisys.const import (
    ATTR_INPUT_NUMBER,
    ATTR_PRESS_TYPE,
    SIGNAL_INPUT_EVENT,
)


class DummyStates:
    def __init__(self) -> None:
        self._states: Dict[str, SimpleNamespace] = {}

    def get(self, entity_id: str) -> SimpleNamespace | None:
        return self._states.get(entity_id)

    async def async_set(
        self, entity_id: str, state: str, attributes: Mapping[str, Any] | None = None
    ) -> None:
        self._states[entity_id] = SimpleNamespace(
            state=state, attributes=dict(attributes or {})
        )


class DummyHass(SimpleNamespace):
    def __init__(self) -> None:
        super().__init__()
        self.states = DummyStates()
        self.services = SimpleNamespace(async_call=AsyncMock())
        self.data: Dict[str, Any] = {}

    def async_create_task(self, coro: Any) -> Any:
        # For these tests we don't need to schedule background work.
        return coro


@pytest.mark.asyncio
async def test_find_zha_cover_entity_returns_first_match(monkeypatch):
    fake_registry = object()
    entry = SimpleNamespace(platform="zha", domain="cover", entity_id="cover.zha_node")

    monkeypatch.setattr(
        "custom_components.ubisys.cover.er.async_get",
        lambda hass: fake_registry,
    )
    monkeypatch.setattr(
        "custom_components.ubisys.cover.er.async_entries_for_device",
        lambda registry, device_id: [entry],
    )

    hass = DummyHass()
    result = await cover_mod._find_zha_cover_entity(hass, "device-1")
    assert result == "cover.zha_node"


@pytest.mark.asyncio
async def test_ubisys_cover_syncs_state_and_delegates(monkeypatch):
    hass = DummyHass()
    hass.states._states["cover.zha_test"] = SimpleNamespace(
        state="open",
        attributes={
            "is_opening": True,
            "is_closing": False,
            "current_position": 70,
            "current_tilt_position": 30,
        },
    )

    entity = cover_mod.UbisysCover(
        hass=hass,
        config_entry=SimpleNamespace(data={}),
        zha_entity_id="cover.zha_test",
        device_ieee="00:11",
        shade_type="venetian",
    )
    entity.hass = hass
    entity.async_write_ha_state = MagicMock()

    await entity._sync_state_from_zha()
    assert entity._attr_is_closed is False
    assert entity._attr_current_cover_position == 70
    assert entity._attr_current_cover_tilt_position == 30
    entity.async_write_ha_state.assert_called_once()

    # Cover commands proxy to underlying ZHA services
    await entity.async_open_cover()
    hass.services.async_call.assert_awaited_with(
        "cover", "open_cover", {"entity_id": "cover.zha_test"}, blocking=True
    )
    hass.services.async_call.reset_mock()

    await entity.async_set_cover_position(position=42)
    hass.services.async_call.assert_awaited_with(
        "cover",
        "set_cover_position",
        {"entity_id": "cover.zha_test", "position": 42},
        blocking=True,
    )
    hass.services.async_call.reset_mock()

    await entity.async_open_cover_tilt()
    hass.services.async_call.assert_awaited_with(
        "cover", "open_cover_tilt", {"entity_id": "cover.zha_test"}, blocking=True
    )


@pytest.mark.asyncio
async def test_cover_tilt_methods_skip_when_not_supported():
    hass = DummyHass()
    entity = cover_mod.UbisysCover(
        hass=hass,
        config_entry=SimpleNamespace(data={}),
        zha_entity_id="cover.zha_roller",
        device_ieee="00:22",
        shade_type="roller",
    )
    entity.hass = hass

    await entity.async_open_cover_tilt()
    await entity.async_set_cover_tilt_position(position=10)
    # No service calls should be made because roller shades have no tilt features.
    hass.services.async_call.assert_not_awaited()


@pytest.mark.asyncio
async def test_find_zha_light_entity_returns_match(monkeypatch):
    fake_registry = object()
    entry = SimpleNamespace(platform="zha", domain="light", entity_id="light.zha_node")

    monkeypatch.setattr(
        "custom_components.ubisys.light.er.async_get",
        lambda hass: fake_registry,
    )
    monkeypatch.setattr(
        "custom_components.ubisys.light.er.async_entries_for_device",
        lambda registry, device_id: [entry],
    )

    hass = SimpleNamespace(data={})
    result = await light_mod._find_zha_light_entity(hass, "device-1")
    assert result == "light.zha_node"


@pytest.mark.asyncio
async def test_ubisys_light_syncs_state_and_delegates():
    hass = DummyHass()
    hass.states._states["light.zha_test"] = SimpleNamespace(
        state="on",
        attributes={"brightness": 123},
    )

    entity = light_mod.UbisysLight(
        hass=hass,
        config_entry=SimpleNamespace(data={"model": "D1"}),
        zha_entity_id="light.zha_test",
        device_ieee="00:33",
        model="D1",
    )
    entity.hass = hass
    entity.async_write_ha_state = MagicMock()

    await entity._sync_state_from_zha()
    assert entity._attr_is_on is True
    assert entity._attr_brightness == 123
    entity.async_write_ha_state.assert_called_once()

    await entity.async_turn_on(brightness=200, transition=1.5)
    hass.services.async_call.assert_awaited_with(
        "light",
        "turn_on",
        {"entity_id": "light.zha_test", "brightness": 200, "transition": 1.5},
        blocking=True,
    )
    hass.services.async_call.reset_mock()

    await entity.async_turn_off(transition=2)
    hass.services.async_call.assert_awaited_with(
        "light",
        "turn_off",
        {"entity_id": "light.zha_test", "transition": 2},
        blocking=True,
    )


@pytest.mark.asyncio
async def test_find_zha_switch_entity_returns_match(monkeypatch):
    fake_registry = object()
    entry = SimpleNamespace(
        platform="zha", domain="switch", entity_id="switch.zha_node"
    )

    monkeypatch.setattr(
        "custom_components.ubisys.switch.er.async_get",
        lambda hass: fake_registry,
    )
    monkeypatch.setattr(
        "custom_components.ubisys.switch.er.async_entries_for_device",
        lambda registry, device_id: [entry],
    )

    hass = SimpleNamespace()
    result = await switch_mod._find_zha_switch_entity(hass, "device-1")
    assert result == "switch.zha_node"


@pytest.mark.asyncio
async def test_ubisys_switch_syncs_state_and_delegates():
    hass = DummyHass()
    hass.states._states["switch.zha_test"] = SimpleNamespace(state="on")

    entity = switch_mod.UbisysSwitch(
        hass=hass,
        config_entry=SimpleNamespace(data={}),
        zha_entity_id="switch.zha_test",
        device_ieee="00:44",
    )
    entity.hass = hass
    entity.async_write_ha_state = MagicMock()

    await entity._sync_state_from_zha()
    assert entity._attr_is_on is True
    entity.async_write_ha_state.assert_called_once()

    await entity.async_turn_off()
    hass.services.async_call.assert_awaited_with(
        "switch", "turn_off", {"entity_id": "switch.zha_test"}, blocking=True
    )
    hass.services.async_call.reset_mock()
    await entity.async_turn_on()
    hass.services.async_call.assert_awaited_with(
        "switch", "turn_on", {"entity_id": "switch.zha_test"}, blocking=True
    )


@pytest.mark.asyncio
async def test_last_input_event_sensor_updates_history(monkeypatch):
    hass = DummyHass()
    callbacks: dict[str, object] = {}

    def fake_connect(hass_arg, signal, callback):
        callbacks[signal] = callback

        def _unsubscribe():
            callbacks.pop(signal, None)

        return _unsubscribe

    monkeypatch.setattr(
        "custom_components.ubisys.sensor.async_dispatcher_connect",
        fake_connect,
    )

    entry = SimpleNamespace(data={"device_id": "device-99"})
    sensor = sensor_mod.UbisysLastInputEventSensor(hass, entry, "00:55")
    sensor.entity_id = "sensor.last_input_event"
    sensor.async_write_ha_state = MagicMock()

    await sensor.async_added_to_hass()

    signal = f"{SIGNAL_INPUT_EVENT}_{entry.data['device_id']}"
    callbacks[signal](
        {
            ATTR_INPUT_NUMBER: 0,
            ATTR_PRESS_TYPE: "short_press",
            "device_ieee": "00:55",
            "model": "D1",
            "command": {"endpoint": 2},
        }
    )

    assert sensor.native_value is not None
    assert sensor.extra_state_attributes["last"]["press"] == "short_press"
    assert sensor.extra_state_attributes["history"]

    await sensor.async_will_remove_from_hass()
    assert not callbacks
