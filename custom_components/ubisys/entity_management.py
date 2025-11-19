"""Entity management utilities for Ubisys integration.

This module handles the lifecycle of Ubisys entities and their relationship
with the underlying ZHA entities. It includes logic for:
- Hiding/unhiding ZHA entities (wrapper pattern)
- Cleaning up orphaned entities
- ensuring device entries are correctly linked
- Managing global options like verbose logging flags
"""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er

from .const import (
    CONF_DEVICE_ID,
    DOMAIN,
    MANUFACTURER,
    OPTION_VERBOSE_INFO_LOGGING,
    OPTION_VERBOSE_INPUT_LOGGING,
    get_device_type,
)

_LOGGER = logging.getLogger(__name__)


async def async_cleanup_orphaned_entities(
    hass: HomeAssistant,
    device_ieee: str,
) -> int:
    """Clean up orphaned Ubisys entities for a specific device.

    This removes entities that:
    1. Belong to the Ubisys platform
    2. Match the given device IEEE address
    3. Have no config_entry_id (orphaned)

    Args:
        hass: Home Assistant instance
        device_ieee: IEEE address of device (e.g., "00:1f:ee:00:00:00:68:a5")

    Returns:
        Number of orphaned entities removed
    """
    entity_registry = er.async_get(hass)

    # Find orphaned entities for this device
    orphaned: list[str] = []
    for entity in entity_registry.entities.values():
        # Only check Ubisys entities
        if entity.platform != DOMAIN:
            continue

        # Check if entity belongs to this device (by IEEE in unique_id)
        if not entity.unique_id or not entity.unique_id.startswith(device_ieee):
            continue

        # Check if orphaned (no config entry)
        if entity.config_entry_id is None:
            orphaned.append(entity.entity_id)
            _LOGGER.debug(
                "Found orphaned entity: %s (unique_id: %s)",
                entity.entity_id,
                entity.unique_id,
            )

    # Remove orphaned entities
    for entity_id in orphaned:
        entity_registry.async_remove(entity_id)
        _LOGGER.debug("Removed orphaned entity: %s", entity_id)

    return len(orphaned)


async def async_ensure_device_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> None:
    """Ensure device entry exists and is properly configured.

    This finds the existing ZHA device and links our config entry to it,
    rather than creating a separate Ubisys device. This is critical for
    the wrapper architecture to work.

    Args:
        hass: Home Assistant instance
        entry: Config entry for this device
    """
    device_registry = dr.async_get(hass)
    device_ieee = entry.data["device_ieee"]
    manufacturer = entry.data.get("manufacturer", MANUFACTURER)
    model = entry.data["model"]
    name = entry.data["name"]

    # First, try to find existing ZHA device by identifier
    existing_device = None
    for device in device_registry.devices.values():
        for identifier_domain, identifier_value in device.identifiers:
            if identifier_domain == "zha" and identifier_value == device_ieee:
                existing_device = device
                break
        if existing_device:
            break

    if existing_device:
        # ZHA device found - update it to include our config entry
        _LOGGER.debug(
            "Found existing ZHA device id=%s for ieee=%s, linking config entry",
            existing_device.id,
            device_ieee,
        )

        # Update device to add our config entry and ubisys identifier
        device = device_registry.async_update_device(
            existing_device.id,
            add_config_entry_id=entry.entry_id,
            merge_identifiers={(DOMAIN, device_ieee)},
        )

        # Update config entry data to store correct device_id
        hass.config_entries.async_update_entry(
            entry,
            data={**entry.data, CONF_DEVICE_ID: existing_device.id},
        )
    else:
        # No ZHA device found - create standalone device (fallback)
        _LOGGER.warning(
            "No ZHA device found for ieee=%s, creating standalone device. "
            "This is unexpected - Ubisys devices should be paired with ZHA first.",
            device_ieee,
        )

        device = device_registry.async_get_or_create(
            config_entry_id=entry.entry_id,
            identifiers={(DOMAIN, device_ieee)},
            manufacturer=manufacturer,
            model=model,
            name=name,
        )

    _LOGGER.debug(
        "Ensured device entry exists: id=%s, ieee=%s, name=%s",
        device.id,
        device_ieee,
        name,
    )

    # Clean up any orphaned Ubisys devices
    await async_cleanup_orphaned_ubisys_device(hass, entry, device.id, device_ieee)


