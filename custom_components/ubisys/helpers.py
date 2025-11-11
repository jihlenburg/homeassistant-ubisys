"""Shared helper utilities for Ubisys integration.

This module provides common utilities used by both J1 (window covering) and
D1 (dimmer) implementations. Functions here handle generic tasks like:
- Zigbee cluster access
- Entity validation
- Device information lookup

Architecture Note:
    This is a "leaf module" - it doesn't import from other integration modules
    (only from HA core and const.py). This prevents circular dependencies and
    makes the dependency tree clear:

        calibration.py  ←┐
                         ├→ helpers.py → const.py
        d1_config.py   ←┘

    Both device-specific modules depend on helpers, but helpers doesn't
    depend on them. This is the Dependency Inversion Principle in action.

Separation of Concerns:
    - helpers.py: Generic utilities (cluster access, validation)
    - calibration.py: J1-specific calibration logic
    - d1_config.py: D1-specific configuration logic

Why Shared:
    These functions have IDENTICAL logic for all device types. Sharing them:
    - Reduces code duplication
    - Provides single source of truth
    - Makes testing easier (mock once, use everywhere)
    - Simplifies maintenance (fix bug once, all devices benefit)
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er

from .const import DOMAIN, UBISYS_MANUFACTURER_CODE

if TYPE_CHECKING:
    from zigpy.zcl import Cluster

_LOGGER = logging.getLogger(__name__)


async def get_cluster(
    hass: HomeAssistant,
    device_ieee: str,
    cluster_id: int,
    endpoint_id: int,
    cluster_name: str = "Unknown",
) -> Cluster | None:
    """Get a Zigbee cluster from a device via ZHA gateway.

    This is the foundational function for all direct Zigbee cluster access.
    Both J1 and D1 use this to get their respective clusters for reading/writing
    attributes and sending commands.

    How It Works:
        1. Convert IEEE address string → EUI64 object (Zigbee format)
        2. Access ZHA integration data to get gateway
        3. Look up device in gateway's device registry by IEEE
        4. Find the specified endpoint on the device
        5. Find the specified cluster within that endpoint
        6. Return cluster object for direct Zigbee operations

    Why Direct Cluster Access:
        Some operations (like calibration, phase mode configuration) require
        access to manufacturer-specific attributes or precise command timing
        that Home Assistant's entity abstraction doesn't provide.

    Args:
        hass: Home Assistant instance (for accessing ZHA data)
        device_ieee: Device IEEE address as string (e.g., "00:12:4b:00:1c:a1:b2:c3")
        cluster_id: Zigbee cluster ID (e.g., 0x0102 for WindowCovering, 0x0301 for Ballast)
        endpoint_id: Endpoint number where cluster resides (e.g., 2 for J1, 4 for D1)
        cluster_name: Human-readable cluster name for error messages

    Returns:
        Cluster object for direct Zigbee access, or None if not found

    Raises:
        HomeAssistantError: If IEEE address format is invalid

    Example Usage:
        # J1: Get WindowCovering cluster for calibration
        >>> cluster = await get_cluster(
        ...     hass,
        ...     "00:12:4b:00:1c:a1:b2:c3",
        ...     0x0102,  # WindowCovering
        ...     2,       # J1 endpoint
        ...     "WindowCovering"
        ... )
        >>> await cluster.write_attributes({0x0017: 0x02})  # Enter calibration

        # D1: Get Ballast cluster for phase mode configuration
        >>> cluster = await get_cluster(
        ...     hass,
        ...     "00:12:4b:00:1c:d4:e5:f6",
        ...     0x0301,  # Ballast
        ...     4,       # D1 dimmer endpoint
        ...     "Ballast"
        ... )
        >>> await cluster.write_attributes({0x0011: 15})  # Set min level

    Why This is Shared:
        The mechanism to access Zigbee clusters via ZHA is identical for all
        device types. Only the cluster_id and endpoint_id parameters differ.
        Sharing this prevents duplicating the ZHA gateway access logic in both
        calibration.py and d1_config.py.

    See Also:
        - calibration.py: Uses this for WindowCovering cluster access
        - d1_config.py: Uses this for Ballast cluster access
    """
    # Get ZHA integration data
    zha_data = hass.data.get("zha")
    if not zha_data:
        _LOGGER.error("ZHA integration not loaded")
        return None

    gateway = zha_data.get("gateway")
    if not gateway:
        _LOGGER.error("ZHA gateway not found")
        return None

    # Convert IEEE string to EUI64 object
    try:
        from zigpy.types import EUI64

        try:
            device_eui64 = EUI64.convert(device_ieee)
        except (ValueError, TypeError) as err:
            _LOGGER.error("Invalid IEEE address format: %s", device_ieee)
            raise HomeAssistantError(
                f"Invalid device IEEE address: {device_ieee}"
            ) from err

        # Get device from ZHA gateway
        device = gateway.application_controller.devices.get(device_eui64)
        if not device:
            _LOGGER.error("Device not found in ZHA gateway: %s", device_ieee)
            return None

        # Get endpoint
        endpoint = device.endpoints.get(endpoint_id)
        if not endpoint:
            _LOGGER.error(
                "Endpoint %d not found for device: %s", endpoint_id, device_ieee
            )
            return None

        # Get cluster from endpoint
        cluster = endpoint.in_clusters.get(cluster_id)
        if not cluster:
            _LOGGER.error(
                "%s cluster (0x%04X) not found on endpoint %d for device: %s",
                cluster_name,
                cluster_id,
                endpoint_id,
                device_ieee,
            )
            return None

        _LOGGER.debug(
            "Successfully retrieved %s cluster for device %s",
            cluster_name,
            device_ieee,
        )
        return cluster

    except Exception as err:
        _LOGGER.error("Error accessing device cluster: %s", err)
        return None


async def get_entity_device_info(
    hass: HomeAssistant,
    entity_id: str,
) -> tuple[str, str, str]:
    """Get device information from an entity ID.

    Looks up the parent device information for a given entity. This is used
    to get the device's IEEE address and model, which are needed for direct
    Zigbee cluster access.

    Args:
        hass: Home Assistant instance
        entity_id: Entity ID (e.g., "cover.bedroom_j1" or "light.bedroom_d1")

    Returns:
        Tuple of (device_id, device_ieee, model)
        - device_id: Home Assistant device registry ID
        - device_ieee: Zigbee IEEE address (string)
        - model: Device model (e.g., "J1", "D1")

    Raises:
        HomeAssistantError: If entity not found, device not found, or
                           required data (IEEE, model) is missing

    Example:
        >>> device_id, ieee, model = await get_entity_device_info(
        ...     hass, "cover.bedroom_j1"
        ... )
        >>> print(f"Model: {model}, IEEE: {ieee}")
        Model: J1, IEEE: 00:12:4b:00:1c:a1:b2:c3

    Why This is Shared:
        Both J1 and D1 entities need to look up their parent device to get
        the IEEE address for cluster access. The lookup mechanism is identical.

    See Also:
        - calibration.py: Uses this to get device info for calibration
        - d1_config.py: Uses this to get device info for configuration
    """
    # Get entity registry
    entity_registry = er.async_get(hass)
    entity_entry = entity_registry.async_get(entity_id)

    if not entity_entry:
        raise HomeAssistantError(f"Entity {entity_id} not found in registry")

    # Get device_id
    device_id = entity_entry.device_id
    if not device_id:
        raise HomeAssistantError(f"Entity {entity_id} has no associated device")

    # Get config entry to extract device info
    config_entry_id = entity_entry.config_entry_id
    if not config_entry_id:
        raise HomeAssistantError(f"Entity {entity_id} has no config entry")

    config_entry = hass.config_entries.async_get_entry(config_entry_id)
    if not config_entry or config_entry.domain != DOMAIN:
        raise HomeAssistantError(
            f"Entity {entity_id} config entry not found or not ubisys"
        )

    # Extract device info from config entry
    device_ieee = config_entry.data.get("device_ieee")
    model = config_entry.data.get("model")

    if not device_ieee:
        raise HomeAssistantError(
            f"Device IEEE address not found in config entry for {entity_id}"
        )

    if not model:
        raise HomeAssistantError(
            f"Device model not found in config entry for {entity_id}"
        )

    return device_id, device_ieee, model


async def validate_ubisys_entity(
    hass: HomeAssistant,
    entity_id: str,
    expected_domain: str | None = None,
) -> None:
    """Validate that an entity is a Ubisys entity and ready for operations.

    Performs common pre-flight checks used by service handlers to fail fast
    with clear error messages rather than failing midway through operations.

    Checks Performed:
        1. Entity exists in entity registry
        2. Entity platform is "ubisys" (our integration)
        3. Entity domain matches expected (if specified)
        4. Entity is available (not offline/unavailable)

    Args:
        hass: Home Assistant instance
        entity_id: Entity to validate (e.g., "cover.bedroom_j1")
        expected_domain: Expected domain ("cover", "light", etc.) or None to skip

    Raises:
        HomeAssistantError: With specific error message indicating which check failed:
            - "Entity not found" → Entity doesn't exist
            - "Not a Ubisys entity" → Wrong platform
            - "Expected domain X, got Y" → Wrong entity type
            - "Entity is unavailable" → Device offline

    Example:
        # Validate this is a Ubisys cover entity
        >>> await validate_ubisys_entity(
        ...     hass, "cover.bedroom_j1", expected_domain="cover"
        ... )
        # Raises if not a Ubisys cover or if offline

        # Validate this is any Ubisys entity
        >>> await validate_ubisys_entity(hass, "light.bedroom_d1")
        # Only checks platform and availability

    Why This is Shared:
        Validation logic is identical for covers, lights, and future switches.
        Sharing prevents duplication and ensures consistent error messages.

    See Also:
        - calibration.py: Validates cover entity before calibration
        - d1_config.py: Validates light entity before configuration
    """
    # Check 1: Entity exists in registry
    entity_registry = er.async_get(hass)
    entity_entry = entity_registry.async_get(entity_id)

    if not entity_entry:
        raise HomeAssistantError(
            f"Entity {entity_id} not found. Please check the entity ID."
        )

    # Check 2: Entity platform is "ubisys"
    if entity_entry.platform != DOMAIN:
        raise HomeAssistantError(
            f"Entity {entity_id} is not a Ubisys entity. "
            f"Expected platform '{DOMAIN}', got '{entity_entry.platform}'"
        )

    # Check 3: Entity domain matches expected (if specified)
    if expected_domain and entity_entry.domain != expected_domain:
        raise HomeAssistantError(
            f"Entity {entity_id} has wrong domain. "
            f"Expected '{expected_domain}', got '{entity_entry.domain}'"
        )

    # Check 4: Entity is available
    state = hass.states.get(entity_id)
    if not state:
        raise HomeAssistantError(
            f"Entity {entity_id} state not found. Device may not be initialized."
        )

    if state.state == "unavailable":
        raise HomeAssistantError(
            f"Entity {entity_id} is unavailable. "
            f"Ensure the device is powered on and connected to the Zigbee network."
        )

    _LOGGER.debug("✓ Validation passed for %s", entity_id)


async def find_zha_entity_for_device(
    hass: HomeAssistant,
    device_id: str,
    domain: str,
) -> str | None:
    """Find the ZHA entity for a device in a specific domain.

    This is used to find the underlying ZHA entity that our wrapper entities
    delegate to. For example, finding the ZHA cover entity that a Ubisys
    cover wrapper monitors for state changes.

    Args:
        hass: Home Assistant instance
        device_id: Device registry ID
        domain: Entity domain to search for ("cover", "light", etc.)

    Returns:
        ZHA entity ID if found, None otherwise

    Example:
        >>> zha_entity = await find_zha_entity_for_device(
        ...     hass, device_id, "cover"
        ... )
        >>> print(zha_entity)
        cover.bedroom_j1_2  # The ZHA cover entity

    Why This is Shared:
        Both J1 and D1 might need to find their underlying ZHA entities.
        The search logic is identical across domains.

    See Also:
        - calibration.py: Finds ZHA cover entity for position monitoring
        - cover.py: Finds ZHA cover entity for state delegation
        - light.py: (Future) Finds ZHA light entity for state delegation
    """
    entity_registry = er.async_get(hass)
    entities = er.async_entries_for_device(entity_registry, device_id)

    for entity_entry in entities:
        if entity_entry.platform == "zha" and entity_entry.domain == domain:
            return entity_entry.entity_id

    return None
