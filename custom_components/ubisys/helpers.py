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

        j1_calibration.py  ←┐
                             ├→ helpers.py → const.py
        d1_config.py       ←┘

    Both device-specific modules depend on helpers, but helpers doesn't
    depend on them. This is the Dependency Inversion Principle in action.

Separation of Concerns:
    - helpers.py: Generic utilities (cluster access, validation)
    - j1_calibration.py: J1-specific calibration logic
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
from typing import TYPE_CHECKING, Any

from async_timeout import timeout
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er

from .const import DOMAIN, VERBOSE_INFO_LOGGING, VERBOSE_INPUT_LOGGING

if TYPE_CHECKING:
    from zigpy.zcl import Cluster

_LOGGER = logging.getLogger(__name__)


def resolve_zha_gateway(zha_data: Any) -> Any | None:
    """Extract ZHA gateway object from Home Assistant's zha data container.

    Home Assistant has changed how it stores ZHA runtime data over time:
        - Older versions exposed a HAZHAData object directly at hass.data["zha"]
    - Transitional versions stored {"gateway": gateway}
    - Current versions store {entry_id: HAZHAData} (dict of entry-specific data)

    This helper inspects those layouts in order and returns the first gateway
    it finds. Callers are still responsible for logging errors if the result is
    None, since some call sites want different error wording.
    """

    if not zha_data:
        _LOGGER.debug("resolve_zha_gateway: zha_data is None or empty")
        return None

    # Enhanced diagnostics to understand ZHA data structure
    _LOGGER.debug(
        "resolve_zha_gateway: zha_data type=%s, is_dict=%s",
        type(zha_data).__name__,
        isinstance(zha_data, dict),
    )

    if isinstance(zha_data, dict):
        _LOGGER.debug(
            "resolve_zha_gateway: dict keys=%s",
            list(zha_data.keys())[:10],  # Limit to first 10 keys
        )
        # Show types of first few values
        value_types = {k: type(v).__name__ for k, v in list(zha_data.items())[:3]}
        _LOGGER.debug("resolve_zha_gateway: dict value types (sample)=%s", value_types)
    else:
        # Show object attributes
        attrs = [attr for attr in dir(zha_data) if not attr.startswith("_")][:10]
        _LOGGER.debug("resolve_zha_gateway: object attributes (sample)=%s", attrs)

    def iter_candidates(obj: Any) -> list[Any]:
        values: list[Any] = [obj]
        if isinstance(obj, dict):
            values.extend(obj.values())
        return values

    candidates = iter_candidates(zha_data)
    _LOGGER.debug(
        "resolve_zha_gateway: checking %d candidates (obj + dict values)",
        len(candidates),
    )

    for idx, candidate in enumerate(candidates):
        if not candidate:
            _LOGGER.debug(
                "resolve_zha_gateway: candidate[%d] is None/empty, skipping", idx
            )
            continue

        candidate_type = type(candidate).__name__
        has_gateway = hasattr(candidate, "gateway") or hasattr(
            candidate, "gateway_proxy"
        )
        _LOGGER.debug(
            "resolve_zha_gateway: candidate[%d] type=%s, has_gateway_attr=%s, is_dict=%s",
            idx,
            candidate_type,
            has_gateway,
            isinstance(candidate, dict),
        )

        # Try attribute access - check both "gateway" (older HA) and "gateway_proxy" (newer HA)
        for attr_name in ["gateway_proxy", "gateway"]:
            if hasattr(candidate, attr_name):
                gateway = getattr(candidate, attr_name)
                if gateway:
                    _LOGGER.debug(
                        "resolve_zha_gateway: ✓ Found gateway via .%s on candidate[%d] (type=%s)",
                        attr_name,
                        idx,
                        candidate_type,
                    )
                    return gateway
                _LOGGER.debug(
                    "resolve_zha_gateway: candidate[%d].%s exists but is None/empty",
                    idx,
                    attr_name,
                )

        # Try dict key access
        if isinstance(candidate, dict):
            if "gateway" in candidate:
                gateway = candidate.get("gateway")
                if gateway:
                    _LOGGER.debug(
                        "resolve_zha_gateway: ✓ Found gateway via dict key on candidate[%d]",
                        idx,
                    )
                    return gateway
                _LOGGER.debug(
                    "resolve_zha_gateway: candidate[%d]['gateway'] exists but is None/empty",
                    idx,
                )
            else:
                _LOGGER.debug(
                    "resolve_zha_gateway: candidate[%d] dict has no 'gateway' key (keys=%s)",
                    idx,
                    list(candidate.keys())[:5],
                )

    _LOGGER.warning(
        "resolve_zha_gateway: ✗ No gateway found after checking %d candidates. "
        "ZHA data structure may have changed. Please report this with debug logs.",
        len(candidates),
    )
    return None


