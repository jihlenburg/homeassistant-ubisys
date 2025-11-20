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

import asyncio
import logging
from typing import TYPE_CHECKING

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from .const import (
    BALLAST_ATTR_MAX_LEVEL,
    BALLAST_ATTR_MIN_LEVEL,
    BALLAST_LEVEL_MAX,
    BALLAST_LEVEL_MIN,
    BRIGHTNESS_LEVEL_MIN,
    BRIGHTNESS_LEVEL_PREVIOUS,
    CLUSTER_BALLAST,
    CLUSTER_DIMMER_SETUP,
    CLUSTER_LEVEL_CONTROL,
    CLUSTER_ON_OFF,
    D1_DIMMABLE_LIGHT_ENDPOINT,
    DIMMER_SETUP_ATTR_MODE,
    DIMMER_SETUP_ATTR_STATUS,
    DOMAIN,
    LEVEL_CONTROL_ATTR_ON_LEVEL,
    LEVEL_CONTROL_ATTR_ON_OFF_TRANSITION_TIME,
    LEVEL_CONTROL_ATTR_STARTUP_LEVEL,
    ON_OFF_ATTR_STARTUP_ON_OFF,
    PHASE_MODES,
    STARTUP_ON_OFF_VALUES,
    TRANSITION_TIME_MAX,
    TRANSITION_TIME_MIN,
    UBISYS_MANUFACTURER_CODE,
)
from .helpers import (
    async_write_and_verify_attrs,
    get_cluster,
    get_entity_device_info,
    is_verbose_info_logging,
    validate_ubisys_entity,
)
from .logtools import Stopwatch, info_banner, kv

if TYPE_CHECKING:
    pass

_LOGGER = logging.getLogger(__name__)


