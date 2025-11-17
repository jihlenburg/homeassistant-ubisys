"""Tests covering integration setup/unload lifecycle."""

from __future__ import annotations

from importlib import import_module
from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.const import EVENT_HOMEASSISTANT_STARTED

from custom_components.ubisys.const import (
    DOMAIN,
    SERVICE_CALIBRATE,
    SERVICE_CONFIGURE_D1_BALLAST,
    SERVICE_CONFIGURE_D1_PHASE_MODE,
)

ubisys = import_module("custom_components.ubisys.__init__")


@pytest.mark.asyncio
async def test_async_setup_registers_services_and_handles_startup(
    hass_full, monkeypatch
):
    """Ensure async_setup wires services and deferred startup tasks."""
    hass = hass_full

    entry = MagicMock()
    entry.entry_id = "entry1"
    hass.config_entries.async_entries = MagicMock(return_value=[entry])

    discover = AsyncMock()
    monitor_setup = AsyncMock()
    monkeypatch.setattr(ubisys, "async_discover_devices", discover)
    monkeypatch.setattr(ubisys, "async_setup_input_monitoring", monitor_setup)

    registry_callbacks: list = []

    def fake_track(hass_arg, callback):
        registry_callbacks.append(callback)

    monkeypatch.setattr(ubisys, "async_track_device_registry_updated_event", fake_track)

    assert await ubisys.async_setup(hass, {})
    await hass.async_block_till_done()

    assert hass.services.has_service(DOMAIN, SERVICE_CALIBRATE)
    assert hass.services.has_service(DOMAIN, SERVICE_CONFIGURE_D1_PHASE_MODE)
    assert hass.services.has_service(DOMAIN, SERVICE_CONFIGURE_D1_BALLAST)

    hass.bus.async_fire(EVENT_HOMEASSISTANT_STARTED)
    await hass.async_block_till_done()

    assert discover.await_count == 1
    monitor_setup.assert_awaited_once_with(hass, "entry1")
    assert registry_callbacks, "device-registry listener should be registered"


@pytest.mark.asyncio
async def test_async_setup_entry_stores_data_and_hides_zha(hass_full, monkeypatch):
    """async_setup_entry should forward platforms and hide ZHA entity."""
    hass = hass_full
    hass.config_entries.async_forward_entry_setups = AsyncMock()

    hide = AsyncMock()
    cleanup = AsyncMock(return_value=0)  # Mock cleanup to return 0 orphaned entities
    ensure_device = AsyncMock()  # Mock device creation
    ensure_zha_enabled = AsyncMock()  # Mock ZHA entity auto-enable
    monkeypatch.setattr(ubisys, "_hide_zha_entity", hide)
    monkeypatch.setattr(ubisys, "_cleanup_orphaned_entities", cleanup)
    monkeypatch.setattr(ubisys, "_ensure_device_entry", ensure_device)
    monkeypatch.setattr(ubisys, "_ensure_zha_entity_enabled", ensure_zha_enabled)

    entry = MagicMock()
    entry.entry_id = "entry42"
    entry.data = {
        "device_ieee": "00:11",
        "model": "J1",
        "device_id": "device-1",
        "zha_config_entry_id": "zha",
    }
    entry.add_update_listener = MagicMock(return_value="listener")
    entry.async_on_unload = MagicMock()

    await ubisys.async_setup_entry(hass, entry)

    # Verify new cleanup and device creation were called
    cleanup.assert_awaited_once_with(hass, "00:11")
    ensure_device.assert_awaited_once_with(hass, entry)
    ensure_zha_enabled.assert_awaited_once_with(hass, entry)

    hass.config_entries.async_forward_entry_setups.assert_awaited_once_with(
        entry, ubisys.PLATFORMS
    )
    hide.assert_awaited_once_with(hass, entry)
    entry.async_on_unload.assert_called_once()
    assert hass.data[DOMAIN][entry.entry_id] == entry.data


@pytest.mark.asyncio
async def test_async_unload_entry_unhides_and_unloads(hass_full, monkeypatch):
    """async_unload_entry should undo setup work and respect unload result."""
    hass = hass_full
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN]["entry99"] = {"device_ieee": "00:11"}

    entry = MagicMock()
    entry.entry_id = "entry99"
    entry.data = {
        "device_ieee": "00:11",
        "model": "J1",
        "device_id": "device-1",
        "zha_config_entry_id": "zha",
    }

    unhide = AsyncMock()
    unload_monitor = AsyncMock()
    cleanup = AsyncMock(return_value=0)  # Mock cleanup
    untrack = MagicMock()  # Mock untrack (synchronous function)
    monkeypatch.setattr(ubisys, "_unhide_zha_entity", unhide)
    monkeypatch.setattr(ubisys, "async_unload_input_monitoring", unload_monitor)
    monkeypatch.setattr(ubisys, "_cleanup_orphaned_entities", cleanup)
    monkeypatch.setattr(ubisys, "_untrack_zha_entities", untrack)
    hass.config_entries.async_unload_platforms = AsyncMock(return_value=True)

    assert await ubisys.async_unload_entry(hass, entry)

    unhide.assert_awaited_once_with(hass, entry)
    untrack.assert_called_once_with(hass, entry)
    unload_monitor.assert_awaited_once_with(hass)
    cleanup.assert_awaited_once_with(hass, "00:11")  # Verify cleanup was called
    hass.config_entries.async_unload_platforms.assert_awaited_once_with(
        entry, ubisys.PLATFORMS
    )
    assert "entry99" not in hass.data[DOMAIN]
