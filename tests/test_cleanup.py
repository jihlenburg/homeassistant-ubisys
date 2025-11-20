"""Tests for cleanup service functions."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from custom_components.ubisys import cleanup as cleanup_mod
from custom_components.ubisys.const import DOMAIN


class DummyEntityRegistry:
    """Minimal entity registry double for cleanup tests."""

    def __init__(self, entities: list[Any] | None = None):
        self._entities = {e.entity_id: e for e in (entities or [])}
        self.removed: list[str] = []

    @property
    def entities(self):
        return SimpleNamespace(values=lambda: self._entities.values())

    def async_get(self, entity_id: str) -> Any | None:
        return self._entities.get(entity_id)

    def async_remove(self, entity_id: str) -> None:
        self.removed.append(entity_id)
        if entity_id in self._entities:
            del self._entities[entity_id]


class DummyDeviceRegistry:
    """Minimal device registry double for cleanup tests."""

    def __init__(
        self,
        devices: list[Any] | None = None,
        deleted_devices: list[dict[str, Any]] | None = None,
    ):
        self._devices = {d.id: d for d in (devices or [])}
        self.deleted_devices = deleted_devices or []
        self._saved = False

    @property
    def devices(self):
        return SimpleNamespace(values=lambda: self._devices.values())

    def async_get(self, device_id: str) -> Any | None:
        return self._devices.get(device_id)

    def async_schedule_save(self) -> None:
        self._saved = True


class DummyHass:
    """Minimal hass double for cleanup tests."""

    def __init__(self):
        self.data: dict[str, Any] = {}


class DummyServiceCall:
    """Minimal service call double."""

    def __init__(self, data: dict[str, Any] | None = None):
        self.data = data or {}


# =============================================================================
# _find_orphaned_devices tests
# =============================================================================


@pytest.mark.asyncio
async def test_find_orphaned_devices_finds_ubisys_devices():
    """Ubisys devices in deleted_devices are found."""
    hass = DummyHass()
    device_registry = DummyDeviceRegistry(
        deleted_devices=[
            {
                "id": "device_1",
                "name": "Ubisys J1",
                "identifiers": [(DOMAIN, "00:11:22:33")],
            },
            {
                "id": "device_2",
                "name": "Other Device",
                "identifiers": [("other", "00:44:55:66")],
            },
        ]
    )

    result = await cleanup_mod._find_orphaned_devices(hass, device_registry)

    assert len(result) == 1
    assert result[0]["id"] == "device_1"


@pytest.mark.asyncio
async def test_find_orphaned_devices_empty_deleted_list():
    """Empty deleted_devices returns empty list."""
    hass = DummyHass()
    device_registry = DummyDeviceRegistry(deleted_devices=[])

    result = await cleanup_mod._find_orphaned_devices(hass, device_registry)

    assert result == []


@pytest.mark.asyncio
async def test_find_orphaned_devices_no_deleted_devices_attr():
    """Missing deleted_devices attribute returns empty list."""
    hass = DummyHass()
    device_registry = DummyDeviceRegistry()
    # Remove the attribute entirely
    delattr(device_registry, "deleted_devices")

    result = await cleanup_mod._find_orphaned_devices(hass, device_registry)

    assert result == []


# =============================================================================
# _find_orphaned_entities tests
# =============================================================================


@pytest.mark.asyncio
async def test_find_orphaned_entities_finds_missing_config_entries():
    """Entities without valid config entries are found."""
    hass = DummyHass()
    hass.data[DOMAIN] = {}  # No config entries

    orphan_entity = SimpleNamespace(
        entity_id="cover.ubisys_test",
        platform=DOMAIN,
        config_entry_id="missing_entry",
    )
    entity_registry = DummyEntityRegistry([orphan_entity])
    device_registry = DummyDeviceRegistry()

    result = await cleanup_mod._find_orphaned_entities(
        hass, entity_registry, device_registry
    )

    assert len(result) == 1
    assert result[0].entity_id == "cover.ubisys_test"


@pytest.mark.asyncio
async def test_find_orphaned_entities_skips_valid_entries():
    """Entities with valid config entries are not orphaned."""
    hass = DummyHass()
    hass.data[DOMAIN] = {"entry_1": {}}  # Valid entry exists

    valid_entity = SimpleNamespace(
        entity_id="cover.ubisys_test",
        platform=DOMAIN,
        config_entry_id="entry_1",
    )
    entity_registry = DummyEntityRegistry([valid_entity])
    device_registry = DummyDeviceRegistry()

    result = await cleanup_mod._find_orphaned_entities(
        hass, entity_registry, device_registry
    )

    assert result == []


@pytest.mark.asyncio
async def test_find_orphaned_entities_skips_other_platforms():
    """Entities from other platforms are ignored."""
    hass = DummyHass()
    hass.data[DOMAIN] = {}

    other_platform = SimpleNamespace(
        entity_id="cover.zha_cover",
        platform="zha",
        config_entry_id="missing_entry",
    )
    entity_registry = DummyEntityRegistry([other_platform])
    device_registry = DummyDeviceRegistry()

    result = await cleanup_mod._find_orphaned_entities(
        hass, entity_registry, device_registry
    )

    assert result == []


# =============================================================================
# _remove_deleted_devices tests
# =============================================================================


@pytest.mark.asyncio
async def test_remove_deleted_devices_removes_orphans(monkeypatch):
    """Orphaned devices are removed from deleted_devices list."""
    hass = DummyHass()

    orphan_device = {"id": "device_1", "name": "Ubisys J1"}
    keep_device = {"id": "device_2", "name": "Keep This"}

    device_registry = DummyDeviceRegistry(deleted_devices=[orphan_device, keep_device])

    monkeypatch.setattr(
        "custom_components.ubisys.cleanup.dr.async_get",
        lambda h: device_registry,
    )

    result = await cleanup_mod._remove_deleted_devices(hass, [orphan_device])

    assert len(result) == 1
    assert result[0]["id"] == "device_1"
    assert device_registry._saved is True
    # Only the kept device should remain
    assert len(device_registry.deleted_devices) == 1
    assert device_registry.deleted_devices[0]["id"] == "device_2"


@pytest.mark.asyncio
async def test_remove_deleted_devices_empty_list():
    """Empty orphan list returns empty result."""
    hass = DummyHass()

    result = await cleanup_mod._remove_deleted_devices(hass, [])

    assert result == []


@pytest.mark.asyncio
async def test_remove_deleted_devices_missing_deleted_devices(monkeypatch):
    """Missing deleted_devices attribute returns empty result."""
    hass = DummyHass()

    device_registry = DummyDeviceRegistry()
    delattr(device_registry, "deleted_devices")

    monkeypatch.setattr(
        "custom_components.ubisys.cleanup.dr.async_get",
        lambda h: device_registry,
    )

    result = await cleanup_mod._remove_deleted_devices(
        hass, [{"id": "device_1", "name": "Test"}]
    )

    assert result == []


# =============================================================================
# async_cleanup_orphans tests
# =============================================================================


@pytest.mark.asyncio
async def test_cleanup_orphans_dry_run(monkeypatch):
    """Dry run finds orphans but doesn't remove them."""
    hass = DummyHass()
    hass.data[DOMAIN] = {}

    orphan_entity = SimpleNamespace(
        entity_id="cover.ubisys_orphan",
        platform=DOMAIN,
        config_entry_id="missing_entry",
    )
    entity_registry = DummyEntityRegistry([orphan_entity])

    orphan_device = {
        "id": "device_1",
        "name": "Ubisys J1",
        "identifiers": [(DOMAIN, "00:11:22:33")],
    }
    device_registry = DummyDeviceRegistry(deleted_devices=[orphan_device])

    monkeypatch.setattr(
        "custom_components.ubisys.cleanup.dr.async_get",
        lambda h: device_registry,
    )
    monkeypatch.setattr(
        "custom_components.ubisys.cleanup.er.async_get",
        lambda h: entity_registry,
    )

    call = DummyServiceCall({"dry_run": True})
    result = await cleanup_mod.async_cleanup_orphans(hass, call)

    assert result["dry_run"] is True
    assert len(result["orphaned_entities"]) == 1
    assert len(result["orphaned_devices"]) == 1
    # Nothing should be removed in dry run
    assert len(entity_registry.removed) == 0