# ==============================================================================
# DEVICE REGISTRY UTILITIES
# ==============================================================================
# Simple utility functions for extracting information from device registry
# entries. These are used by multiple modules to avoid code duplication.


def extract_model_from_device(device: dr.DeviceEntry) -> str | None:
    """Extract model string from device entry.

    The device model field typically contains the model code followed by
    hardware version in parentheses (e.g., "J1 (5502)", "D1-R (5603)").
    This function extracts just the model code part.

    Args:
        device: Device registry entry

    Returns:
        Model string (e.g., "J1", "D1-R", "S1") or None if not found

    Example:
        >>> device.model = "J1 (5502)"
        >>> extract_model_from_device(device)
        "J1"
        >>> device.model = "D1-R (5603)"
        >>> extract_model_from_device(device)
        "D1-R"

    Why This is Shared:
        Multiple modules need to extract model strings from device entries:
        - device_trigger.py: Determine available triggers based on model
        - input_monitor.py: Set up monitoring for devices with physical inputs
        - config_flow.py: Validate device information during setup

        Sharing prevents code duplication and ensures consistent parsing.
    """
    if not device.model:
        return None

    # Extract just the model code (e.g., "J1" from "J1 (5502)")
    # Handle both "J1" and "J1-R" formats
    model: str = device.model.split("(")[0].strip()
    return model if model else None


def extract_ieee_from_device(device: dr.DeviceEntry) -> str | None:
    """Extract IEEE address from device entry.

    The IEEE address uniquely identifies a Zigbee device and is stored
    in the device's identifiers tuple with the "zha" domain prefix.

    Args:
        device: Device registry entry

    Returns:
        IEEE address string (e.g., "00:1f:ee:00:00:00:00:01") or None if not found

    Example:
        >>> device.identifiers = {("zha", "00:1f:ee:00:00:00:00:01")}
        >>> extract_ieee_from_device(device)
        "00:1f:ee:00:00:00:00:01"

    Technical Details:
        ZHA stores device identifiers as tuples in the format:
        ("zha", "<ieee_address>")

        This function searches through all identifiers to find the ZHA one
        and extracts the IEEE address from the second element.

    Why This is Shared:
        Multiple modules need to extract IEEE addresses from device entries:
        - device_trigger.py: Get device IEEE for event filtering
        - input_monitor.py: Get device IEEE for ZHA cluster access
        - config_flow.py: Validate device identity during setup

        Sharing prevents code duplication and ensures consistent extraction.
    """
    # IEEE address is in device identifiers
    for identifier in device.identifiers:
        if identifier[0] == "zha":  # ZHA domain identifier
            # Format: ("zha", "00:1f:ee:00:00:00:00:01")
            if len(identifier) > 1:
                return str(identifier[1])
    return None


