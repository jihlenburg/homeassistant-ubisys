"""Tests for button platform."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.ubisys import button as button_mod
from custom_components.ubisys.const import DOMAIN, SERVICE_CALIBRATE_J1


class DummyHass:
    """Minimal hass double for button tests."""

    def __init__(self):
        self.services = MagicMock()
        self.services.async_call = AsyncMock()
        self.data = {DOMAIN: {}}


@pytest.mark.asyncio
async def test_async_setup_entry_creates_buttons_for_j1(monkeypatch):
    """Button entities created for J1/J1-R devices."""
    hass = DummyHass()
    entities_added = []

    config_entry = SimpleNamespace(
        data={
            "device_ieee": "00:11:22:33",
            "model": "J1",
        },
        entry_id="entry1",
    )

    def add_entities(entities):
        entities_added.extend(entities)

    await button_mod.async_setup_entry(hass, config_entry, add_entities)

    # Should create 2 buttons: Calibrate and Health Check
    assert len(entities_added) == 2
    assert isinstance(entities_added[0], button_mod.UbisysCalibrationButton)
    assert isinstance(entities_added[1], button_mod.UbisysHealthCheckButton)


@pytest.mark.asyncio
async def test_async_setup_entry_skips_non_j1(monkeypatch):
    """No buttons for D1/S1 devices."""
    hass = DummyHass()
    entities_added = []

    # Test D1 model
    config_entry = SimpleNamespace(
        data={
            "device_ieee": "00:11:22:33",
            "model": "D1",
        },
        entry_id="entry1",
    )

    await button_mod.async_setup_entry(
        hass, config_entry, lambda e: entities_added.extend(e)
    )
    assert len(entities_added) == 0

    # Test S1 model
    config_entry_s1 = SimpleNamespace(
        data={
            "device_ieee": "00:11:22:34",
            "model": "S1",
        },
        entry_id="entry2",
    )

    await button_mod.async_setup_entry(
        hass, config_entry_s1, lambda e: entities_added.extend(e)
    )
    assert len(entities_added) == 0


@pytest.mark.asyncio
async def test_calibration_button_press_calls_service(monkeypatch):
    """Pressing calibration button calls ubisys.calibrate_j1 service."""
    hass = DummyHass()

    config_entry = SimpleNamespace(
        data={"device_ieee": "00:11:22:33", "model": "J1"},
        entry_id="entry1",
    )

    button = button_mod.UbisysCalibrationButton(
        hass=hass,
        config_entry=config_entry,
        device_ieee="00:11:22:33",
    )

    # Mock entity registry
    cover_entry = SimpleNamespace(
        entity_id="cover.ubisys_test",
        domain="cover",
    )
    fake_registry = MagicMock()

    monkeypatch.setattr(
        "homeassistant.helpers.entity_registry.async_get",
        lambda h: fake_registry,
    )
    monkeypatch.setattr(
        "homeassistant.helpers.entity_registry.async_entries_for_config_entry",
        lambda reg, entry_id: [cover_entry],
    )

    await button.async_press()

    hass.services.async_call.assert_awaited_once_with(
        DOMAIN,
        SERVICE_CALIBRATE_J1,
        {"entity_id": "cover.ubisys_test"},
        blocking=False,
    )


@pytest.mark.asyncio
async def test_calibration_button_press_handles_missing_cover(monkeypatch, caplog):
    """Button press handles missing cover entity gracefully."""
    hass = DummyHass()

    config_entry = SimpleNamespace(
        data={"device_ieee": "00:11:22:33", "model": "J1"},
        entry_id="entry1",
    )

    button = button_mod.UbisysCalibrationButton(
        hass=hass,
        config_entry=config_entry,
        device_ieee="00:11:22:33",
    )

    # Mock entity registry with no cover entity
    fake_registry = MagicMock()

    monkeypatch.setattr(
        "homeassistant.helpers.entity_registry.async_get",
        lambda h: fake_registry,
    )
    monkeypatch.setattr(
        "homeassistant.helpers.entity_registry.async_entries_for_config_entry",
        lambda reg, entry_id: [],  # No entities
    )

    await button.async_press()

    # Service should not be called
    hass.services.async_call.assert_not_awaited()
    assert "Could not find cover entity" in caplog.text


@pytest.mark.asyncio
async def test_health_check_button_press_calls_service_with_test_mode(monkeypatch):
    """Pressing health check button calls service with test_mode=True."""
    hass = DummyHass()

    config_entry = SimpleNamespace(
        data={"device_ieee": "00:11:22:33", "model": "J1"},
        entry_id="entry1",
    )

    button = button_mod.UbisysHealthCheckButton(
        hass=hass,
        config_entry=config_entry,
        device_ieee="00:11:22:33",
    )

    # Mock entity registry
    cover_entry = SimpleNamespace(
        entity_id="cover.ubisys_test",
        domain="cover",
    )
    fake_registry = MagicMock()

    monkeypatch.setattr(
        "homeassistant.helpers.entity_registry.async_get",
        lambda h: fake_registry,
    )
    monkeypatch.setattr(
        "homeassistant.helpers.entity_registry.async_entries_for_config_entry",
        lambda reg, entry_id: [cover_entry],
    )

    await button.async_press()

    hass.services.async_call.assert_awaited_once_with(
        DOMAIN,
        SERVICE_CALIBRATE_J1,
        {"entity_id": "cover.ubisys_test", "test_mode": True},
        blocking=False,
    )


def test_calibration_button_device_info():
    """Calibration button has correct device info."""
    hass = DummyHass()
    config_entry = SimpleNamespace(
        data={"device_ieee": "00:11:22:33", "model": "J1"},
        entry_id="entry1",
    )

    button = button_mod.UbisysCalibrationButton(
        hass=hass,
        config_entry=config_entry,
        device_ieee="00:11:22:33",
    )

    assert button._attr_unique_id == "00:11:22:33_calibrate"
    assert button._attr_device_info == {"identifiers": {(DOMAIN, "00:11:22:33")}}
    assert button._attr_name == "Calibrate"
    assert button._attr_icon == "mdi:tune"


def test_health_check_button_attributes():
    """Health check button has correct attributes."""
    hass = DummyHass()
    config_entry = SimpleNamespace(
        data={"device_ieee": "00:11:22:33", "model": "J1"},
        entry_id="entry1",
    )

    button = button_mod.UbisysHealthCheckButton(
        hass=hass,
        config_entry=config_entry,
        device_ieee="00:11:22:33",
    )

    assert button._attr_unique_id == "00:11:22:33_health_check"
    assert button._attr_device_info == {"identifiers": {(DOMAIN, "00:11:22:33")}}
    assert button._attr_name == "Health Check"
    assert button._attr_icon == "mdi:heart-pulse"


@pytest.mark.asyncio
async def test_calibration_button_handles_service_exception(monkeypatch, caplog):
    """Button handles service call exceptions gracefully."""
    hass = DummyHass()
    hass.services.async_call = AsyncMock(side_effect=Exception("Service error"))

    config_entry = SimpleNamespace(
        data={"device_ieee": "00:11:22:33", "model": "J1"},
        entry_id="entry1",
    )

    button = button_mod.UbisysCalibrationButton(
        hass=hass,
        config_entry=config_entry,
        device_ieee="00:11:22:33",
    )

    # Mock entity registry
    cover_entry = SimpleNamespace(
        entity_id="cover.ubisys_test",
        domain="cover",
    )
    fake_registry = MagicMock()

    monkeypatch.setattr(
        "homeassistant.helpers.entity_registry.async_get",
        lambda h: fake_registry,
    )
    monkeypatch.setattr(
        "homeassistant.helpers.entity_registry.async_entries_for_config_entry",
        lambda reg, entry_id: [cover_entry],
    )

    # Should not raise, just log error
    await button.async_press()
    assert "Failed to call calibration service" in caplog.text