@pytest.mark.asyncio
async def test_cleanup_orphans_actual_removal(monkeypatch):
    """Actual cleanup removes orphans."""
    hass = DummyHass()
    hass.data[DOMAIN] = {}

    orphan_entity = SimpleNamespace(
        entity_id="cover.ubisys_orphan",
        platform=DOMAIN,
        config_entry_id="missing_entry",
    )
    entity_registry = DummyEntityRegistry([orphan_entity])

    orphan_device = {
        "id": "device_1",
        "name": "Ubisys J1",
        "identifiers": [(DOMAIN, "00:11:22:33")],
    }
    device_registry = DummyDeviceRegistry(deleted_devices=[orphan_device])

    monkeypatch.setattr(
        "custom_components.ubisys.cleanup.dr.async_get",
        lambda h: device_registry,
    )
    monkeypatch.setattr(
        "custom_components.ubisys.cleanup.er.async_get",
        lambda h: entity_registry,
    )

    call = DummyServiceCall({"dry_run": False})
    result = await cleanup_mod.async_cleanup_orphans(hass, call)

    assert result["dry_run"] is False
    assert len(result["orphaned_entities"]) == 1
    assert "cover.ubisys_orphan" in result["orphaned_entities"]
    # Entity should be removed
    assert "cover.ubisys_orphan" in entity_registry.removed


@pytest.mark.asyncio
async def test_cleanup_orphans_no_orphans(monkeypatch):
    """Cleanup with no orphans returns empty results."""
    hass = DummyHass()
    hass.data[DOMAIN] = {"entry_1": {}}

    valid_entity = SimpleNamespace(
        entity_id="cover.ubisys_valid",
        platform=DOMAIN,
        config_entry_id="entry_1",
    )
    entity_registry = DummyEntityRegistry([valid_entity])
    device_registry = DummyDeviceRegistry(deleted_devices=[])

    monkeypatch.setattr(
        "custom_components.ubisys.cleanup.dr.async_get",
        lambda h: device_registry,
    )
    monkeypatch.setattr(
        "custom_components.ubisys.cleanup.er.async_get",
        lambda h: entity_registry,
    )

    call = DummyServiceCall({})
    result = await cleanup_mod.async_cleanup_orphans(hass, call)

    assert result["dry_run"] is False
    assert result["orphaned_entities"] == []
    assert result["orphaned_devices"] == []