# ==============================================================================
# ZIGBEE CLUSTER ACCESS
# ==============================================================================
# Functions for accessing Zigbee clusters via ZHA integration


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
        j1_calibration.py and d1_config.py.

    See Also:
        - j1_calibration.py: Uses this for WindowCovering cluster access
        - d1_config.py: Uses this for Ballast cluster access
    """
    # Get ZHA integration data
    zha_data = hass.data.get("zha")
    if not zha_data:
        _LOGGER.error("ZHA integration not loaded")
        return None

    gateway = resolve_zha_gateway(zha_data)
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
        # Handle both old API (gateway.application_controller.devices) and new API (gateway_proxy.gateway.devices)
        if hasattr(gateway, "application_controller"):
            # Old API: direct gateway object
            devices = gateway.application_controller.devices
        elif hasattr(gateway, "gateway"):
            # New API: ZHAGatewayProxy wrapping gateway
            devices = gateway.gateway.devices
        else:
            _LOGGER.error(
                "Gateway object has no known device access pattern. Type: %s, Attributes: %s",
                type(gateway).__name__,
                [attr for attr in dir(gateway) if not attr.startswith("_")][:20],
            )
            return None

        device = devices.get(device_eui64)
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
        - j1_calibration.py: Uses this to get device info for calibration
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
        - j1_calibration.py: Validates cover entity before calibration
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
        - j1_calibration.py: Finds ZHA cover entity for position monitoring
        - cover.py: Finds ZHA cover entity for state delegation
        - light.py: (Future) Finds ZHA light entity for state delegation
    """
    entity_registry = er.async_get(hass)
    entities = er.async_entries_for_device(entity_registry, device_id)

    from typing import cast

    for entity_entry in entities:
        if entity_entry.platform == "zha" and entity_entry.domain == domain:
            return cast(str, entity_entry.entity_id)

    return None


async def get_device_setup_cluster(
    hass: HomeAssistant,
    device_ieee: str,
) -> Cluster | None:
    """Get the DeviceSetup cluster (0xFC00) from a Ubisys device.

    This is a convenience wrapper around get_cluster() specifically for
    accessing the DeviceSetup cluster which is used for input configuration
    on all Ubisys devices (J1, D1, S1).

    The DeviceSetup cluster is always located at endpoint 232 for all
    Ubisys devices and provides access to:
    - InputConfigurations (0x0000): Enable/disable/invert inputs
    - InputActions (0x0001): Input behavior micro-code

    Args:
        hass: Home Assistant instance
        device_ieee: Device IEEE address as string

    Returns:
        DeviceSetup cluster object, or None if not found

    Example:
        >>> cluster = await get_device_setup_cluster(hass, "00:12:4b:00:1c:a1:b2:c3")
        >>> # Read InputActions
        >>> result = await cluster.read_attributes(
        ...     [0x0001],
        ...     manufacturer=0x10F2
        ... )
        >>> input_actions_data = result[0][0x0001]

    See Also:
        - input_monitor.py: Uses this to read InputActions for event correlation
        - s1_config.py: Uses this for S1 input configuration
        - d1_config.py: Uses this for D1 input configuration
    """
    DEVICE_SETUP_ENDPOINT = 232
    DEVICE_SETUP_CLUSTER_ID = 0xFC00

    return await get_cluster(
        hass,
        device_ieee,
        DEVICE_SETUP_CLUSTER_ID,
        DEVICE_SETUP_ENDPOINT,
        "DeviceSetup",
    )


# ==============================================================================
# ZCL COMMAND WITH TIMEOUT/RETRY
# ==============================================================================


async def async_zcl_command(
    cluster: "Cluster",
    command: str,
    *args: Any,
    timeout_s: float = 10.0,
    retries: int = 1,
    **kwargs: Any,
) -> None:
    """Send a Zigbee cluster command with timeout and limited retries.

    Args:
        cluster: Zigbee cluster
        command: Command name (e.g., "up_open", "down_close", "stop")
        *args: Positional args passed to cluster.command
        timeout_s: Timeout per attempt
        retries: Number of retries on failure
        **kwargs: Keyword args for cluster.command

    Raises:
        HomeAssistantError on failure
    """
    attempt = 0
    last_err: Exception | None = None
    while attempt <= retries:
        try:
            _LOGGER.debug(
                "ZCL cmd attempt %d: %s(%s)",
                attempt + 1,
                command,
                ", ".join(map(str, args)),
            )
            async with timeout(timeout_s):
                # Execute command and ignore any return value; callers rely on
                # success/exception rather than command response payload.
                await cluster.command(command, *args, **kwargs)
                return None
        except Exception as err:
            last_err = err
            attempt += 1
            if attempt > retries:
                break
            _LOGGER.debug("ZCL cmd retry after error: %s", err)
    raise HomeAssistantError(f"Cluster command failed: {command}: {last_err}")