async def async_cleanup_orphaned_ubisys_device(
    hass: HomeAssistant,
    entry: ConfigEntry,
    correct_device_id: str,
    device_ieee: str,
) -> None:
    """Clean up orphaned Ubisys device entries.

    Args:
        hass: Home Assistant instance
        entry: Our config entry
        correct_device_id: The device_id we should be using (ZHA device)
        device_ieee: IEEE address for identification
    """
    device_registry = dr.async_get(hass)

    # Find orphaned Ubisys device (has our identifier but is not the correct device)
    orphaned_device = None
    for device in device_registry.devices.values():
        # Skip the correct device
        if device.id == correct_device_id:
            continue

        # Check if this device has ("ubisys", ieee) identifier
        for identifier_domain, identifier_value in device.identifiers:
            if identifier_domain == DOMAIN and identifier_value == device_ieee:
                orphaned_device = device
                break

        if orphaned_device:
            break

    if not orphaned_device:
        return

    _LOGGER.info(
        "Found orphaned Ubisys device: id=%s, cleaning up",
        orphaned_device.id,
    )

    try:
        # Remove our config entry from the orphaned device
        device_registry.async_update_device(
            orphaned_device.id,
            remove_config_entry_id=entry.entry_id,
        )
        _LOGGER.debug(
            "Removed config entry from orphaned device id=%s",
            orphaned_device.id,
        )
    except Exception as err:
        _LOGGER.warning(
            "Failed to clean up orphaned device id=%s: %s",
            orphaned_device.id,
            err,
        )


