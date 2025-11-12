"""D1 Universal Dimmer Configuration Services.

This module provides configuration services specifically for Ubisys D1 and D1-R
universal dimmers. These services expose manufacturer-specific features that are
not available through Home Assistant's standard light platform.

Services Provided:
    1. configure_d1_phase_mode: Configure phase control mode (automatic/forward/reverse)
    2. configure_d1_ballast: Configure ballast min/max brightness levels
    3. configure_d1_inputs: Configure physical switch inputs (planned Phase 3)

Architecture Note:
    This is a device-specific module (D1 only) that depends on:
    - helpers.py: Shared utilities (cluster access, validation)
    - const.py: Shared constants (phase modes, ballast limits, endpoints)

    This separation keeps D1-specific logic isolated from J1 calibration logic,
    following the Single Responsibility Principle.

Why These Services Are Needed:
    The D1 exposes several manufacturer-specific features that Home Assistant's
    standard ZHA light integration doesn't provide:

    1. Phase Control Mode (CRITICAL - safety issue):
       - Automatic (0): Auto-detect load type (resistive/inductive/capacitive)
       - Forward (1): Leading edge dimming (for resistive/inductive loads)
       - Reverse (2): Trailing edge dimming (for capacitive loads like LEDs)
       - Wrong mode can cause flickering, buzzing, or even damage
       - Home Assistant ZHA doesn't expose this configuration

    2. Ballast Min/Max Levels (CRITICAL - LED compatibility):
       - Min level: Prevents LED flickering at low brightness
       - Max level: Limits maximum brightness for energy savings
       - Essential for proper LED dimming behavior
       - Home Assistant ZHA doesn't expose these attributes

    3. Physical Input Configuration (convenience):
       - Configure wall switches as momentary/toggle/decoupled
       - Advanced feature for power users
       - Not exposed by standard ZHA integration

See Also:
    - custom_zha_quirks/ubisys_d1.py: ZHA quirk that exposes these clusters
    - helpers.py: Shared cluster access utilities
    - const.py: D1-specific constants (phase modes, ballast limits)
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from .const import (
    BALLAST_ATTR_MAX_LEVEL,
    BALLAST_ATTR_MIN_LEVEL,
    BALLAST_LEVEL_MAX,
    BALLAST_LEVEL_MIN,
    CLUSTER_BALLAST,
    CLUSTER_DEVICE_SETUP,
    CLUSTER_DIMMER_SETUP,
    D1_DIMMABLE_LIGHT_ENDPOINT,
    D1_DIMMER_ENDPOINT,
    DEVICE_SETUP_ATTR_INPUT_ACTIONS,
    DEVICE_SETUP_ATTR_INPUT_CONFIGS,
    DIMMER_SETUP_ATTR_MODE,
    PHASE_MODE_AUTOMATIC,
    PHASE_MODE_FORWARD,
    PHASE_MODE_NAMES,
    PHASE_MODE_REVERSE,
    PHASE_MODES,
    UBISYS_MANUFACTURER_CODE,
)
from .helpers import get_cluster, get_entity_device_info, validate_ubisys_entity

if TYPE_CHECKING:
    from zigpy.zcl import Cluster

_LOGGER = logging.getLogger(__name__)


async def async_configure_phase_mode(
    hass: HomeAssistant,
    entity_id: str,
    phase_mode: str,
) -> None:
    """Configure D1 phase control mode.

    Phase control mode determines how the D1 dims connected loads. This is a
    CRITICAL safety feature - incorrect configuration can cause:
    - LED flickering or buzzing
    - Excessive heat generation
    - Shortened bulb lifespan
    - Potential damage to dimmer or bulbs

    Phase Modes:
        - automatic (0): Auto-detect load type (default, safest)
        - forward (1): Leading edge (for resistive/inductive loads)
        - reverse (2): Trailing edge (for capacitive loads like LEDs)

    When to Use:
        - automatic: Always start here (default)
        - forward: Only if experiencing issues with resistive loads
        - reverse: Only if experiencing LED flickering with automatic mode

    How It Works:
        1. Validate entity is a Ubisys D1 light entity
        2. Get device IEEE address from entity registry
        3. Access D1's Ballast cluster (0x0301) on endpoint 4
        4. Write phase control mode attribute (exact location TBD via testing)
        5. Verify write succeeded

    Note on Implementation:
        The exact attribute ID for phase control mode is TBD. Based on other
        Ubisys devices, it's likely either:
        - A manufacturer-specific attribute in Ballast cluster (0x0301)
        - An attribute in DeviceSetup cluster (0xFC00)

        Testing with a real D1 device will reveal the correct location.
        For now, this implementation uses a placeholder approach.

    Args:
        hass: Home Assistant instance
        entity_id: D1 light entity ID (e.g., "light.bedroom_d1")
        phase_mode: Phase mode string ("automatic", "forward", or "reverse")

    Raises:
        HomeAssistantError: If:
            - Entity validation fails (not found, wrong type, offline)
            - Device not found in ZHA
            - Cluster not accessible
            - Write operation fails
            - Invalid phase mode specified

    Example:
        >>> await async_configure_phase_mode(
        ...     hass, "light.bedroom_d1", "automatic"
        ... )

    See Also:
        - custom_zha_quirks/ubisys_d1.py: D1 quirk that exposes Ballast cluster
        - const.py: PHASE_MODES mapping
        - Ubisys D1 Technical Reference Manual (phase control section)
    """
    _LOGGER.debug(
        "D1 Config: Starting phase mode configuration for %s (mode=%s)",
        entity_id,
        phase_mode,
    )

    # Step 1: Validate entity
    await validate_ubisys_entity(hass, entity_id, expected_domain="light")
    _LOGGER.debug("D1 Config: ✓ Entity validation passed")

    # Step 2: Validate phase mode parameter
    if phase_mode not in PHASE_MODES:
        raise HomeAssistantError(
            f"Invalid phase mode '{phase_mode}'. "
            f"Valid modes: {', '.join(PHASE_MODES.keys())}"
        )

    phase_mode_value = PHASE_MODES[phase_mode]
    _LOGGER.debug(
        "D1 Config: ✓ Phase mode validated: %s = %d",
        phase_mode,
        phase_mode_value,
    )

    # Step 3: Get device info
    device_id, device_ieee, model = await get_entity_device_info(hass, entity_id)
    _LOGGER.debug(
        "D1 Config: ✓ Device info: model=%s, ieee=%s",
        model,
        device_ieee,
    )

    # Step 4: Verify this is a D1 model
    if model not in ["D1", "D1-R"]:
        raise HomeAssistantError(
            f"Entity {entity_id} is not a D1 dimmer (model: {model}). "
            f"Phase mode configuration only applies to D1/D1-R models."
        )
    _LOGGER.debug("D1 Config: ✓ Model verification passed")

    # Step 5: Access DimmerSetup cluster (0xFC01) on endpoint 1
    # According to D1 Technical Reference Section 7.2.8:
    # - Cluster ID: 0xFC01 (DimmerSetup, manufacturer-specific)
    # - Endpoint: 1 (Dimmable Light endpoint)
    # - Attribute: 0x0002 (Mode)
    # - Manufacturer Code: 0x10F2 (required)
    cluster = await get_cluster(
        hass,
        device_ieee,
        CLUSTER_DIMMER_SETUP,
        D1_DIMMABLE_LIGHT_ENDPOINT,
        "DimmerSetup",
    )

    if not cluster:
        raise HomeAssistantError(
            f"Could not access DimmerSetup cluster for {entity_id}. "
            f"Ensure the device is online and the D1 quirk is loaded."
        )
    _LOGGER.debug("D1 Config: ✓ DimmerSetup cluster accessed")

    # Step 6: Write phase control mode
    # IMPORTANT: According to D1 technical reference, the Mode attribute
    # is only writable when the output is OFF. If the light is currently ON,
    # the write will fail. The service should be called when light is off.
    _LOGGER.info(
        "D1 Config: Configuring phase mode for %s: %s (%d)",
        entity_id,
        phase_mode,
        phase_mode_value,
    )

    try:
        # Write the Mode attribute with manufacturer code
        # The quirk will automatically inject the manufacturer code (0x10F2)
        result = await cluster.write_attributes(
            {DIMMER_SETUP_ATTR_MODE: phase_mode_value},
            manufacturer=UBISYS_MANUFACTURER_CODE,
        )
        _LOGGER.debug("D1 Config: Write result: %s", result)

        # Check if write succeeded
        # Note: result is a list of WriteAttributesResponse objects
        if result and result[0].status != 0:
            status_code = result[0].status
            error_msg = f"Failed to write phase mode: status={status_code}"

            # Provide helpful error message if write failed
            if status_code == 0x87:  # INVALID_VALUE
                error_msg += (
                    " (Invalid value - ensure output is OFF before changing mode)"
                )
            elif status_code == 0x88:  # READ_ONLY
                error_msg += (
                    " (Attribute is read-only - ensure output is OFF)"
                )

            _LOGGER.error("D1 Config: %s", error_msg)
            raise HomeAssistantError(error_msg)

        _LOGGER.info(
            "D1 Config: ✓ Successfully configured phase mode: %s -> %s",
            entity_id,
            phase_mode,
        )

    except HomeAssistantError:
        # Re-raise HomeAssistantError as-is (already formatted)
        raise
    except Exception as err:
        _LOGGER.error("D1 Config: Failed to write phase mode: %s", err)
        raise HomeAssistantError(
            f"Failed to configure phase mode for {entity_id}: {err}"
        ) from err


async def async_configure_ballast(
    hass: HomeAssistant,
    entity_id: str,
    min_level: int | None = None,
    max_level: int | None = None,
) -> None:
    """Configure D1 ballast minimum and maximum brightness levels.

    Ballast configuration controls the dimming range of the D1. This is
    essential for proper LED dimming:

    Min Level (1-254):
        - Prevents LED flickering at low brightness
        - Set to lowest brightness where LED doesn't flicker
        - Typical values: 10-20 for most LEDs
        - Lower values = smoother dimming, but may cause flickering

    Max Level (1-254):
        - Limits maximum brightness
        - Use for energy savings or to protect sensitive loads
        - Typical value: 254 (no limit)
        - Lower values = less maximum brightness

    Important:
        - min_level must be < max_level
        - Both values must be in range 1-254 (0 and 255 are invalid)
        - You can set one or both parameters
        - Values are stored persistently in the device

    How It Works:
        1. Validate entity is a Ubisys D1 light entity
        2. Validate min/max level values (range, min < max)
        3. Get device IEEE address from entity registry
        4. Access D1's Ballast cluster (0x0301) on endpoint 4
        5. Write ballast_min_level (0x0011) and/or ballast_max_level (0x0012)
        6. Verify write succeeded

    Args:
        hass: Home Assistant instance
        entity_id: D1 light entity ID (e.g., "light.bedroom_d1")
        min_level: Minimum brightness level (1-254), or None to leave unchanged
        max_level: Maximum brightness level (1-254), or None to leave unchanged

    Raises:
        HomeAssistantError: If:
            - Entity validation fails
            - min_level or max_level out of range (1-254)
            - min_level >= max_level
            - Both min_level and max_level are None
            - Device not found or offline
            - Write operation fails

    Example:
        # Set minimum brightness to 15 (prevents flickering)
        >>> await async_configure_ballast(
        ...     hass, "light.bedroom_d1", min_level=15
        ... )

        # Set maximum brightness to 200 (limit brightness)
        >>> await async_configure_ballast(
        ...     hass, "light.bedroom_d1", max_level=200
        ... )

        # Set both min and max
        >>> await async_configure_ballast(
        ...     hass, "light.bedroom_d1", min_level=15, max_level=200
        ... )

    See Also:
        - custom_zha_quirks/ubisys_d1.py: D1 quirk exposing Ballast cluster
        - const.py: BALLAST_LEVEL_MIN, BALLAST_LEVEL_MAX constants
        - ZCL Spec 5.3: Ballast Configuration Cluster
    """
    _LOGGER.debug(
        "D1 Config: Starting ballast configuration for %s (min=%s, max=%s)",
        entity_id,
        min_level,
        max_level,
    )

    # Step 1: Validate entity
    await validate_ubisys_entity(hass, entity_id, expected_domain="light")
    _LOGGER.debug("D1 Config: ✓ Entity validation passed")

    # Step 2: Validate parameters
    if min_level is None and max_level is None:
        raise HomeAssistantError(
            "At least one of min_level or max_level must be specified"
        )

    # Validate min_level range
    if min_level is not None and not (BALLAST_LEVEL_MIN <= min_level <= BALLAST_LEVEL_MAX):
        raise HomeAssistantError(
            f"min_level must be between {BALLAST_LEVEL_MIN} and {BALLAST_LEVEL_MAX}, "
            f"got {min_level}"
        )

    # Validate max_level range
    if max_level is not None and not (BALLAST_LEVEL_MIN <= max_level <= BALLAST_LEVEL_MAX):
        raise HomeAssistantError(
            f"max_level must be between {BALLAST_LEVEL_MIN} and {BALLAST_LEVEL_MAX}, "
            f"got {max_level}"
        )

    # Validate min < max (if both specified)
    if min_level is not None and max_level is not None and min_level >= max_level:
        raise HomeAssistantError(
            f"min_level ({min_level}) must be less than max_level ({max_level})"
        )

    _LOGGER.debug("D1 Config: ✓ Parameter validation passed")

    # Step 3: Get device info
    device_id, device_ieee, model = await get_entity_device_info(hass, entity_id)
    _LOGGER.debug(
        "D1 Config: ✓ Device info: model=%s, ieee=%s",
        model,
        device_ieee,
    )

    # Step 4: Verify this is a D1 model
    if model not in ["D1", "D1-R"]:
        raise HomeAssistantError(
            f"Entity {entity_id} is not a D1 dimmer (model: {model}). "
            f"Ballast configuration only applies to D1/D1-R models."
        )
    _LOGGER.debug("D1 Config: ✓ Model verification passed")

    # Step 5: Access Ballast cluster
    cluster = await get_cluster(
        hass,
        device_ieee,
        CLUSTER_BALLAST,
        D1_DIMMER_ENDPOINT,
        "Ballast",
    )

    if not cluster:
        raise HomeAssistantError(
            f"Could not access Ballast cluster for {entity_id}. "
            f"Ensure the device is online and the D1 quirk is loaded."
        )
    _LOGGER.debug("D1 Config: ✓ Ballast cluster accessed")

    # Step 6: Build attributes dictionary
    attributes_to_write = {}
    if min_level is not None:
        attributes_to_write[BALLAST_ATTR_MIN_LEVEL] = min_level
    if max_level is not None:
        attributes_to_write[BALLAST_ATTR_MAX_LEVEL] = max_level

    _LOGGER.debug(
        "D1 Config: Writing ballast attributes: %s",
        attributes_to_write,
    )

    # Step 7: Write attributes
    try:
        # Standard ballast attributes don't require manufacturer code
        # (unlike manufacturer-specific attributes which do)
        result = await cluster.write_attributes(attributes_to_write)
        _LOGGER.debug("D1 Config: Write result: %s", result)

        # Check if write succeeded
        # Result is a list of WriteAttributesResponse objects
        for response in result:
            if response.status != 0:
                raise HomeAssistantError(
                    f"Failed to write ballast attribute: status={response.status}"
                )

        # Build success message
        changes = []
        if min_level is not None:
            changes.append(f"min_level={min_level}")
        if max_level is not None:
            changes.append(f"max_level={max_level}")

        _LOGGER.info(
            "D1 Config: ✓ Successfully configured ballast for %s: %s",
            entity_id,
            ", ".join(changes),
        )

    except Exception as err:
        _LOGGER.error(
            "D1 Config: Failed to write ballast configuration: %s",
            err,
            exc_info=True,
        )
        raise HomeAssistantError(
            f"Failed to configure ballast for {entity_id}: {err}"
        ) from err


async def async_configure_inputs(
    hass: HomeAssistant,
    entity_id: str,
    input_config: str,
    input_actions: str | None = None,
) -> None:
    """Configure D1 physical switch inputs.

    This is an advanced feature for configuring how physical wall switches
    connected to the D1 interact with the dimmer. Most users won't need this.

    Input Configuration (input_config):
        Configures the type of physical switch connected to each input:
        - Momentary: Push button (press and release)
        - Stationary: Toggle switch (on/off positions)
        - Decoupled: Switch controls Zigbee bindings, not local output

    Input Actions (input_actions):
        Configures what actions each input triggers (on/off, dim up/down, etc.)

    Format:
        Both parameters use Ubisys-specific string format. See D1 Technical
        Reference Manual for exact syntax.

    Why This Is Phase 3:
        This feature requires understanding the Ubisys DeviceSetup cluster
        string format, which is complex and device-specific. Most users can
        use the default input configuration. This service will be implemented
        after phase mode and ballast configuration are tested and working.

    How It Works (when implemented):
        1. Validate entity is a Ubisys D1 light entity
        2. Get device IEEE address from entity registry
        3. Access D1's DeviceSetup cluster (0xFC00) on endpoint 4
        4. Write input_configurations (0x0000) attribute
        5. Optionally write input_actions (0x0001) attribute
        6. Verify write succeeded

    Args:
        hass: Home Assistant instance
        entity_id: D1 light entity ID (e.g., "light.bedroom_d1")
        input_config: Input configuration string (Ubisys format)
        input_actions: Optional input actions string (Ubisys format)

    Raises:
        HomeAssistantError: Not yet implemented (Phase 3)

    See Also:
        - custom_zha_quirks/ubisys_d1.py: D1 quirk exposing DeviceSetup cluster
        - Ubisys D1 Technical Reference Manual (DeviceSetup cluster section)
    """
    _LOGGER.debug(
        "D1 Config: Starting input configuration for %s",
        entity_id,
    )

    # Step 1: Validate entity
    await validate_ubisys_entity(hass, entity_id, expected_domain="light")

    # This feature is planned for Phase 3
    raise HomeAssistantError(
        "D1 input configuration is not yet implemented. "
        "This is a Phase 3 feature that requires testing with a real D1 device "
        "to understand the DeviceSetup cluster string format. "
        "Most users can use the default input configuration."
    )

    # When implementation is complete, this will:
    # 1. Get device info and verify D1 model
    # 2. Access DeviceSetup cluster (0xFC00) on endpoint 4
    # 3. Write input_configurations (0x0000) and optionally input_actions (0x0001)
    # 4. Verify write succeeded and log result
