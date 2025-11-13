"""Tests for Ubisys input monitoring stack."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.ubisys import input_monitor
from custom_components.ubisys.const import (
    ATTR_INPUT_NUMBER,
    ATTR_PRESS_TYPE,
    DOMAIN,
    EVENT_UBISYS_INPUT,
)
from custom_components.ubisys.input_monitor import UbisysInputMonitor
from custom_components.ubisys.input_parser import (
    InputAction,
    PressType,
    TransitionState,
)


@pytest.mark.asyncio
async def test_input_monitor_reads_actions_and_fires_events(hass_full, monkeypatch):
    """UbisysInputMonitor should read InputActions and emit correlated events."""
    hass = hass_full

    fake_cluster = MagicMock()
    fake_cluster.read_attributes = AsyncMock(
        return_value=[{input_monitor.INPUT_ACTIONS_ATTR_ID: b"\x00"}]
    )
    monkeypatch.setattr(
        "custom_components.ubisys.input_monitor.get_device_setup_cluster",
        AsyncMock(return_value=fake_cluster),
    )

    action = InputAction(
        input_number=0,
        input_options=0,
        transition=0,
        initial_state=TransitionState.PRESSED,
        final_state=TransitionState.RELEASED,
        has_alternate=False,
        is_alternate=False,
        source_endpoint=2,
        cluster_id=0x0006,
        command_id=1,
        command_payload=b"",
        press_type=PressType.SHORT_PRESS,
    )
    monkeypatch.setattr(
        "custom_components.ubisys.input_monitor.InputActionsParser.parse",
        lambda raw: [action],
    )

    events: list = []
    hass.bus.async_listen(EVENT_UBISYS_INPUT, lambda event: events.append(event))

    monitor = UbisysInputMonitor(hass, "00:11", "D1", "device-1")
    await monitor.async_start()

    hass.bus.async_fire(
        "zha_event",
        {
            "device_ieee": "00:11",
            "endpoint_id": 2,
            "cluster_id": 0x0006,
            "command": 1,
            "args": [],
        },
    )
    await hass.async_block_till_done()

    assert events, "Expected ubisys input event"
    assert events[0].data[ATTR_PRESS_TYPE] == "short_press"
    assert events[0].data[ATTR_INPUT_NUMBER] == 0

    await monitor.async_stop()
    assert monitor._started is False


@pytest.mark.asyncio
async def test_async_setup_input_monitoring_creates_monitors(monkeypatch):
    """Ensure async_setup_input_monitoring instantiates monitors for supported devices."""
    hass = SimpleNamespace(data={})

    def make_device(identifier: str, model: str) -> SimpleNamespace:
        return SimpleNamespace(
            id=f"device-{identifier}",
            name=f"Device {identifier}",
            model=f"{model} (5502)",
            identifiers={("zha", f"00:{identifier}")},
        )

    devices = [make_device("11", "D1"), make_device("22", "Unknown")]

    registry = SimpleNamespace()
    monkeypatch.setattr(
        "custom_components.ubisys.input_monitor.dr.async_get",
        lambda hass_arg: registry,
    )
    monkeypatch.setattr(
        "custom_components.ubisys.input_monitor.dr.async_entries_for_config_entry",
        lambda reg, entry_id: devices,
    )

    created = []

    class FakeMonitor:
        def __init__(self, hass_arg, ieee, model, device_id):
            self.hass = hass_arg
            self.ieee = ieee
            self.model = model
            self.device_id = device_id

        async def async_start(self):
            created.append(self)

    monkeypatch.setattr(
        "custom_components.ubisys.input_monitor.UbisysInputMonitor", FakeMonitor
    )

    await input_monitor.async_setup_input_monitoring(hass, "entry")

    assert len(created) == 1
    assert hass.data[DOMAIN]["input_monitors"] == created


@pytest.mark.asyncio
async def test_async_unload_input_monitoring_stops_all(monkeypatch):
    """Stored monitors should be stopped and cleared on unload."""
    hass = SimpleNamespace(data={DOMAIN: {"input_monitors": []}})

    stop_calls = []

    class DummyMonitor:
        async def async_stop(self):
            stop_calls.append(1)

    hass.data[DOMAIN]["input_monitors"] = [DummyMonitor(), DummyMonitor()]

    await input_monitor.async_unload_input_monitoring(hass)

    assert len(stop_calls) == 2
    assert "input_monitors" not in hass.data[DOMAIN]


def test_handle_controller_command_generic_fallback(monkeypatch):
    """When no InputActions match, the monitor should fire a generic pressed event."""
    hass = SimpleNamespace(
        bus=SimpleNamespace(async_fire=lambda *args, **kwargs: None),
    )
    monitor = UbisysInputMonitor(hass, "00:AA", "D1", "device-x")
    monitor._controller_endpoints = [2]
    monitor._registry = MagicMock()
    monitor._registry.lookup.return_value = None
    fired = {}
    monitor._fire_input_event = lambda **kwargs: fired.update(kwargs)

    monitor._handle_controller_command(2, 0x0006, 1, b"")

    assert fired["press_type"] == PressType.PRESSED.value
    assert fired["input_number"] == 0
