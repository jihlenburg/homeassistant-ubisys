"""Tests for Ubisys device triggers."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from custom_components.ubisys import device_trigger
from custom_components.ubisys.const import ATTR_INPUT_NUMBER, ATTR_PRESS_TYPE, DOMAIN


@pytest.mark.asyncio
async def test_async_get_triggers_returns_device_buttons(monkeypatch):
    """Ensure trigger list is built from device model metadata."""
    device = SimpleNamespace(
        id="device-1",
        model="J1 (5502)",
        area_id="office",
    )
    registry = SimpleNamespace(async_get=lambda device_id: device)
    monkeypatch.setattr(
        "custom_components.ubisys.device_trigger.dr.async_get",
        lambda hass: registry,
    )

    hass = SimpleNamespace()
    triggers = await device_trigger.async_get_triggers(hass, "device-1")
    assert len(triggers) == 8  # J1 exposes two buttons with four press types each
    for trig in triggers:
        assert trig["platform"] == "device"
        assert trig["domain"] == DOMAIN
        assert trig["device_id"] == "device-1"


@pytest.mark.asyncio
async def test_async_attach_trigger_filters_events(monkeypatch):
    """Dispatcher callback should fire automation action when trigger matches."""
    hass = SimpleNamespace()

    def async_run_job(action, payload):
        action(payload)

    hass.async_run_job = async_run_job

    callbacks: dict[str, object] = {}

    def fake_dispatcher_connect(hass_arg, signal, callback):
        callbacks[signal] = callback

        def _unsub():
            callbacks.pop(signal, None)

        return _unsub

    monkeypatch.setattr(
        "custom_components.ubisys.device_trigger.async_dispatcher_connect",
        fake_dispatcher_connect,
    )

    captured: list[dict] = []

    def action(payload):
        captured.append(payload)

    config = {
        "platform": "device",
        "domain": DOMAIN,
        "device_id": "device-1",
        "type": device_trigger.TRIGGER_BUTTON_1_SHORT_PRESS,
    }

    unsub = await device_trigger.async_attach_trigger(
        hass, config, action, {"metadata": {}}
    )

    signal = f"{device_trigger.SIGNAL_INPUT_EVENT}_device-1"
    callbacks[signal](
        {
            ATTR_INPUT_NUMBER: 0,
            ATTR_PRESS_TYPE: "short_press",
        }
    )

    assert captured, "Expected automation action to be executed"
    assert captured[0]["trigger"]["type"] == device_trigger.TRIGGER_BUTTON_1_SHORT_PRESS

    unsub()
    assert signal not in callbacks
