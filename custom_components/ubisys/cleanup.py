"""Cleanup orphaned devices and entities for Ubisys integration.

This module provides functionality to detect and remove orphaned Ubisys devices
and entities from Home Assistant's device and entity registries.

Orphaned items occur when:
- Integration is removed/reinstalled
- Devices are deleted but remain in deleted_devices list
- Entities exist without valid config entries
- Config entries are removed but entities remain

This cleanup service helps maintain a clean registry without manual intervention.
"""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_cleanup_orphans(
    hass: HomeAssistant, call: ServiceCall
) -> dict[str, Any]:
    """Clean up orphaned Ubisys devices and entities.

    Searches for and optionally removes:
    1. Devices in deleted_devices list with Ubisys identifiers
    2. Entities with platform='ubisys' but no valid config entry
    3. Entities referencing deleted Ubisys config entries

    Args:
        hass: Home Assistant instance
        call: Service call with optional dry_run parameter

    Returns:
        Dictionary with cleanup results:
        - orphaned_devices: List of device names/IDs removed
        - orphaned_entities: List of entity IDs removed
        - dry_run: Whether this was a preview (no changes made)
    """
    dry_run = call.data.get("dry_run", False)

    _LOGGER.info(
        "Starting Ubisys orphan cleanup (dry_run=%s)",
        dry_run,
    )

    # Get registries
    device_registry = dr.async_get(hass)
    entity_registry = er.async_get(hass)

    # Find orphaned devices
    orphaned_devices = await _find_orphaned_devices(hass, device_registry)

    # Find orphaned entities
    orphaned_entities = await _find_orphaned_entities(
        hass, entity_registry, device_registry
    )

    # Log what was found
    _LOGGER.info(
        "Found %d orphaned devices and %d orphaned entities",
        len(orphaned_devices),
        len(orphaned_entities),
    )

    if dry_run:
        _LOGGER.info("Dry run - no changes made")
        return {
            "orphaned_devices": [
                {
                    "id": d["id"],
                    "name": d.get("name_by_user") or d.get("name", "unknown"),
                }
                for d in orphaned_devices
            ],
            "orphaned_entities": [e.entity_id for e in orphaned_entities],
            "dry_run": True,
        }

    # Remove orphaned entities
    removed_entities = []
    for entity_entry in orphaned_entities:
        entity_registry.async_remove(entity_entry.entity_id)
        removed_entities.append(entity_entry.entity_id)
        _LOGGER.debug("Removed orphaned entity: %s", entity_entry.entity_id)

    # Remove orphaned devices from deleted_devices
    removed_devices = await _remove_deleted_devices(hass, orphaned_devices)

    _LOGGER.info(
        "Cleanup complete: removed %d devices and %d entities",
        len(removed_devices),
        len(removed_entities),
    )

    return {
        "orphaned_devices": removed_devices,
        "orphaned_entities": removed_entities,
        "dry_run": False,
    }


async def _find_orphaned_devices(
    hass: HomeAssistant, device_registry: dr.DeviceRegistry
) -> list[dict[str, Any]]:
    """Find Ubisys devices in the deleted_devices list.

    These are devices that were deleted but remain in the registry's
    recycle bin. They can be safely purged.

    Args:
        hass: Home Assistant instance
        device_registry: Device registry instance

    Returns:
        List of orphaned device dictionaries from deleted_devices
    """
    # Access the internal deleted_devices list
    # This is stored in the registry data but not exposed via the API
    deleted_devices = getattr(device_registry, "deleted_devices", [])

    orphaned = []
    for device_data in deleted_devices:
        # Check if device has Ubisys identifiers
        identifiers = device_data.get("identifiers", [])
        has_ubisys = any(
            identifier[0] == DOMAIN
            for identifier in identifiers
            if len(identifier) >= 2
        )

        if has_ubisys:
            orphaned.append(device_data)
            _LOGGER.debug(
                "Found orphaned device in deleted_devices: %s (ID: %s)",
                device_data.get("name_by_user") or device_data.get("name", "unknown"),
                device_data.get("id", "unknown"),
            )

    return orphaned


async def _find_orphaned_entities(
    hass: HomeAssistant,
    entity_registry: er.EntityRegistry,
    device_registry: dr.DeviceRegistry,
) -> list[er.RegistryEntry]:
    """Find orphaned Ubisys entities.

    An entity is orphaned if:
    - Platform is 'ubisys' but config_entry_id is invalid/missing
    - Config entry no longer exists in hass.data[DOMAIN]

    Args:
        hass: Home Assistant instance
        entity_registry: Entity registry instance
        device_registry: Device registry instance

    Returns:
        List of orphaned entity registry entries
    """
    orphaned = []

    # Check all entities with platform='ubisys'
    for entity_entry in entity_registry.entities.values():
        if entity_entry.platform == DOMAIN:
            config_entry_id = entity_entry.config_entry_id

            # Check if config entry still exists
            if config_entry_id not in hass.data.get(DOMAIN, {}):
                orphaned.append(entity_entry)
                _LOGGER.debug(
                    "Found orphaned entity: %s (config_entry: %s)",
                    entity_entry.entity_id,
                    config_entry_id,
                )

    return orphaned


async def _remove_deleted_devices(
    hass: HomeAssistant, orphaned_devices: list[dict[str, Any]]
) -> list[dict[str, str]]:
    """Remove devices from the deleted_devices list.

    This requires direct access to the device registry storage since
    deleted_devices is not exposed via the public API.

    Args:
        hass: Home Assistant instance
        orphaned_devices: List of device dictionaries to remove

    Returns:
        List of removed device info (id, name)
    """
    if not orphaned_devices:
        return []

    device_registry = dr.async_get(hass)
    removed = []

    # Access the internal deleted_devices list
    deleted_devices = getattr(device_registry, "deleted_devices", None)

    if deleted_devices is None:
        _LOGGER.warning("Cannot access deleted_devices list - API may have changed")
        return []

    # Remove orphaned devices from the list
    device_ids_to_remove = {d["id"] for d in orphaned_devices}

    # Filter out the orphaned devices
    remaining_deleted = [
        d for d in deleted_devices if d.get("id") not in device_ids_to_remove
    ]

    # Update the deleted_devices list
    setattr(device_registry, "deleted_devices", remaining_deleted)

    # Save the updated registry
    device_registry.async_schedule_save()

    for device in orphaned_devices:
        removed.append(
            {
                "id": device.get("id", "unknown"),
                "name": device.get("name_by_user") or device.get("name", "unknown"),
            }
        )
        _LOGGER.debug(
            "Removed device from deleted_devices: %s",
            device.get("name_by_user") or device.get("name", "unknown"),
        )

    return removed
