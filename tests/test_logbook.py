"""Tests for logbook event registration."""

from __future__ import annotations

import importlib
import sys
import types

import homeassistant.components as ha_components

from custom_components.ubisys.const import (
    EVENT_UBISYS_CALIBRATION_COMPLETE,
    EVENT_UBISYS_INPUT,
)


def test_async_describe_events_registers_calibration_and_input():
    # Provide lightweight psutil shim required by Home Assistant recorder import
    sys.modules.setdefault(
        "psutil_home_assistant", types.ModuleType("psutil_home_assistant")
    )
    # Stub HA logbook component to avoid pulling recorder/sqlalchemy dependency tree
    fake_logbook = types.ModuleType("homeassistant.components.logbook")
    fake_logbook.ACTION_CHANGE = "change"
    sys.modules["homeassistant.components.logbook"] = fake_logbook
    setattr(ha_components, "logbook", fake_logbook)

    logbook = importlib.import_module("custom_components.ubisys.logbook")

    recorded: list[tuple] = []

    def fake_describe(domain, event, description, action):
        recorded.append((domain, event, description, action))

    logbook.async_describe_events(None, fake_describe)

    domains_and_events = {(domain, event) for domain, event, *_ in recorded}
    assert ("ubisys", EVENT_UBISYS_CALIBRATION_COMPLETE) in domains_and_events
    assert ("ubisys", EVENT_UBISYS_INPUT) in domains_and_events