def _get_d1_lock(hass: HomeAssistant, device_ieee: str) -> asyncio.Lock:
    """Return an asyncio.Lock guarding configuration writes for this device."""
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN].setdefault("d1_config_locks", {})
    locks: dict[str, asyncio.Lock] = hass.data[DOMAIN]["d1_config_locks"]
    locks.setdefault(device_ieee, asyncio.Lock())
    return locks[device_ieee]


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
        3. Access D1's DimmerSetup cluster (0xFC01) on endpoint 1
        4. Write mode attribute (0x0002) with phase control value
        5. Verify write succeeded

    Note on Implementation:
        Phase control mode is in DimmerSetup cluster (0xFC01) on EP1, not Ballast.
        Attribute 0x0002 controls phase mode:
        - Bits [1:0]: 0=automatic, 1=forward, 2=reverse
        - Only writable when output is OFF

        Testing with a real D1 device may be needed to verify exact location.

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
    info_banner(_LOGGER, "D1 Phase Mode", entity_id=entity_id, phase_mode=phase_mode)
    sw = Stopwatch()

    # Step 1: Validate entity
    await validate_ubisys_entity(hass, entity_id, expected_domain="light")
    kv(_LOGGER, _LOGGER.level, "Entity validated", entity_id=entity_id)

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
    kv(_LOGGER, _LOGGER.level, "Device info", model=model, ieee=device_ieee)

    # Step 4: Verify this is a D1 model
    if model not in ["D1", "D1-R"]:
        raise HomeAssistantError(
            f"Entity {entity_id} is not a D1 dimmer (model: {model}). "
            f"Phase mode configuration only applies to D1/D1-R models."
        )
    _LOGGER.debug("D1 Config: ✓ Model verification passed")

    lock = _get_d1_lock(hass, device_ieee)

    try:
        async with lock:
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
            kv(
                _LOGGER,
                _LOGGER.level,
                "DimmerSetup accessed",
                endpoint=D1_DIMMABLE_LIGHT_ENDPOINT,
            )

            state = hass.states.get(entity_id)
            if state and state.state == "on":
                _LOGGER.debug("Light is ON; turning off before mode write")
                await hass.services.async_call(
                    "light", "turn_off", {"entity_id": entity_id}, blocking=True
                )
                await asyncio.sleep(0.5)

            _LOGGER.log(
                logging.INFO if is_verbose_info_logging(hass) else logging.DEBUG,
                "D1 Config: Configuring phase mode for %s: %s (%d)",
                entity_id,
                phase_mode,
                phase_mode_value,
            )

            await async_write_and_verify_attrs(
                cluster,
                {DIMMER_SETUP_ATTR_MODE: phase_mode_value},
                manufacturer=UBISYS_MANUFACTURER_CODE,
            )
            kv(
                _LOGGER,
                _LOGGER.level,
                "Phase mode set",
                phase_mode=phase_mode,
                elapsed_s=round(sw.elapsed, 1),
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
        4. Access D1's Ballast cluster (0x0301) on endpoint 1
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
    info_banner(
        _LOGGER, "D1 Ballast Config", entity_id=entity_id, min=min_level, max=max_level
    )
    sw = Stopwatch()

    # Step 1: Validate entity
    await validate_ubisys_entity(hass, entity_id, expected_domain="light")
    kv(_LOGGER, _LOGGER.level, "Entity validated", entity_id=entity_id)

    # Step 2: Validate parameters
    if min_level is None and max_level is None:
        raise HomeAssistantError(
            "At least one of min_level or max_level must be specified"
        )

    # Validate min_level range
    if min_level is not None and not (
        BALLAST_LEVEL_MIN <= min_level <= BALLAST_LEVEL_MAX
    ):
        raise HomeAssistantError(
            f"min_level must be between {BALLAST_LEVEL_MIN} and {BALLAST_LEVEL_MAX}, "
            f"got {min_level}"
        )

    # Validate max_level range
    if max_level is not None and not (
        BALLAST_LEVEL_MIN <= max_level <= BALLAST_LEVEL_MAX
    ):
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
    kv(_LOGGER, _LOGGER.level, "Device info", model=model, ieee=device_ieee)

    # Step 4: Verify this is a D1 model
    if model not in ["D1", "D1-R"]:
        raise HomeAssistantError(
            f"Entity {entity_id} is not a D1 dimmer (model: {model}). "
            f"Ballast configuration only applies to D1/D1-R models."
        )
    _LOGGER.debug("D1 Config: ✓ Model verification passed")

    lock = _get_d1_lock(hass, device_ieee)

    try:
        async with lock:
            cluster = await get_cluster(
                hass,
                device_ieee,
                CLUSTER_BALLAST,
                D1_DIMMABLE_LIGHT_ENDPOINT,
                "Ballast",
            )

            if not cluster:
                raise HomeAssistantError(
                    f"Could not access Ballast cluster for {entity_id}. "
                    f"Ensure the device is online and the D1 quirk is loaded."
                )
            kv(
                _LOGGER,
                _LOGGER.level,
                "Ballast accessed",
                endpoint=D1_DIMMABLE_LIGHT_ENDPOINT,
            )

            attributes_to_write = {}
            if min_level is not None:
                attributes_to_write[BALLAST_ATTR_MIN_LEVEL] = min_level
            if max_level is not None:
                attributes_to_write[BALLAST_ATTR_MAX_LEVEL] = max_level

            _LOGGER.debug(
                "D1 Config: Writing ballast attributes: %s",
                attributes_to_write,
            )

            await async_write_and_verify_attrs(cluster, attributes_to_write)
            changes = []
            if min_level is not None:
                changes.append(f"min_level={min_level}")
            if max_level is not None:
                changes.append(f"max_level={max_level}")
            kv(
                _LOGGER,
                _LOGGER.level,
                "Ballast set",
                changes=", ".join(changes),
                elapsed_s=round(sw.elapsed, 1),
            )

    except HomeAssistantError:
        raise
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
        3. Access D1's DeviceSetup cluster (0xFC00) on endpoint 232
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
    # 2. Access DeviceSetup cluster (0xFC00) on endpoint 232
    # 3. Write input_configurations (0x0000) and optionally input_actions (0x0001)
    # 4. Verify write succeeded and log result


async def async_configure_transition_time(
    hass: HomeAssistant,
    entity_id: str,
    transition_time: int,
) -> None:
    """Configure D1 on/off transition time (ramp rate).

    This controls how quickly the light fades on or off - the "dimming curve"
    that users typically ask about. Higher values = slower, smoother fades.

    Units: 0.1 seconds (tenths of a second)
    Examples:
        - 0 = Instant on/off (no fade)
        - 10 = 1 second fade
        - 50 = 5 second fade
        - 100 = 10 second fade

    Range: 0-65535 (0 to ~109 minutes)

    Technical Details:
        This writes the OnOffTransitionTime attribute (0x0010) in the Level
        Control cluster (0x0008). This is a standard ZCL attribute, not
        manufacturer-specific.

    Args:
        hass: Home Assistant instance
        entity_id: D1 light entity ID (e.g., "light.bedroom_d1")
        transition_time: Transition time in 0.1s units (0-65535)

    Raises:
        HomeAssistantError: If validation fails or write fails

    Example:
        # Set 2-second fade
        >>> await async_configure_transition_time(
        ...     hass, "light.bedroom_d1", 20
        ... )
    """
    info_banner(
        _LOGGER,
        "D1 Transition Time",
        entity_id=entity_id,
        transition_time=transition_time,
    )
    sw = Stopwatch()

    # Step 1: Validate entity
    await validate_ubisys_entity(hass, entity_id, expected_domain="light")
    kv(_LOGGER, _LOGGER.level, "Entity validated", entity_id=entity_id)

    # Step 2: Validate transition time range
    if not (TRANSITION_TIME_MIN <= transition_time <= TRANSITION_TIME_MAX):
        raise HomeAssistantError(
            f"transition_time must be between {TRANSITION_TIME_MIN} and "
            f"{TRANSITION_TIME_MAX}, got {transition_time}"
        )

    _LOGGER.debug(
        "D1 Config: ✓ Transition time validated: %d (%.1fs)",
        transition_time,
        transition_time / 10.0,
    )

    # Step 3: Get device info
    device_id, device_ieee, model = await get_entity_device_info(hass, entity_id)
    kv(_LOGGER, _LOGGER.level, "Device info", model=model, ieee=device_ieee)

    # Step 4: Verify this is a D1 model
    if model not in ["D1", "D1-R"]:
        raise HomeAssistantError(
            f"Entity {entity_id} is not a D1 dimmer (model: {model}). "
            f"Transition time configuration only applies to D1/D1-R models."
        )

    lock = _get_d1_lock(hass, device_ieee)

    try:
        async with lock:
            cluster = await get_cluster(
                hass,
                device_ieee,
                CLUSTER_LEVEL_CONTROL,
                D1_DIMMABLE_LIGHT_ENDPOINT,
                "LevelControl",
            )

            if not cluster:
                raise HomeAssistantError(
                    f"Could not access Level Control cluster for {entity_id}. "
                    f"Ensure the device is online."
                )
            kv(
                _LOGGER,
                _LOGGER.level,
                "LevelControl accessed",
                endpoint=D1_DIMMABLE_LIGHT_ENDPOINT,
            )

            await async_write_and_verify_attrs(
                cluster,
                {LEVEL_CONTROL_ATTR_ON_OFF_TRANSITION_TIME: transition_time},
            )
            kv(
                _LOGGER,
                _LOGGER.level,
                "Transition time set",
                value=transition_time,
                seconds=round(transition_time / 10.0, 1),
                elapsed_s=round(sw.elapsed, 1),
            )
    except HomeAssistantError:
        raise
    except Exception as err:
        _LOGGER.error("D1 Config: Failed to write transition time: %s", err)
        raise HomeAssistantError(
            f"Failed to configure transition time for {entity_id}: {err}"
        ) from err


async def async_configure_on_level(
    hass: HomeAssistant,
    entity_id: str,
    on_level: int | None = None,
    startup_level: int | None = None,
) -> None:
    """Configure D1 turn-on and startup brightness levels.

    on_level: The brightness level when the light is turned on
        - Range: 1-254 (specific brightness)
        - 255: Use previous brightness (before it was turned off)

    startup_level: The brightness level after power loss/restore
        - Range: 1-254 (specific brightness)
        - 255: Use previous brightness (before power loss)

    Technical Details:
        - on_level → OnLevel attribute (0x0011) in Level Control cluster
        - startup_level → StartupLevel attribute (0x4000) in Level Control cluster

    Args:
        hass: Home Assistant instance
        entity_id: D1 light entity ID
        on_level: Turn-on brightness (1-255), or None to leave unchanged
        startup_level: Power-on brightness (1-255), or None to leave unchanged

    Raises:
        HomeAssistantError: If validation fails or write fails

    Example:
        # Always turn on at 50% brightness
        >>> await async_configure_on_level(
        ...     hass, "light.bedroom_d1", on_level=127
        ... )

        # Remember previous brightness
        >>> await async_configure_on_level(
        ...     hass, "light.bedroom_d1", on_level=255
        ... )
    """
    info_banner(
        _LOGGER,
        "D1 On Level",
        entity_id=entity_id,
        on_level=on_level,
        startup_level=startup_level,
    )
    sw = Stopwatch()

    # Step 1: Validate entity
    await validate_ubisys_entity(hass, entity_id, expected_domain="light")
    kv(_LOGGER, _LOGGER.level, "Entity validated", entity_id=entity_id)

    # Step 2: Validate parameters
    if on_level is None and startup_level is None:
        raise HomeAssistantError(
            "At least one of on_level or startup_level must be specified"
        )

    # Validate on_level range (1-255, where 255 = previous)
    if on_level is not None and not (
        BRIGHTNESS_LEVEL_MIN <= on_level <= BRIGHTNESS_LEVEL_PREVIOUS
    ):
        raise HomeAssistantError(
            f"on_level must be between {BRIGHTNESS_LEVEL_MIN} and "
            f"{BRIGHTNESS_LEVEL_PREVIOUS}, got {on_level}"
        )

    # Validate startup_level range
    if startup_level is not None and not (
        BRIGHTNESS_LEVEL_MIN <= startup_level <= BRIGHTNESS_LEVEL_PREVIOUS
    ):
        raise HomeAssistantError(
            f"startup_level must be between {BRIGHTNESS_LEVEL_MIN} and "
            f"{BRIGHTNESS_LEVEL_PREVIOUS}, got {startup_level}"
        )

    _LOGGER.debug("D1 Config: ✓ Level parameter validation passed")

    # Step 3: Get device info
    device_id, device_ieee, model = await get_entity_device_info(hass, entity_id)
    kv(_LOGGER, _LOGGER.level, "Device info", model=model, ieee=device_ieee)

    # Step 4: Verify this is a D1 model
    if model not in ["D1", "D1-R"]:
        raise HomeAssistantError(
            f"Entity {entity_id} is not a D1 dimmer (model: {model}). "
            f"On level configuration only applies to D1/D1-R models."
        )

    lock = _get_d1_lock(hass, device_ieee)

    try:
        async with lock:
            cluster = await get_cluster(
                hass,
                device_ieee,
                CLUSTER_LEVEL_CONTROL,
                D1_DIMMABLE_LIGHT_ENDPOINT,
                "LevelControl",
            )

            if not cluster:
                raise HomeAssistantError(
                    f"Could not access Level Control cluster for {entity_id}. "
                    f"Ensure the device is online."
                )

            attributes_to_write = {}
            if on_level is not None:
                attributes_to_write[LEVEL_CONTROL_ATTR_ON_LEVEL] = on_level
            if startup_level is not None:
                attributes_to_write[LEVEL_CONTROL_ATTR_STARTUP_LEVEL] = startup_level

            _LOGGER.debug(
                "D1 Config: Writing level attributes: %s",
                attributes_to_write,
            )

            await async_write_and_verify_attrs(cluster, attributes_to_write)

            changes = []
            if on_level is not None:
                label = "previous" if on_level == 255 else str(on_level)
                changes.append(f"on_level={label}")
            if startup_level is not None:
                label = "previous" if startup_level == 255 else str(startup_level)
                changes.append(f"startup_level={label}")

            kv(
                _LOGGER,
                _LOGGER.level,
                "Levels set",
                changes=", ".join(changes),
                elapsed_s=round(sw.elapsed, 1),
            )
    except HomeAssistantError:
        raise
    except Exception as err:
        _LOGGER.error("D1 Config: Failed to write level configuration: %s", err)
        raise HomeAssistantError(
            f"Failed to configure on level for {entity_id}: {err}"
        ) from err


async def async_configure_startup(
    hass: HomeAssistant,
    entity_id: str,
    startup_on_off: str,
) -> None:
    """Configure D1 power-on state behavior.

    This determines what the light does after power is restored (e.g., after
    a power outage).

    startup_on_off values:
        - "off": Light stays off after power restore
        - "on": Light turns on after power restore
        - "toggle": Light toggles from previous state
        - "previous": Light restores to state before power loss

    Technical Details:
        Writes StartupOnOff attribute (0x4003) in On/Off cluster (0x0006).

    Args:
        hass: Home Assistant instance
        entity_id: D1 light entity ID
        startup_on_off: Power-on behavior ("off", "on", "toggle", "previous")

    Raises:
        HomeAssistantError: If validation fails or write fails

    Example:
        # Always start off after power restore
        >>> await async_configure_startup(
        ...     hass, "light.bedroom_d1", "off"
        ... )

        # Restore previous state
        >>> await async_configure_startup(
        ...     hass, "light.bedroom_d1", "previous"
        ... )
    """
    info_banner(
        _LOGGER,
        "D1 Startup Config",
        entity_id=entity_id,
        startup_on_off=startup_on_off,
    )
    sw = Stopwatch()

    # Step 1: Validate entity
    await validate_ubisys_entity(hass, entity_id, expected_domain="light")
    kv(_LOGGER, _LOGGER.level, "Entity validated", entity_id=entity_id)

    # Step 2: Validate startup_on_off value
    if startup_on_off not in STARTUP_ON_OFF_VALUES:
        raise HomeAssistantError(
            f"Invalid startup_on_off '{startup_on_off}'. "
            f"Valid values: {', '.join(STARTUP_ON_OFF_VALUES.keys())}"
        )

    startup_value = STARTUP_ON_OFF_VALUES[startup_on_off]
    _LOGGER.debug(
        "D1 Config: ✓ Startup on/off validated: %s = 0x%02X",
        startup_on_off,
        startup_value,
    )

    # Step 3: Get device info
    device_id, device_ieee, model = await get_entity_device_info(hass, entity_id)
    kv(_LOGGER, _LOGGER.level, "Device info", model=model, ieee=device_ieee)

    # Step 4: Verify this is a D1 model
    if model not in ["D1", "D1-R"]:
        raise HomeAssistantError(
            f"Entity {entity_id} is not a D1 dimmer (model: {model}). "
            f"Startup configuration only applies to D1/D1-R models."
        )

    lock = _get_d1_lock(hass, device_ieee)

    try:
        async with lock:
            cluster = await get_cluster(
                hass,
                device_ieee,
                CLUSTER_ON_OFF,
                D1_DIMMABLE_LIGHT_ENDPOINT,
                "OnOff",
            )

            if not cluster:
                raise HomeAssistantError(
                    f"Could not access On/Off cluster for {entity_id}. "
                    f"Ensure the device is online."
                )
            kv(
                _LOGGER,
                _LOGGER.level,
                "OnOff accessed",
                endpoint=D1_DIMMABLE_LIGHT_ENDPOINT,
            )

            await async_write_and_verify_attrs(
                cluster,
                {ON_OFF_ATTR_STARTUP_ON_OFF: startup_value},
            )
            kv(
                _LOGGER,
                _LOGGER.level,
                "Startup behavior set",
                startup_on_off=startup_on_off,
                elapsed_s=round(sw.elapsed, 1),
            )
    except HomeAssistantError:
        raise
    except Exception as err:
        _LOGGER.error("D1 Config: Failed to write startup configuration: %s", err)
        raise HomeAssistantError(
            f"Failed to configure startup behavior for {entity_id}: {err}"
        ) from err


async def async_get_status(
    hass: HomeAssistant,
    entity_id: str,
) -> dict[str, int | str | bool]:
    """Read D1 dimmer status and diagnostics.

    Returns read-only diagnostic information from the D1's DimmerSetup
    cluster Status attribute.

    Status bits indicate:
        - Detected load type (forward/reverse phase control)
        - Operational conditions (overload, capacitive, inductive)

    This is useful for troubleshooting phase mode issues - you can see
    what the dimmer actually detected about your connected load.

    Returns:
        Dictionary with status information:
        {
            "raw_status": <int>,
            "forward_phase_control": <bool>,
            "reverse_phase_control": <bool>,
            "overload": <bool>,
            "capacitive_load": <bool>,
            "inductive_load": <bool>,
        }

    Raises:
        HomeAssistantError: If entity validation fails or read fails
    """
    info_banner(_LOGGER, "D1 Status Read", entity_id=entity_id)
    sw = Stopwatch()

    # Step 1: Validate entity
    await validate_ubisys_entity(hass, entity_id, expected_domain="light")
    kv(_LOGGER, _LOGGER.level, "Entity validated", entity_id=entity_id)

    # Step 2: Get device info
    device_id, device_ieee, model = await get_entity_device_info(hass, entity_id)
    kv(_LOGGER, _LOGGER.level, "Device info", model=model, ieee=device_ieee)

    # Step 3: Verify this is a D1 model
    if model not in ["D1", "D1-R"]:
        raise HomeAssistantError(
            f"Entity {entity_id} is not a D1 dimmer (model: {model}). "
            f"Status read only applies to D1/D1-R models."
        )

    try:
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

        # Read status attribute
        result = await cluster.read_attributes(
            [DIMMER_SETUP_ATTR_STATUS],
            manufacturer=UBISYS_MANUFACTURER_CODE,
        )

        if not result or DIMMER_SETUP_ATTR_STATUS not in result[0]:
            raise HomeAssistantError(
                f"Failed to read status from {entity_id}. "
                f"The device may not support this attribute."
            )

        raw_status = result[0][DIMMER_SETUP_ATTR_STATUS]

        # Parse status bits based on Zigbee2MQTT D1 documentation
        # Bits: 0=forward, 1=reverse, 2=overload, 3=capacitive, 4=inductive
        status = {
            "raw_status": raw_status,
            "forward_phase_control": bool(raw_status & 0x01),
            "reverse_phase_control": bool(raw_status & 0x02),
            "overload": bool(raw_status & 0x04),
            "capacitive_load": bool(raw_status & 0x08),
            "inductive_load": bool(raw_status & 0x10),
        }

        kv(
            _LOGGER,
            _LOGGER.level,
            "Status read",
            raw=hex(raw_status),
            elapsed_s=round(sw.elapsed, 1),
        )

        return status

    except HomeAssistantError:
        raise
    except Exception as err:
        _LOGGER.error("D1 Config: Failed to read status: %s", err)
        raise HomeAssistantError(
            f"Failed to read status from {entity_id}: {err}"
        ) from err
