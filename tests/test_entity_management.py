"""Tests for entity management utilities."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

import pytest

from custom_components.ubisys import entity_management as em
from custom_components.ubisys.const import DOMAIN


class DummyEntityRegistry:
    """Minimal entity registry double."""

    def __init__(self, entities: list[Any] | None = None):
        self._entities = {e.entity_id: e for e in (entities or [])}
        self.removed: list[str] = []
        self.updated: dict[str, Any] = {}

    @property
    def entities(self):
        return SimpleNamespace(values=lambda: self._entities.values())

    def async_remove(self, entity_id):
        self.removed.append(entity_id)
        if entity_id in self._entities:
            del self._entities[entity_id]

    def async_update_entity(self, entity_id, **kwargs):
        self.updated[entity_id] = kwargs


class DummyDeviceRegistry:
    """Minimal device registry double."""

    def __init__(self, devices: list[Any] | None = None):
        self._devices = {d.id: d for d in (devices or [])}
        self.created: list[dict[str, Any]] = []
        self.updated: dict[str, Any] = {}

    @property
    def devices(self):
        return SimpleNamespace(values=lambda: self._devices.values())

    def async_get(self, device_id):
        return self._devices.get(device_id)

    def async_get_or_create(self, **kwargs):
        device = SimpleNamespace(id="new_device", **kwargs)
        self.created.append(kwargs)
        return device

    def async_update_device(self, device_id, **kwargs):
        self.updated[device_id] = kwargs
        device = self._devices.get(device_id)
        return device if device else SimpleNamespace(id=device_id)


class DummyHass:
    """Minimal hass double."""

    def __init__(self):
        self.data = {}
        self.config_entries = MagicMock()


@pytest.mark.asyncio
async def test_async_cleanup_orphaned_entities_removes_orphans(monkeypatch):
    """Orphaned entities are removed."""
    # Create orphaned entity (no config_entry_id)
    orphan = SimpleNamespace(
        entity_id="cover.ubisys_orphan",
        platform=DOMAIN,
        unique_id="00:11:22:33_cover",
        config_entry_id=None,
    )
    registry = DummyEntityRegistry([orphan])

    monkeypatch.setattr(
        "custom_components.ubisys.entity_management.er.async_get",
        lambda h: registry,
    )

    hass = DummyHass()
    count = await em.async_cleanup_orphaned_entities(hass, "00:11:22:33")

    assert count == 1
    assert "cover.ubisys_orphan" in registry.removed


@pytest.mark.asyncio
async def test_async_cleanup_orphaned_entities_skips_valid_entities(monkeypatch):
    """Valid entities are not removed."""
    # Entity with config_entry_id is not orphaned
    valid = SimpleNamespace(
        entity_id="cover.ubisys_valid",
        platform=DOMAIN,
        unique_id="00:11:22:33_cover",
        config_entry_id="entry1",
    )
    registry = DummyEntityRegistry([valid])

    monkeypatch.setattr(
        "custom_components.ubisys.entity_management.er.async_get",
        lambda h: registry,
    )

    hass = DummyHass()
    count = await em.async_cleanup_orphaned_entities(hass, "00:11:22:33")

    assert count == 0
    assert len(registry.removed) == 0


@pytest.mark.asyncio
async def test_async_cleanup_orphaned_entities_skips_other_platforms(monkeypatch):
    """Only Ubisys entities are considered for cleanup."""
    # Entity from different platform
    other = SimpleNamespace(
        entity_id="cover.zha_cover",
        platform="zha",
        unique_id="00:11:22:33_cover",
        config_entry_id=None,
    )
    registry = DummyEntityRegistry([other])

    monkeypatch.setattr(
        "custom_components.ubisys.entity_management.er.async_get",
        lambda h: registry,
    )

    hass = DummyHass()
    count = await em.async_cleanup_orphaned_entities(hass, "00:11:22:33")

    assert count == 0


@pytest.mark.asyncio
async def test_async_ensure_device_entry_links_zha_device(monkeypatch):
    """Existing ZHA device is linked to Ubisys config entry."""
    # Create existing ZHA device
    zha_device = SimpleNamespace(
        id="device_123",
        identifiers={("zha", "00:11:22:33")},
    )
    device_registry = DummyDeviceRegistry([zha_device])

    monkeypatch.setattr(
        "custom_components.ubisys.entity_management.dr.async_get",
        lambda h: device_registry,
    )

    hass = DummyHass()
    hass.config_entries.async_update_entry = MagicMock()

    entry = SimpleNamespace(
        entry_id="entry1",
        data={
            "device_ieee": "00:11:22:33",
            "model": "J1",
            "name": "Test J1",
        },
    )

    await em.async_ensure_device_entry(hass, entry)

    # Device should be updated with our config entry
    assert "device_123" in device_registry.updated
    assert device_registry.updated["device_123"]["add_config_entry_id"] == "entry1"


@pytest.mark.asyncio
async def test_async_ensure_device_entry_creates_standalone(monkeypatch):
    """Standalone device created when no ZHA device found."""
    device_registry = DummyDeviceRegistry([])  # No devices

    monkeypatch.setattr(
        "custom_components.ubisys.entity_management.dr.async_get",
        lambda h: device_registry,
    )

    hass = DummyHass()
    hass.config_entries.async_update_entry = MagicMock()

    entry = SimpleNamespace(
        entry_id="entry1",
        data={
            "device_ieee": "00:11:22:33",
            "model": "J1",
            "name": "Test J1",
        },
    )

    await em.async_ensure_device_entry(hass, entry)

    # Should create standalone device
    assert len(device_registry.created) == 1


def test_recompute_verbose_flags_aggregates_entries():
    """Verbose flags computed from all config entries."""
    hass = DummyHass()

    # Create mock config entries
    entry1 = SimpleNamespace(
        options={"verbose_info_logging": True, "verbose_input_logging": False}
    )
    entry2 = SimpleNamespace(
        options={"verbose_info_logging": False, "verbose_input_logging": True}
    )
    hass.config_entries.async_entries = MagicMock(return_value=[entry1, entry2])

    em.recompute_verbose_flags(hass)

    # Any entry with True should make the flag True
    assert hass.data[DOMAIN]["verbose_info_logging"] is True
    assert hass.data[DOMAIN]["verbose_input_logging"] is True


def test_recompute_verbose_flags_all_false():
    """Verbose flags are False when no entries have them enabled."""
    hass = DummyHass()

    entry1 = SimpleNamespace(options={"verbose_info_logging": False})
    entry2 = SimpleNamespace(options={})  # No option set
    hass.config_entries.async_entries = MagicMock(return_value=[entry1, entry2])

    em.recompute_verbose_flags(hass)

    assert hass.data[DOMAIN]["verbose_info_logging"] is False
    assert hass.data[DOMAIN]["verbose_input_logging"] is False


@pytest.mark.asyncio
async def test_options_update_listener_recomputes_flags():
    """Options update listener recomputes verbose flags."""
    hass = DummyHass()

    entry = SimpleNamespace(options={"verbose_info_logging": True})
    hass.config_entries.async_entries = MagicMock(return_value=[entry])

    await em.options_update_listener(hass, entry)

    assert hass.data[DOMAIN]["verbose_info_logging"] is True


def test_async_untrack_zha_entities(monkeypatch):
    """ZHA entities are removed from tracking."""
    hass = DummyHass()
    hass.data[DOMAIN] = {"tracked_zha_entities": {"cover.zha_test", "light.zha_other"}}

    # Mock entity registry
    zha_entity = SimpleNamespace(
        entity_id="cover.zha_test",
        platform="zha",
        domain="cover",
        device_id="device_123",
    )
    registry = DummyEntityRegistry([zha_entity])

    monkeypatch.setattr(
        "custom_components.ubisys.entity_management.er.async_get",
        lambda h: registry,
    )
    monkeypatch.setattr(
        "custom_components.ubisys.entity_management.er.async_entries_for_config_entry",
        lambda reg, entry_id: [zha_entity],
    )

    entry = SimpleNamespace(
        entry_id="entry1",
        data={
            "device_ieee": "00:11:22:33",
            "model": "J1",
            "zha_config_entry_id": "zha_entry",
            "device_id": "device_123",
        },
    )

    em.async_untrack_zha_entities(hass, entry)

    # Entity should be removed from tracking
    assert "cover.zha_test" not in hass.data[DOMAIN]["tracked_zha_entities"]
    # Other entities should remain
    assert "light.zha_other" in hass.data[DOMAIN]["tracked_zha_entities"]