async def async_hide_zha_entity(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Hide the original ZHA entity to prevent duplicate entities.

    Args:
        hass: Home Assistant instance
        entry: Config entry for this device
    """
    entity_registry = er.async_get(hass)
    device_ieee = entry.data.get("device_ieee")
    model = entry.data.get("model", "")

    if not device_ieee:
        _LOGGER.warning("No device IEEE in config entry, cannot hide ZHA entity")
        return

    # Determine which domain to hide based on device type
    device_type = get_device_type(model)

    if device_type == "window_covering":
        domain_to_hide = "cover"
    elif device_type == "dimmer":
        domain_to_hide = "light"
    else:
        _LOGGER.warning(
            "Unknown device type '%s' for model '%s', cannot determine domain to hide",
            device_type,
            model,
        )
        return

    _LOGGER.debug(
        "Hiding ZHA %s entity for device type %s (model %s)",
        domain_to_hide,
        device_type,
        model,
    )

    # Find the ZHA entity for this device
    zha_entities = er.async_entries_for_config_entry(
        entity_registry, entry.data.get("zha_config_entry_id", "")
    )

    for entity_entry in zha_entities:
        # Look for matching platform and domain
        if (
            entity_entry.platform == "zha"
            and entity_entry.domain == domain_to_hide
            and entity_entry.device_id == entry.data.get("device_id")
        ):
            _LOGGER.debug(
                "Hiding ZHA %s entity: %s (%s)",
                domain_to_hide,
                entity_entry.entity_id,
                entity_entry.unique_id,
            )

            entity_registry.async_update_entity(
                entity_entry.entity_id,
                disabled_by=er.RegistryEntryDisabler.INTEGRATION,
                hidden_by=er.RegistryEntryHider.INTEGRATION,
            )


async def async_ensure_zha_entity_enabled(
    hass: HomeAssistant, entry: ConfigEntry
) -> None:
    """Ensure ZHA entity stays enabled (but hidden) for wrapper delegation.

    Args:
        hass: Home Assistant instance
        entry: Config entry for this device
    """
    entity_registry = er.async_get(hass)
    device_ieee = entry.data.get("device_ieee")
    model = entry.data.get("model", "")

    if not device_ieee:
        _LOGGER.warning(
            "No device IEEE in config entry, cannot ensure ZHA entity enabled"
        )
        return

    # Determine which domain based on device type
    device_type = get_device_type(model)

    if device_type == "window_covering":
        domain = "cover"
    elif device_type == "dimmer":
        domain = "light"
    else:
        _LOGGER.warning(
            "Unknown device type '%s' for model '%s', cannot determine domain to enable",
            device_type,
            model,
        )
        return

    # Find the ZHA entity for this device
    zha_entities = er.async_entries_for_config_entry(
        entity_registry, entry.data.get("zha_config_entry_id", "")
    )

    # Initialize tracked entities set if it doesn't exist
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN].setdefault("tracked_zha_entities", set())

    for entity_entry in zha_entities:
        # Look for matching platform and domain
        if (
            entity_entry.platform == "zha"
            and entity_entry.domain == domain
            and entity_entry.device_id == entry.data.get("device_id")
        ):
            # Track this entity for ongoing monitoring
            hass.data[DOMAIN]["tracked_zha_entities"].add(entity_entry.entity_id)

            # Re-enable if disabled by integration
            if entity_entry.disabled_by == er.RegistryEntryDisabler.INTEGRATION:
                _LOGGER.debug(
                    "ZHA %s entity %s is disabled by integration. "
                    "Re-enabling for wrapper delegation (entity remains hidden).",
                    domain,
                    entity_entry.entity_id,
                )
                try:
                    entity_registry.async_update_entity(
                        entity_entry.entity_id,
                        disabled_by=None,
                    )
                except Exception as err:
                    _LOGGER.error(
                        "Failed to re-enable ZHA %s entity %s: %s",
                        domain,
                        entity_entry.entity_id,
                        err,
                    )


def async_untrack_zha_entities(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Remove ZHA entities for this config entry from tracking.

    Args:
        hass: Home Assistant instance
        entry: Config entry being unloaded
    """
    entity_registry = er.async_get(hass)
    device_ieee = entry.data.get("device_ieee")
    model = entry.data.get("model", "")

    if not device_ieee:
        return

    device_type = get_device_type(model)

    if device_type == "window_covering":
        domain = "cover"
    elif device_type == "dimmer":
        domain = "light"
    else:
        return

    zha_entities = er.async_entries_for_config_entry(
        entity_registry, entry.data.get("zha_config_entry_id", "")
    )

    tracked = hass.data.get(DOMAIN, {}).get("tracked_zha_entities", set())

    for entity_entry in zha_entities:
        if (
            entity_entry.platform == "zha"
            and entity_entry.domain == domain
            and entity_entry.device_id == entry.data.get("device_id")
        ):
            tracked.discard(entity_entry.entity_id)
            _LOGGER.debug(
                "Untracked ZHA %s entity: %s",
                domain,
                entity_entry.entity_id,
            )


async def async_unhide_zha_entity(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Unhide the original ZHA entity when unloading integration.

    Args:
        hass: Home Assistant instance
        entry: Config entry for this device
    """
    entity_registry = er.async_get(hass)
    device_ieee = entry.data.get("device_ieee")
    model = entry.data.get("model", "")

    if not device_ieee:
        _LOGGER.warning("No device IEEE in config entry, cannot unhide ZHA entity")
        return

    device_type = get_device_type(model)

    if device_type == "window_covering":
        domain_to_unhide = "cover"
    elif device_type == "dimmer":
        domain_to_unhide = "light"
    else:
        _LOGGER.warning(
            "Unknown device type '%s' for model '%s', cannot determine domain to unhide",
            device_type,
            model,
        )
        return

    _LOGGER.debug(
        "Unhiding ZHA %s entity for device type %s (model %s)",
        domain_to_unhide,
        device_type,
        model,
    )

    zha_entities = er.async_entries_for_config_entry(
        entity_registry, entry.data.get("zha_config_entry_id", "")
    )

    for entity_entry in zha_entities:
        if (
            entity_entry.platform == "zha"
            and entity_entry.domain == domain_to_unhide
            and entity_entry.device_id == entry.data.get("device_id")
            and entity_entry.hidden_by == er.RegistryEntryHider.INTEGRATION
        ):
            _LOGGER.debug(
                "Unhiding ZHA %s entity: %s (%s)",
                domain_to_unhide,
                entity_entry.entity_id,
                entity_entry.unique_id,
            )

            updates: dict[str, Any] = {"hidden_by": None}
            if entity_entry.disabled_by == er.RegistryEntryDisabler.INTEGRATION:
                updates["disabled_by"] = None

            entity_registry.async_update_entity(
                entity_entry.entity_id,
                **updates,
            )


def recompute_verbose_flags(hass: HomeAssistant) -> None:
    """Recompute and store global verbose logging flags from all entries."""
    info = any(
        entry.options.get(OPTION_VERBOSE_INFO_LOGGING, False)
        for entry in hass.config_entries.async_entries(DOMAIN)
    )
    per_input = any(
        entry.options.get(OPTION_VERBOSE_INPUT_LOGGING, False)
        for entry in hass.config_entries.async_entries(DOMAIN)
    )
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN]["verbose_info_logging"] = info
    hass.data[DOMAIN]["verbose_input_logging"] = per_input


async def options_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update by recomputing verbose flags."""
    recompute_verbose_flags(hass)