# ==============================================================================
# ATTR WRITE + READBACK VERIFICATION
# ==============================================================================
# Shared helper to write manufacturer/standard attributes and verify by reading
# them back. This reduces duplication across J1 tuning and D1 configuration.


async def async_write_and_verify_attrs(
    cluster: "Cluster",
    attrs: dict[int, int],
    *,
    manufacturer: int | None = None,
    write_timeout: float = 10.0,
    read_timeout: float = 10.0,
    retries: int = 1,
) -> None:
    """Write attributes on a cluster, then read and verify values.

    Args:
        cluster: Zigbee cluster object (from get_cluster/get_device_setup_cluster)
        attrs: Mapping of attribute_id -> value to write
        manufacturer: Manufacturer code if required (e.g., 0x10F2 for Ubisys)

    Raises:
        HomeAssistantError: If write fails or readback does not match.

    Notes:
        - For manufacturer-specific attributes, pass manufacturer=0x10F2 (Ubisys).
        - For standard ZCL attributes, manufacturer=None is fine.
    """
    attempt = 0
    last_err: Exception | None = None
    while attempt <= retries:
        try:
            _LOGGER.debug(
                "Write+Verify: attempt %d writing attrs %s (mfg=%s)",
                attempt + 1,
                attrs,
                manufacturer,
            )
            async with timeout(write_timeout):
                result = await cluster.write_attributes(
                    attrs, manufacturer=manufacturer
                )
            _LOGGER.debug("Write+Verify: Write result: %s", result)

            # Read back the attributes we wrote
            read_ids = list(attrs.keys())
            async with timeout(read_timeout):
                readback = await cluster.read_attributes(
                    read_ids, manufacturer=manufacturer
                )
            _LOGGER.debug("Write+Verify: Readback result: %s", readback)

            # Normalize response
            if isinstance(readback, list) and readback:
                readback = readback[0]

            mismatches: dict[int, dict[str, int | None]] = {}
            for attr_id, expected in attrs.items():
                actual = readback.get(attr_id)
                if actual != expected:
                    mismatches[attr_id] = {"expected": expected, "actual": actual}

            if mismatches:
                raise HomeAssistantError(f"Attribute verification failed: {mismatches}")

            return

        except Exception as err:  # capture and retry
            last_err = err
            attempt += 1
            if attempt > retries:
                break
            _LOGGER.debug("Write+Verify: retrying after error: %s", err)

    if isinstance(last_err, HomeAssistantError):
        raise last_err
    raise HomeAssistantError(f"Attribute write/verify failed: {last_err}")


# ==============================================================================
# VERBOSE LOGGING FLAGS (GLOBAL RUNTIME)
# ==============================================================================


def is_verbose_info_logging(hass: HomeAssistant | None) -> bool:
    """Return whether verbose INFO logging is enabled.

    Prefers runtime flags in hass.data[DOMAIN], falling back to constants.
    """
    try:
        if hass is None:
            return VERBOSE_INFO_LOGGING
        domain_data = hass.data.get(DOMAIN, {})
        return bool(domain_data.get("verbose_info_logging", VERBOSE_INFO_LOGGING))
    except Exception:
        return VERBOSE_INFO_LOGGING


def is_verbose_input_logging(hass: HomeAssistant | None) -> bool:
    """Return whether per-input INFO logs are enabled.

    Prefers runtime flags in hass.data[DOMAIN], falling back to constants.
    """
    try:
        if hass is None:
            return VERBOSE_INPUT_LOGGING
        domain_data = hass.data.get(DOMAIN, {})
        return bool(domain_data.get("verbose_input_logging", VERBOSE_INPUT_LOGGING))
    except Exception:
        return VERBOSE_INPUT_LOGGING
