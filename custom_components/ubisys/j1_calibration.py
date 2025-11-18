"""Calibration module for Ubisys J1 window covering controller.

This module provides automated calibration of Ubisys J1 devices using proper
limit detection via motor stall monitoring. The calibration sequence follows
the proven deCONZ approach:

1. Enter calibration mode
2. Find top limit (motor stall detection)
3. Find bottom limit (motor stall detection)
4. Return to top (verification)
5. Configure device (tilt steps, configured_mode)
6. Exit calibration mode

This works for both roller blinds and venetian blinds.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import TYPE_CHECKING, cast

from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er

from .const import (
    CALIBRATION_MODE_ATTR,
    CALIBRATION_MODE_ENTER,
    CALIBRATION_MODE_EXIT,
    CONF_DEVICE_IEEE,
    CONF_SHADE_TYPE,
    DOMAIN,
    PER_MOVE_TIMEOUT,
    SETTLE_TIME,
    SHADE_TYPE_TILT_STEPS,
    SHADE_TYPE_TO_WINDOW_COVERING_TYPE,
    STALL_DETECTION_INTERVAL,
    STALL_DETECTION_TIME,
    UBISYS_ATTR_ADDITIONAL_STEPS,
    UBISYS_ATTR_CONFIGURED_MODE,
    UBISYS_ATTR_INACTIVE_POWER_THRESHOLD,
    UBISYS_ATTR_LIFT_TO_TILT_TRANSITION_STEPS,
    UBISYS_ATTR_STARTUP_STEPS,
    UBISYS_ATTR_TOTAL_STEPS,
    UBISYS_ATTR_TURNAROUND_GUARD_TIME,
    UBISYS_MANUFACTURER_CODE,
)
from .helpers import (
    async_write_and_verify_attrs,
    async_zcl_command,
    is_verbose_info_logging,
    resolve_zha_gateway,
)
from .logtools import Stopwatch, info_banner, kv

if TYPE_CHECKING:
    from zigpy.zcl import Cluster

_LOGGER = logging.getLogger(__name__)

# Note: Calibration constants are now imported from const.py to avoid duplication
# See const.py for: CALIBRATION_MODE_*, STALL_DETECTION_*, PER_MOVE_TIMEOUT, SETTLE_TIME

TOTAL_CALIBRATION_TIMEOUT = 300  # Maximum 5 minutes total (not yet used)


async def async_calibrate_j1(hass: HomeAssistant, call: ServiceCall) -> None:
    """Handle ubisys.calibrate_j1 service calls (single or multiple entities).

    The service schema uses ``cv.entity_ids`` so Home Assistant passes either a
    string (YAML automations) or a list of strings (UI multi-select). We normalize
    both cases to a list and process each request sequentially so locking,
    notifications, and logging remain consistent.
    """

    raw_entity_ids = call.data.get("entity_id")
    test_mode = bool(call.data.get("test_mode", False))

    if raw_entity_ids is None:
        raise HomeAssistantError("Missing required parameter: entity_id")

    entity_ids: list[str]
    if isinstance(raw_entity_ids, str):
        entity_ids = [raw_entity_ids]
    elif isinstance(raw_entity_ids, (list, tuple, set)):
        if not raw_entity_ids:
            raise HomeAssistantError("entity_id list cannot be empty")
        entity_ids = []
        for idx, entity_id in enumerate(raw_entity_ids, start=1):
            if not isinstance(entity_id, str) or not entity_id:
                raise HomeAssistantError(
                    f"entity_id entries must be non-empty strings (entry {idx})"
                )
            entity_ids.append(entity_id)
    else:
        raise HomeAssistantError(
            f"entity_id must be a string or list of strings, got {type(raw_entity_ids).__name__}"
        )

    successes: list[str] = []
    failures: dict[str, str] = {}

    for position, entity_id in enumerate(entity_ids, start=1):
        _LOGGER.debug(
            "Processing calibration request %d/%d: %s",
            position,
            len(entity_ids),
            entity_id,
        )
        try:
            await _async_calibrate_single_entity(hass, entity_id, test_mode)
            successes.append(entity_id)
        except HomeAssistantError as err:
            failures[entity_id] = str(err)
        except Exception as err:  # pragma: no cover - defensive guardrail
            _LOGGER.exception("Unexpected calibration error for %s", entity_id)
            failures[entity_id] = str(err)

    if failures:
        summary = "; ".join(f"{entity}: {error}" for entity, error in failures.items())
        if successes:
            raise HomeAssistantError(
                "Calibration completed with partial failures. "
                f"Successful: {successes}. Failed: {summary}"
            )
        raise HomeAssistantError(f"Calibration failed for all entities: {summary}")


async def async_tune_j1(hass: HomeAssistant, call: ServiceCall) -> None:
    """Advanced tuning for Ubisys J1 manufacturer attributes.

    Allows writing persistent tuning parameters on the WindowCovering cluster:
    - turnaround_guard_time (0x1000) in 50ms units (uint16)
    - inactive_power_threshold (0x1006) in mW (uint16)
    - startup_steps (0x1007) in AC waves (uint16)
    - additional_steps (0x1005) percentage (0-100) (uint8/uint16)

    Service data (all optional except entity_id):
      entity_id: Cover entity (ubisys)
      turnaround_guard_time: int
      inactive_power_threshold: int
      startup_steps: int
      additional_steps: int
    """
    entity_id = call.data.get("entity_id")
    if not entity_id or not isinstance(entity_id, str):
        raise HomeAssistantError("Missing or invalid entity_id")

    entity_registry = er.async_get(hass)
    entry = entity_registry.async_get(entity_id)
    if not entry or entry.platform != DOMAIN:
        raise HomeAssistantError("Entity is not a Ubisys entity")

    cfg_entry = hass.config_entries.async_get_entry(entry.config_entry_id)
    if not cfg_entry:
        raise HomeAssistantError("Config entry not found")

    device_ieee = cfg_entry.data.get(CONF_DEVICE_IEEE)
    if not device_ieee:
        raise HomeAssistantError("Device IEEE not found in config entry")

    cluster = await _get_window_covering_cluster(hass, device_ieee)
    if not cluster:
        raise HomeAssistantError("WindowCovering cluster not available")

    # Build attributes to write based on provided inputs
    attributes: dict[int, int] = {}
    if "turnaround_guard_time" in call.data:
        val = int(call.data["turnaround_guard_time"])
        if val < 0 or val > 65535:
            raise HomeAssistantError("turnaround_guard_time out of range (0-65535)")
        attributes[UBISYS_ATTR_TURNAROUND_GUARD_TIME] = val

    if "inactive_power_threshold" in call.data:
        val = int(call.data["inactive_power_threshold"])
        if val < 0 or val > 65535:
            raise HomeAssistantError("inactive_power_threshold out of range (0-65535)")
        attributes[UBISYS_ATTR_INACTIVE_POWER_THRESHOLD] = val

    if "startup_steps" in call.data:
        val = int(call.data["startup_steps"])
        if val < 0 or val > 65535:
            raise HomeAssistantError("startup_steps out of range (0-65535)")
        attributes[UBISYS_ATTR_STARTUP_STEPS] = val

    if "additional_steps" in call.data:
        val = int(call.data["additional_steps"])
        if val < 0 or val > 100:
            raise HomeAssistantError("additional_steps out of range (0-100)")
        attributes[UBISYS_ATTR_ADDITIONAL_STEPS] = val

    if not attributes:
        raise HomeAssistantError("No tuning parameters provided")

    try:
        _LOGGER.info("Tuning J1 attributes for %s: %s", entity_id, attributes)
        await async_write_and_verify_attrs(
            cluster, attributes, manufacturer=UBISYS_MANUFACTURER_CODE
        )
        _LOGGER.info("✓ Advanced J1 tuning verified successfully for %s", entity_id)
    except HomeAssistantError:
        raise
    except Exception as err:
        raise HomeAssistantError(f"Failed to tune J1: {err}") from err


async def _async_calibrate_single_entity(
    hass: HomeAssistant,
    entity_id: str,
    test_mode: bool,
) -> None:
    """Validate inputs, manage locks, and calibrate a single Ubisys cover."""

    entity_id = entity_id.strip()
    if not entity_id:
        raise HomeAssistantError("Missing required parameter: entity_id")

    _LOGGER.info("Starting calibration for entity: %s", entity_id)
    try:
        hass.components.persistent_notification.create(
            title="Ubisys Calibration",
            message=f"Starting calibration for {entity_id}…",
            notification_id=_get_notification_id(entity_id),
        )
    except Exception:  # pragma: no cover - notifications are best-effort
        _LOGGER.debug("Unable to create start notification")

    entity_registry = er.async_get(hass)
    entity_entry = entity_registry.async_get(entity_id)
    if not entity_entry:
        raise HomeAssistantError(f"Entity {entity_id} not found in registry")
    if entity_entry.platform != DOMAIN:
        raise HomeAssistantError(
            f"Entity {entity_id} is not a Ubisys entity. "
            f"Expected platform '{DOMAIN}', got '{entity_entry.platform}'"
        )

    config_entry_id = entity_entry.config_entry_id
    if not config_entry_id:
        raise HomeAssistantError(f"Entity has no config entry: {entity_id}")

    config_entry = hass.config_entries.async_get_entry(config_entry_id)
    if not config_entry or config_entry.domain != DOMAIN:
        raise HomeAssistantError(f"Invalid config entry for entity: {entity_id}")

    device_ieee = config_entry.data.get(CONF_DEVICE_IEEE)
    shade_type = config_entry.data.get(CONF_SHADE_TYPE)
    if not device_ieee or not shade_type:
        raise HomeAssistantError("Missing device information in config entry")

    zha_entity_id = await _find_zha_cover_entity(hass, entity_entry.device_id)
    if not zha_entity_id:
        raise HomeAssistantError(f"ZHA cover entity not found for: {entity_id}")

    if test_mode:
        await _async_run_calibration_health_check(
            hass,
            entity_id,
            device_ieee,
            zha_entity_id,
        )
        return

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN].setdefault("calibration_locks", {})
    locks: dict[str, asyncio.Lock] = hass.data[DOMAIN]["calibration_locks"]
    locks.setdefault(device_ieee, asyncio.Lock())
    device_lock = locks[device_ieee]

    if device_lock.locked():
        raise HomeAssistantError(
            f"Calibration already in progress for device {device_ieee}. "
            "Please wait for the current calibration to complete."
        )

    async with device_lock:
        _LOGGER.info(
            "Acquired calibration lock for device %s - starting calibration",
            device_ieee,
        )
        calibration_start = time.time()
        try:
            await _perform_calibration(hass, zha_entity_id, device_ieee, shade_type)
            elapsed = time.time() - calibration_start
            _LOGGER.info(
                "Calibration completed successfully for %s in %.1f seconds",
                entity_id,
                elapsed,
            )
            _record_calibration_history(
                hass,
                device_ieee,
                {
                    "entity_id": entity_id,
                    "device_ieee": device_ieee,
                    "shade_type": shade_type,
                    "duration_s": round(elapsed, 1),
                    "success": True,
                    "ts": time.time(),
                },
            )
            try:
                hass.components.persistent_notification.create(
                    title="Ubisys Calibration",
                    message=f"Calibration completed for {entity_id} in {elapsed:.1f}s.",
                    notification_id=_get_notification_id(entity_id),
                )
            except Exception:  # pragma: no cover
                _LOGGER.debug("Unable to update success notification")
            try:
                from .const import EVENT_UBISYS_CALIBRATION_COMPLETE

                hass.bus.async_fire(
                    EVENT_UBISYS_CALIBRATION_COMPLETE,
                    {
                        "entity_id": entity_id,
                        "device_ieee": device_ieee,
                        "shade_type": shade_type,
                        "duration_s": round(elapsed, 1),
                    },
                )
            except Exception:  # pragma: no cover
                _LOGGER.debug("Unable to fire calibration completion event")
        except Exception as err:
            await _handle_calibration_failure(
                hass,
                entity_id,
                device_ieee,
                shade_type,
                err,
            )
            raise


def _get_notification_id(entity_id: str) -> str:
    return f"ubisys_calibration_{entity_id}"


async def _find_zha_cover_entity(hass: HomeAssistant, device_id: str) -> str | None:
    """Find the ZHA cover entity for a device.

    Searches the entity registry for the ZHA cover entity that corresponds
    to the given device_id. This is needed because calibration monitors the
    ZHA entity's position attribute (not the ubisys wrapper entity).

    Why Search for ZHA Entity?

    The ubisys integration creates wrapper entities that delegate to ZHA entities:
        - User interacts with: cover.bedroom_shade (ubisys wrapper)
        - Calibration monitors: cover.bedroom_shade_2 (ZHA entity)

    We need the ZHA entity because:
        - It reports position attribute directly from device
        - Updates faster than wrapper (no delegation overhead)
        - More reliable for stall detection timing

    Search Strategy:

        1. Get entity registry
        2. Find all entities for this device_id
        3. Filter for platform="zha" AND domain="cover"
        4. Return first match (should only be one)

    Args:
        hass: Home Assistant instance for registry access
        device_id: Device ID from device registry

    Returns:
        ZHA cover entity_id (e.g., "cover.bedroom_shade_2"), or None if not found

    Example:
        >>> zha_entity = await _find_zha_cover_entity(hass, "abc123...")
        >>> print(zha_entity)
        cover.bedroom_shade_2

    See Also:
        - async_calibrate_j1(): Calls this to find entity for monitoring
        - _wait_for_stall(): Uses this entity_id for position monitoring
    """
    entity_registry = er.async_get(hass)
    entities = er.async_entries_for_device(entity_registry, device_id)

    for entity_entry in entities:
        if entity_entry.platform == "zha" and entity_entry.domain == "cover":
            return cast(str, entity_entry.entity_id)

    return None


async def _validate_device_ready(hass: HomeAssistant, entity_id: str) -> None:
    """Validate device is ready for calibration (pre-flight checks).

    Performs essential checks before starting calibration to fail fast with clear
    error messages rather than failing midway through the sequence. This improves
    user experience by catching common issues early.

    Pre-flight Checks:
        1. Entity exists in Home Assistant state registry
           → Catches misconfigured entity_id or deleted entities

        2. Device is available (not offline/unavailable)
           → Prevents starting calibration on disconnected device
           → User should check Zigbee connection, power, signal strength

        3. Device reports current_position attribute
           → Verifies device is compatible (WindowCovering device)
           → Required for stall detection algorithm

    Why these specific checks?
        - Entity existence: ZHA entity could be disabled/removed between
          service call and calibration start
        - Availability: Zigbee device could go offline, preventing any commands
        - Position attribute: Required for stall detection; missing indicates
          incompatible device or ZHA configuration issue

    Args:
        hass: Home Assistant instance for state access
        entity_id: ZHA cover entity ID to validate (not ubisys wrapper entity)

    Raises:
        HomeAssistantError: With specific message indicating which check failed:
            - "Entity {id} not found" → Check entity_id, verify ZHA pairing
            - "Device is unavailable" → Check power, Zigbee connection
            - "Does not report current_position" → Incompatible device

    Example:
        >>> await _validate_device_ready(hass, "cover.zha_bedroom_j1")
        # Returns normally if all checks pass

        >>> await _validate_device_ready(hass, "cover.wrong_id")
        HomeAssistantError: Entity cover.wrong_id not found...
    """
    _LOGGER.debug("Running pre-flight checks for %s", entity_id)

    # Check 1: Entity exists
    state = hass.states.get(entity_id)
    if not state:
        raise HomeAssistantError(
            f"Entity {entity_id} not found. Device may not be paired correctly."
        )

    # Check 2: Device is available
    if state.state == "unavailable":
        raise HomeAssistantError(
            "Device is unavailable. Ensure it's powered on and connected to Zigbee network."
        )

    # Check 3: Position attribute exists
    if state.attributes.get("current_position") is None:
        raise HomeAssistantError(
            "Device does not report current_position. This device may not be compatible."
        )

    _LOGGER.debug("✓ Pre-flight checks passed for %s", entity_id)


async def _async_run_calibration_health_check(
    hass: HomeAssistant,
    entity_id: str,
    device_ieee: str,
    zha_entity_id: str,
) -> None:
    """Perform the read-only test_mode workflow (no writes/movements)."""

    if is_verbose_info_logging(hass):
        info_banner(
            _LOGGER,
            "J1 Calibration Test Mode",
            entity_id=entity_id,
            device_ieee=device_ieee,
        )

    await _validate_device_ready(hass, zha_entity_id)
    cluster = await _get_window_covering_cluster(hass, device_ieee)
    if not cluster:
        raise HomeAssistantError("WindowCovering cluster unavailable")

    state = hass.states.get(zha_entity_id)
    current_position = state.attributes.get("current_position") if state else None
    try:
        read = await cluster.read_attributes(
            [UBISYS_ATTR_TOTAL_STEPS],
            manufacturer=UBISYS_MANUFACTURER_CODE,
        )
        total_steps = (
            read[0].get(UBISYS_ATTR_TOTAL_STEPS)
            if isinstance(read, list) and read
            else None
        )
    except Exception:  # pragma: no cover - diagnostic helper
        total_steps = None

    kv(
        _LOGGER,
        logging.INFO,
        "Health check",
        entity_id=entity_id,
        device_ieee=device_ieee,
        current_position=current_position,
        total_steps=total_steps,
    )


def _record_calibration_history(
    hass: HomeAssistant,
    device_ieee: str,
    data: dict[str, object],
) -> None:
    hass.data.setdefault(DOMAIN, {}).setdefault("calibration_history", {})
    hass.data[DOMAIN]["calibration_history"][device_ieee] = data


async def _handle_calibration_failure(
    hass: HomeAssistant,
    entity_id: str,
    device_ieee: str,
    shade_type: str,
    err: Exception,
) -> None:
    """Shared cleanup/logging for calibration failures."""

    _LOGGER.error("Calibration failed for %s: %s", entity_id, err)
    _record_calibration_history(
        hass,
        device_ieee,
        {
            "entity_id": entity_id,
            "device_ieee": device_ieee,
            "shade_type": shade_type,
            "duration_s": None,
            "success": False,
            "error": str(err),
            "ts": time.time(),
        },
    )
    try:
        hass.components.persistent_notification.create(
            title="Ubisys Calibration",
            message=f"Calibration FAILED for {entity_id}: {err}",
            notification_id=_get_notification_id(entity_id),
        )
    except Exception:  # pragma: no cover
        _LOGGER.debug("Unable to update failure notification")
    try:
        cluster = await _get_window_covering_cluster(hass, device_ieee)
        if cluster:
            await _exit_calibration_mode(cluster)
    except Exception as cleanup_err:  # pragma: no cover
        _LOGGER.error("Failed to exit calibration mode during cleanup: %s", cleanup_err)
    try:
        from .const import EVENT_UBISYS_CALIBRATION_FAILED

        hass.bus.async_fire(
            EVENT_UBISYS_CALIBRATION_FAILED,
            {
                "entity_id": entity_id,
                "device_ieee": device_ieee,
                "shade_type": shade_type,
                "error": str(err),
            },
        )
    except Exception:  # pragma: no cover
        _LOGGER.debug("Unable to fire calibration failure event")


async def _calibration_phase_1_enter_mode(
    cluster: Cluster,
    shade_type: str,
) -> None:
    """PHASE 1: Enter calibration mode and configure shade type.

    Prepares the Ubisys J1 device for calibration by entering a special
    device mode and configuring the window covering type.

    What is Calibration Mode?

    The J1 has a special calibration mode (manufacturer-specific attribute 0x0017)
    with these values:
        - 0x00: Normal operation mode
        - 0x02: Calibration mode (what we set here)

    In calibration mode, the device:
        - Counts motor steps during movement
        - Calculates total_steps automatically
        - Allows writing special configuration attributes
        - Disables normal position limit enforcement

    Why Set window_covering_type?

    CRITICAL FIX (v1.2.0): Corrected attribute ID from 0x1000 → 0x0000
        - Previous code was accidentally writing to TurnaroundGuardTime (0x1000)
        - Now correctly writes to WindowCoveringType (0x10F2:0x0000)
        - This prevents unintended modification of device guard time settings

    The window_covering_type attribute (manufacturer 0x10F2, attribute 0x0000)
    tells the device what type of window covering is attached. This affects how
    the device interprets commands and calculates positions.

    Values from const.py SHADE_TYPE_TO_WINDOW_COVERING_TYPE:
        - 0x00: Roller shade / Cellular shade (position only)
        - 0x04: Vertical blind (position only)
        - 0x08: Venetian blind / Exterior venetian (position + tilt)

    Phase Sequence:
        Step 1: Write mode attribute = 0x02 (enter calibration mode)
                Wait SETTLE_TIME (1s) for device to enter mode

        Step 2: Write window_covering_type based on shade type
                Maps shade_type string → WindowCoveringType enum value
                Wait SETTLE_TIME (1s) for device to accept configuration

    Why the delays?

    SETTLE_TIME (1s) after each write allows the device to:
        - Process the attribute write
        - Update internal state
        - Prepare for next command

    Skipping delays can cause subsequent commands to fail because device
    hasn't finished processing the mode change.

    Args:
        cluster: WindowCovering cluster for Zigbee communication
        shade_type: Shade type from const.py (roller, cellular, vertical,
                   venetian, exterior_venetian)

    Raises:
        HomeAssistantError: If either write operation fails
            - Mode write failure → Zigbee communication issue
            - window_covering_type write failure → Invalid shade type or cluster issue

    Example:
        >>> await _calibration_phase_1_enter_mode(cluster, "venetian")
        # Device now in calibration mode, configured as venetian blind

    See Also:
        - _enter_calibration_mode(): Helper that writes mode=0x02
        - _exit_calibration_mode(): Reverses this (mode=0x00)
        - const.py SHADE_TYPE_TO_WINDOW_COVERING_TYPE: Mappings
    """
    sw = Stopwatch()

    kv(
        _LOGGER,
        logging.DEBUG,
        "PHASE 1: Entering calibration mode",
        shade_type=shade_type,
    )

    # Step 1: Enter calibration mode
    _LOGGER.debug("Step 1: Writing calibration mode = 0x02")
    await _enter_calibration_mode(cluster)
    await asyncio.sleep(SETTLE_TIME)

    # Step 2: Write & verify window_covering_type based on shade type
    window_covering_type = SHADE_TYPE_TO_WINDOW_COVERING_TYPE.get(shade_type, 0x00)
    try:
        await async_write_and_verify_attrs(
            cluster,
            {UBISYS_ATTR_CONFIGURED_MODE: window_covering_type},
            manufacturer=UBISYS_MANUFACTURER_CODE,
        )
    except Exception as err:
        raise HomeAssistantError(f"Failed to set window_covering_type: {err}") from err

    await asyncio.sleep(SETTLE_TIME)
    kv(
        _LOGGER,
        logging.DEBUG,
        "PHASE 1 complete",
        mode="calibration",
        window_covering_type=window_covering_type,
        elapsed_s=round(sw.elapsed, 1),
    )


async def _calibration_phase_2_find_top(
    hass: HomeAssistant,
    cluster: Cluster,
    entity_id: str,
) -> int:
    """PHASE 2: Find top limit via motor stall detection.

    Moves the blind upward until the motor stalls at the fully open position.
    This establishes the top reference point for the calibration.

    Phase Sequence:
        Step 3: Send up_open command (continuous upward movement)
        Step 4: Monitor position via stall detection algorithm
        Step 5: Send stop command when motor stalls

    Why Stall Detection?

    The J1 motor doesn't have limit switches or provide a "reached limit" signal.
    We must detect stall by monitoring the position attribute. See _wait_for_stall()
    for detailed algorithm explanation.

    Why Find Top First?

    Calibration sequence is always: top → bottom → top (verification)
        - Ensures consistent reference point
        - Follows deCONZ proven sequence
        - Allows device to count steps from known position

    Args:
        hass: Home Assistant instance for state monitoring
        cluster: WindowCovering cluster for sending commands
        entity_id: ZHA cover entity ID for position monitoring

    Returns:
        Final position when motor stalled at top (typically 100 = fully open)

    Raises:
        HomeAssistantError: If up_open command fails or timeout occurs

    Example:
        >>> pos = await _calibration_phase_2_find_top(hass, cluster, entity_id)
        >>> print(f"Top limit found at position {pos}")
        Top limit found at position 100

    See Also:
        - _wait_for_stall(): Stall detection algorithm
        - _calibration_phase_3_find_bottom(): Next phase
    """
    kv(
        _LOGGER,
        logging.INFO if is_verbose_info_logging(hass) else logging.DEBUG,
        "PHASE 2: Finding top limit",
    )

    # Step 3: Send up_open command
    _LOGGER.debug("Step 3: Sending up_open command")
    try:
        await async_zcl_command(cluster, "up_open", timeout_s=15.0, retries=1)
    except Exception as err:
        raise HomeAssistantError(f"Failed to send up_open command: {err}") from err

    # Step 4: Wait for motor stall
    _LOGGER.debug("Step 4: Waiting for motor stall at top position")
    final_position = await _wait_for_stall(hass, entity_id, "finding top limit (up)")

    # Step 5: Send stop command
    _LOGGER.debug("Step 5: Motor stalled at position %s - sending stop", final_position)
    try:
        await async_zcl_command(cluster, "stop", timeout_s=10.0, retries=1)
    except Exception as err:
        _LOGGER.warning("Failed to send stop command: %s", err)

    await asyncio.sleep(SETTLE_TIME)
    kv(
        _LOGGER,
        logging.INFO if is_verbose_info_logging(hass) else logging.DEBUG,
        "PHASE 2 complete",
        position=final_position,
    )

    return final_position


async def _calibration_phase_3_find_bottom(
    hass: HomeAssistant,
    cluster: Cluster,
    entity_id: str,
) -> int:
    """PHASE 3: Find bottom limit and read device-calculated total_steps.

    This is the CRITICAL PHASE where the Ubisys J1 device calculates total_steps
    (total motor steps from fully open to fully closed). The device performs this
    calculation internally during the down movement from top to bottom.

    Phase Sequence:
        Step 6: Send down_close command (continuous downward movement)
        Step 7: Monitor position until motor stalls at bottom limit
        Step 8: Send stop command to halt motor
        Step 9: Read total_steps attribute (device has calculated this value)

    Why does the device calculate total_steps?

    The J1 uses a stepper motor that counts steps during movement. When we complete
    the "Phase 2 (up) → Phase 3 (down)" sequence, the device knows exactly how many
    steps it took to traverse the full range. This is more accurate than trying to
    calculate it from position percentages because:
        - Avoids rounding errors
        - Accounts for mechanical tolerances
        - Matches device's internal step counter

    Example Calibration Flow:
        Phase 2 result: Top position = 100 (fully open)
        Phase 3 movement: Down from 100 → 0
        Device calculates: 5000 steps to traverse full range
        total_steps returned: 5000

    For Venetian Blinds:
        Phase 3 also determines the tilt range baseline. After reading total_steps
        (e.g., 4500 for a typical venetian), Phase 5 writes lift_to_tilt_transition_steps
        (typically 100) which tells the device how many steps are needed to fully
        tilt the slats.

    Common Failure Modes & Troubleshooting:

        1. total_steps = 0xFFFF (65535):
           → Device didn't complete calculation correctly
           → Usually means Phase 2 didn't complete properly
           → Check logs for Phase 2 completion message
           → Verify motor actually moved in Phase 2

        2. total_steps = 0:
           → Motor didn't move during Phase 3
           → Check for physical obstruction
           → Verify device is receiving commands
           → Check Zigbee signal strength

        3. Timeout before stall:
           → Motor moving extremely slowly
           → Could indicate mechanical issue
           → Try increasing PER_MOVE_TIMEOUT constant
           → Check for binding or friction

        4. total_steps seems wrong (too low/high):
           → Typical range: 1000-20000 steps
           → <1000: Very small blind or high step motor
           → >20000: Very large blind or low step motor
           → If suspiciously high/low, re-run calibration

    Args:
        hass: Home Assistant instance for state monitoring
        cluster: WindowCovering cluster for sending commands and reading attributes
        entity_id: ZHA cover entity ID for stall detection monitoring

    Returns:
        Total motor steps measured by device during full travel.
        Typical values: 1000-20000 depending on blind size and motor gearing.
        This value is used by the device for all subsequent position calculations.

    Raises:
        HomeAssistantError: If any of the following occur:
            - down_close command fails → Zigbee communication issue
            - Timeout during movement → Motor jammed or very slow
            - stop command fails → Warning logged, not fatal
            - total_steps read fails → Cluster communication issue
            - total_steps invalid (None or 0xFFFF) → Calibration incomplete

    Example:
        >>> total_steps = await _calibration_phase_3_find_bottom(hass, cluster, entity_id)
        >>> print(f"Device measured {total_steps} steps")
        Device measured 5000 steps

    See Also:
        - _calibration_phase_2_find_top(): Must complete before this phase
        - _wait_for_stall(): Used to detect bottom limit
        - UBISYS_ATTR_TOTAL_STEPS in const.py: Attribute definition
    """
    kv(
        _LOGGER,
        logging.INFO if is_verbose_info_logging(hass) else logging.DEBUG,
        "PHASE 3: Finding bottom limit",
    )

    # Step 6: Send down_close command
    _LOGGER.debug("Step 6: Sending down_close command")
    try:
        await async_zcl_command(cluster, "down_close", timeout_s=15.0, retries=1)
    except Exception as err:
        raise HomeAssistantError(f"Failed to send down_close command: {err}") from err

    # Step 7: Wait for motor stall
    _LOGGER.debug("Step 7: Waiting for motor stall at bottom position")
    final_position = await _wait_for_stall(
        hass, entity_id, "finding bottom limit (down)"
    )

    # Step 8: Send stop command
    _LOGGER.debug("Step 8: Motor stalled at position %s - sending stop", final_position)
    try:
        await async_zcl_command(cluster, "stop", timeout_s=10.0, retries=1)
    except Exception as err:
        _LOGGER.warning("Failed to send stop command: %s", err)

    await asyncio.sleep(SETTLE_TIME)

    # Step 9: Read total_steps from device
    sw = Stopwatch()
    _LOGGER.debug("Step 9: Reading total_steps attribute from device")
    try:
        result = await cluster.read_attributes(
            ["total_steps"],
            manufacturer=UBISYS_MANUFACTURER_CODE,
        )

        # Handle both name and ID in response
        total_steps = cast(
            int | None, result.get("total_steps") or result.get(UBISYS_ATTR_TOTAL_STEPS)
        )

        if total_steps is None or total_steps == 0xFFFF:
            raise HomeAssistantError(
                f"Invalid total_steps value: {total_steps}. "
                f"Device may not have completed calibration correctly."
            )

        kv(
            _LOGGER,
            logging.INFO if is_verbose_info_logging(hass) else logging.DEBUG,
            "PHASE 3 complete",
            total_steps=total_steps,
            elapsed_s=round(sw.elapsed, 1),
        )
        return total_steps

    except Exception as err:
        raise HomeAssistantError(
            f"Failed to read total_steps attribute: {err}"
        ) from err


async def _calibration_phase_4_verify(
    hass: HomeAssistant,
    cluster: Cluster,
    entity_id: str,
) -> int:
    """PHASE 4: Verification - return to top position.

    Moves blind back to top to verify calibration was successful. This ensures
    the device correctly learned the limits and can reproduce the top position.

    Why Verify?

    After finding top → bottom → measuring total_steps, we return to top to:
        1. Confirm device understood the calibration
        2. Verify total_steps measurement was accurate
        3. Leave blind in consistent state (fully open)
        4. Detect any calibration errors before finalizing

    What Success Looks Like:

    If calibration worked correctly:
        - Motor should stall at same position as Phase 2
        - Position should be ~100 (fully open)
        - Should take similar time as Phase 2

    What Indicates Problems:

    If verification fails:
        - Stalls at different position → total_steps incorrect
        - Times out → motor issue or obstruction
        - Stalls too early → device didn't learn limits

    Phase Sequence:
        Step 10: Send up_open command
        Step 11: Monitor until stall (should match Phase 2 position)
        Step 12: Send stop command

    Args:
        hass: Home Assistant instance for state monitoring
        cluster: WindowCovering cluster for commands
        entity_id: ZHA cover entity ID for position monitoring

    Returns:
        Final position when stalled (should be ~100, matching Phase 2)

    Raises:
        HomeAssistantError: If up_open fails or timeout occurs

    Example:
        >>> pos = await _calibration_phase_4_verify(hass, cluster, entity_id)
        >>> print(f"Verification complete, position {pos}")
        Verification complete, position 100

    See Also:
        - _calibration_phase_2_find_top(): Should match this position
        - _wait_for_stall(): Position monitoring algorithm
    """
    if is_verbose_info_logging(hass):
        _LOGGER.info("═══ PHASE 4: Verification - returning to top ═══")
    else:
        _LOGGER.debug("PHASE 4: Verification - returning to top")

    # Step 10: Send up_open command
    _LOGGER.debug("Step 10: Sending up_open command for verification")
    try:
        await async_zcl_command(cluster, "up_open", timeout_s=15.0, retries=1)
    except Exception as err:
        raise HomeAssistantError(
            f"Failed to send verification up_open command: {err}"
        ) from err

    # Step 11: Wait for motor stall
    _LOGGER.debug("Step 11: Waiting for motor stall at top position")
    final_position = await _wait_for_stall(
        hass, entity_id, "verification return to top"
    )

    # Step 12: Send stop command
    _LOGGER.debug("Step 12: Verification complete - sending stop")
    try:
        await async_zcl_command(cluster, "stop", timeout_s=10.0, retries=1)
    except Exception as err:
        _LOGGER.warning("Failed to send stop command: %s", err)

    await asyncio.sleep(SETTLE_TIME)
    kv(
        _LOGGER,
        logging.INFO if is_verbose_info_logging(hass) else logging.DEBUG,
        "PHASE 4 complete",
        result="verified",
    )

    return final_position


async def _calibration_phase_5_finalize(
    cluster: Cluster,
    shade_type: str,
    total_steps: int,
) -> None:
    """PHASE 5: Write tilt steps and exit calibration mode.

    Finalizes calibration by configuring tilt settings and returning device
    to normal operation mode.

    What are Tilt Steps?

    The lift_to_tilt_transition_steps attribute (0x1001) tells the device how
    many motor steps are needed to fully tilt the slats on a venetian blind.

    Values from const.py SHADE_TYPE_TILT_STEPS:
        - 0: Roller, cellular, vertical (no tilt capability)
        - 100: Venetian blinds (typical value for full tilt range)

    Why 100 for Venetian?

    This is a typical value that works for most venetian blinds. The actual
    mechanical tilt range is much smaller than the full lift range, so 100
    steps (vs. 1000-20000 for full lift) provides adequate tilt resolution.

    Phase Sequence:
        Step 13: Write lift_to_tilt_transition_steps based on shade type
                 Wait SETTLE_TIME for device to accept

        Step 14: Write mode=0x00 to exit calibration mode
                 Device returns to normal operation

    After This Phase:

    Device is now:
        - In normal operation mode
        - Fully calibrated with limits learned
        - Configured for correct shade type
        - Ready for position/tilt commands

    Args:
        cluster: WindowCovering cluster for attribute writes
        shade_type: Shade type (determines tilt_steps value)
        total_steps: Total steps from Phase 3 (for logging only)

    Raises:
        HomeAssistantError: If attribute writes fail

    Example:
        >>> await _calibration_phase_5_finalize(cluster, "venetian", 5000)
        # Device now in normal mode, tilt_steps=100, total_steps=5000

    See Also:
        - _exit_calibration_mode(): Helper for mode=0x00 write
        - const.py SHADE_TYPE_TILT_STEPS: Tilt step mappings
    """
    kv(
        _LOGGER,
        logging.DEBUG,
        "PHASE 5: Finalizing calibration",
    )

    # Step 13: Write + verify tilt transition steps
    tilt_steps = SHADE_TYPE_TILT_STEPS.get(shade_type, 0)
    try:
        await async_write_and_verify_attrs(
            cluster,
            {UBISYS_ATTR_LIFT_TO_TILT_TRANSITION_STEPS: tilt_steps},
            manufacturer=UBISYS_MANUFACTURER_CODE,
        )
    except Exception as err:
        raise HomeAssistantError(f"Failed to set tilt_steps: {err}") from err

    await asyncio.sleep(SETTLE_TIME)

    # Step 14: Exit calibration mode
    _LOGGER.debug("Step 14: Exiting calibration mode (mode=0x00)")
    await _exit_calibration_mode(cluster)

    _LOGGER.debug(
        "✓ PHASE 5 Complete: Calibration finalized (total_steps=%s, tilt_steps=%s)",
        total_steps,
        tilt_steps,
    )


async def _perform_calibration(
    hass: HomeAssistant,
    zha_entity_id: str,
    device_ieee: str,
    shade_type: str,
) -> None:
    """Orchestrate complete 5-phase calibration sequence.

    This is the main calibration orchestrator that coordinates all phases.
    Each phase is a separate function for modularity, testing, and clarity.

    ═══════════════════════════════════════════════════════════════
    CALIBRATION SEQUENCE OVERVIEW
    ═══════════════════════════════════════════════════════════════

    Phase 1: Preparation
    ├─ Enter calibration mode (mode=0x02)
    ├─ Configure shade type (configured_mode)
    └─ Purpose: Prepare device for measurement

    Phase 2: Find Top Limit
    ├─ Send up_open → monitor → stop at stall
    └─ Purpose: Establish fully-open reference point

    Phase 3: Find Bottom + Measure
    ├─ Send down_close → monitor → stop at stall
    ├─ Read total_steps (device calculated during movement)
    └─ Purpose: Establish fully-closed point + get travel distance

    Phase 4: Verification
    ├─ Send up_open → monitor → stop at stall
    └─ Purpose: Verify calibration worked (should reach same top position)

    Phase 5: Finalization
    ├─ Write tilt_steps (0 for rollers, 100 for venetian)
    ├─ Exit calibration mode (mode=0x00)
    └─ Purpose: Configure device and return to normal operation

    ═══════════════════════════════════════════════════════════════

    Error Handling Strategy:

    Each phase can fail independently. When a phase fails:
        1. Exception is raised with phase-specific message
        2. Cleanup handler attempts to exit calibration mode
        3. Original error is re-raised to service handler
        4. Service handler logs and reports to user

    This ensures:
        - User knows which phase failed (from error message)
        - Device doesn't stay stuck in calibration mode
        - Logs have full diagnostic information
        - User can safely retry calibration

    Args:
        hass: Home Assistant instance for state access
        zha_entity_id: ZHA cover entity ID for monitoring
        device_ieee: Device IEEE address for cluster access
        shade_type: Shade type for configuration

    Raises:
        HomeAssistantError: If any phase fails or cluster unavailable

    Duration:
        Roller/Cellular: 60-90 seconds
        Venetian: 90-120 seconds

        Factors:
        - Blind size (larger = more steps = slower)
        - Motor speed (Ubisys default is conservative)
        - Stall detection time (3s per limit × 3 movements = 9s minimum)

    Example:
        >>> await _perform_calibration(hass, "cover.zha_j1", "00:12:4b...", "roller")
        # Calibration completes, logs show each phase

    See Also:
        - _calibration_phase_N_xxx(): Individual phase implementations
        - async_calibrate_j1(): Service handler that calls this
    """
    if is_verbose_info_logging(hass):
        info_banner(
            _LOGGER,
            "Starting J1 Calibration",
            device_ieee=device_ieee,
            shade_type=shade_type,
        )

    try:
        overall_start = time.time()
        # Pre-flight validation
        await _validate_device_ready(hass, zha_entity_id)

        # Get WindowCovering cluster access
        cluster = await _get_window_covering_cluster(hass, device_ieee)
        if not cluster:
            raise HomeAssistantError(
                f"Could not access WindowCovering cluster for {device_ieee}"
            )

        # Execute 5-phase calibration sequence
        await _calibration_phase_1_enter_mode(cluster, shade_type)
        # Total timeout enforcement across phases
        if time.time() - overall_start > TOTAL_CALIBRATION_TIMEOUT:
            raise HomeAssistantError(
                "Calibration exceeded total timeout during Phase 1"
            )

        await _calibration_phase_2_find_top(hass, cluster, zha_entity_id)
        if time.time() - overall_start > TOTAL_CALIBRATION_TIMEOUT:
            raise HomeAssistantError(
                "Calibration exceeded total timeout during Phase 2"
            )
        total_steps = await _calibration_phase_3_find_bottom(
            hass, cluster, zha_entity_id
        )
        if time.time() - overall_start > TOTAL_CALIBRATION_TIMEOUT:
            raise HomeAssistantError(
                "Calibration exceeded total timeout during Phase 3"
            )
        await _calibration_phase_4_verify(hass, cluster, zha_entity_id)
        if time.time() - overall_start > TOTAL_CALIBRATION_TIMEOUT:
            raise HomeAssistantError(
                "Calibration exceeded total timeout during Phase 4"
            )
        await _calibration_phase_5_finalize(cluster, shade_type, total_steps)

        # Success!
        if is_verbose_info_logging(hass):
            info_banner(
                _LOGGER,
                "J1 Calibration Complete",
                device_ieee=device_ieee,
                total_steps=total_steps,
            )

    except Exception as err:
        if is_verbose_info_logging(hass):
            info_banner(
                _LOGGER,
                "J1 Calibration Failed",
                device_ieee=device_ieee,
                error=str(err),
            )

        # Attempt cleanup
        try:
            _LOGGER.debug("Attempting to exit calibration mode after error")
            cluster = await _get_window_covering_cluster(hass, device_ieee)
            if cluster:
                await _exit_calibration_mode(cluster)
        except Exception as cleanup_err:
            _LOGGER.warning(
                "Failed to exit calibration mode during cleanup: %s", cleanup_err
            )

        # Re-raise original error
        raise


async def _enter_calibration_mode(cluster: Cluster) -> None:
    """Enter calibration mode by writing mode attribute.

    Writes the calibration mode attribute (0x0017) with value 0x02 to enter
    the special calibration mode.

    What This Does:

    Sets manufacturer-specific attribute 0x0017 = 0x02, which tells the device:
        "I'm about to calibrate you. Start counting motor steps and prepare
         to calculate total_steps when I move you from top to bottom."

    Args:
        cluster: WindowCovering cluster for attribute write

    Raises:
        HomeAssistantError: If attribute write fails (Zigbee communication issue)

    See Also:
        - _exit_calibration_mode(): Reverses this (mode=0x00)
        - _calibration_phase_1_enter_mode(): Uses this helper
    """
    try:
        await cluster.write_attributes(
            {CALIBRATION_MODE_ATTR: CALIBRATION_MODE_ENTER},
            manufacturer=UBISYS_MANUFACTURER_CODE,
        )
        _LOGGER.debug("Entered calibration mode (mode=0x02)")
    except Exception as err:
        raise HomeAssistantError(f"Failed to enter calibration mode: {err}") from err


async def _exit_calibration_mode(cluster: Cluster) -> None:
    """Exit calibration mode by writing mode attribute.

    Writes the calibration mode attribute (0x0017) with value 0x00 to return
    the device to normal operation mode.

    What This Does:

    Sets manufacturer-specific attribute 0x0017 = 0x00, which tells the device:
        "Calibration complete. Use the total_steps you calculated for normal
         position control operations."

    When This Is Called:

        1. End of successful calibration (Phase 5)
        2. During error cleanup (if calibration fails midway)

    Why Cleanup Matters:

    If device is left in calibration mode:
        - Normal position commands may not work correctly
        - User must power cycle device to recover
        - Device behavior is undefined

    Therefore, we ALWAYS try to exit calibration mode, even during error handling.

    Args:
        cluster: WindowCovering cluster for attribute write

    Raises:
        HomeAssistantError: If attribute write fails

    See Also:
        - _enter_calibration_mode(): Sets mode=0x02
        - _calibration_phase_5_finalize(): Normal exit path
    """
    try:
        await cluster.write_attributes(
            {CALIBRATION_MODE_ATTR: CALIBRATION_MODE_EXIT},
            manufacturer=UBISYS_MANUFACTURER_CODE,
        )
        _LOGGER.debug("Exited calibration mode (mode=0x00)")
    except Exception as err:
        raise HomeAssistantError(f"Failed to exit calibration mode: {err}") from err


async def _wait_for_stall(
    hass: HomeAssistant,
    entity_id: str,
    phase_description: str,
    timeout: int = PER_MOVE_TIMEOUT,
) -> int:
    """Wait for motor stall via position monitoring (stall detection algorithm).

    The Ubisys J1 motor doesn't provide a "reached limit" signal. Instead, we must
    detect when the motor has stalled by monitoring the position attribute reported
    by the ZHA cover entity. A stall is detected when the position remains unchanged
    for STALL_DETECTION_TIME seconds (default 3s).

    This approach was derived from deCONZ's window_covering.cpp implementation,
    which has proven reliable across various blind types and motor speeds.

    ═══════════════════════════════════════════════════════════════
    STALL DETECTION ALGORITHM
    ═══════════════════════════════════════════════════════════════

    1. Poll position attribute every STALL_DETECTION_INTERVAL (0.5s)
    2. Compare current position to last known position
    3. If unchanged:
       - Start stall timer (if not already started)
       - If timer reaches STALL_DETECTION_TIME (3s): declare stall
    4. If position changes:
       - Reset stall timer
       - Update last_position
       - Continue monitoring
    5. If elapsed time exceeds timeout: raise error

    Why 3 seconds for stall detection?
        - <2s: False positives if motor briefly pauses during movement
        - >5s: Poor UX (user perceives lag, wasted time)
        - 3s: Balances reliability with user experience
        - Proven value from deCONZ implementation

    Why 0.5s polling interval?
        - Fast enough to detect stall promptly
        - Slow enough to avoid excessive state polling
        - Provides ~6 samples during 3s stall window

    Why 120s timeout?
        - Allows for very large blinds or slow motors
        - Prevents infinite loops if device fails
        - User can interrupt via Home Assistant if needed

    Args:
        hass: Home Assistant instance for state access
        entity_id: ZHA cover entity ID to monitor (NOT ubisys wrapper entity)
        phase_description: Human-readable phase description for logging
                          (e.g., "finding top limit", "verification return")
        timeout: Maximum seconds to wait before raising timeout error
                Default PER_MOVE_TIMEOUT (120s)

    Returns:
        Final position value when motor stalled (e.g., 100 for fully open,
        0 for fully closed). Position is in Home Assistant percentage format
        where 100 = fully open, 0 = fully closed.

    Raises:
        HomeAssistantError: If any of the following occur:
            - Motor doesn't stall within timeout period
              → Usually indicates jammed motor, physical obstruction,
                or device disconnected from Zigbee network
            - Entity not found during monitoring
              → ZHA entity was removed/disabled during calibration
            - Position attribute missing
              → Device not reporting position (rare, usually transient)

    Example:
        >>> # During Phase 2: Finding top limit
        >>> await cluster.command("up_open")  # Start upward movement
        >>> final_pos = await _wait_for_stall(hass, "cover.zha_j1", "finding top")
        >>> await cluster.command("stop")
        >>> print(f"Motor stalled at position {final_pos}")
        Motor stalled at position 100  # Fully open

    See Also:
        - _calibration_phase_2_find_top(): Uses this for top limit detection
        - _calibration_phase_3_find_bottom(): Uses this for bottom limit
        - _calibration_phase_4_verify(): Uses this for verification move
    """
    _LOGGER.debug(
        "Waiting for stall during '%s' (timeout: %ss, stall time: %ss)",
        phase_description,
        timeout,
        STALL_DETECTION_TIME,
    )

    start_time = time.time()
    last_position = None
    stall_start_time = None
    last_log_time = start_time

    while True:
        current_time = time.time()
        elapsed = current_time - start_time

        # Check timeout
        if elapsed > timeout:
            raise HomeAssistantError(
                f"Timeout during {phase_description} after {elapsed:.1f}s. "
                f"Last position: {last_position}. "
                f"Motor may be jammed, disconnected, or moving very slowly."
            )

        # Get current state
        state = hass.states.get(entity_id)
        if not state:
            raise HomeAssistantError(
                f"Entity not found during calibration: {entity_id}"
            )

        current_position = state.attributes.get("current_position")

        if current_position is None:
            _LOGGER.warning(
                "No current_position attribute during %s, waiting...", phase_description
            )
            await asyncio.sleep(STALL_DETECTION_INTERVAL)
            continue

        # Check if position has changed
        if current_position == last_position:
            # Position unchanged
            if stall_start_time is None:
                stall_start_time = current_time
                _LOGGER.debug(
                    "%s: Position stable at %s, starting stall timer",
                    phase_description,
                    current_position,
                )
            else:
                stall_duration = current_time - stall_start_time
                if stall_duration >= STALL_DETECTION_TIME:
                    # Stalled! Motor has reached limit
                    _LOGGER.info(
                        "%s: Motor stalled at position %s after %.1fs",
                        phase_description,
                        current_position,
                        stall_duration,
                    )
                    return int(current_position)
        else:
            # Position changed - motor still moving
            if last_position is not None:
                _LOGGER.debug(
                    "%s: Position changed from %s to %s (elapsed: %.1fs)",
                    phase_description,
                    last_position,
                    current_position,
                    elapsed,
                )
            stall_start_time = None
            last_position = current_position

        # Log progress every 5 seconds
        if current_time - last_log_time >= 5.0:
            _LOGGER.info(
                "%s: Still moving, position=%s, elapsed=%.1fs",
                phase_description,
                current_position,
                elapsed,
            )
            last_log_time = current_time

        # Wait before next check
        await asyncio.sleep(STALL_DETECTION_INTERVAL)


async def _get_window_covering_cluster(
    hass: HomeAssistant, device_ieee: str
) -> Cluster | None:
    """Get WindowCovering cluster for direct Zigbee access.

    Obtains the WindowCovering cluster object for sending commands and reading/writing
    attributes directly, bypassing Home Assistant's cover entity abstraction.

    Why Direct Cluster Access?

    Calibration requires low-level control that Home Assistant's cover entity
    doesn't provide:
        - Manufacturer-specific attribute access (mode, total_steps, tilt_steps)
        - Precise command timing (up_open → wait → stop)
        - Synchronous attribute reads during calibration
        - Timeout control for movements

    How It Works:

        1. Convert IEEE address string → EUI64 object
        2. Access ZHA gateway via integration data
        3. Look up device in gateway's device registry
        4. Find WindowCovering cluster on endpoint 2
        5. Return cluster object for direct use

    Endpoint Selection Strategy (CRITICAL FIX v1.2.0):

    The Ubisys J1 manual states:
        - Endpoint 1: Window Covering Device (server cluster 0x0102)
        - Endpoint 2: Window Covering Controller (client)

    However, field testing shows the cluster may be on either endpoint depending
    on firmware version or device configuration. Therefore, we probe BOTH:

        1. Try EP1 first (per manual specification)
        2. Fall back to EP2 if EP1 doesn't have the cluster
        3. Error only if neither endpoint has WindowCovering cluster

    This resilient approach ensures compatibility across firmware versions and
    prevents calibration failures due to endpoint assumptions.

    Args:
        hass: Home Assistant instance for integration data access
        device_ieee: Device IEEE address as string (e.g., "00:12:4b:00:1c:a1:b2:c3")

    Returns:
        WindowCovering cluster object, or None if not found

    Raises:
        HomeAssistantError: If IEEE address invalid or conversion fails

    Example:
        >>> cluster = await _get_window_covering_cluster(hass, "00:12:4b:00:1c...")
        >>> await cluster.command("up_open")  # Direct command
        >>> result = await cluster.read_attributes(["total_steps"])  # Direct read

    See Also:
        - custom_zha_quirks/ubisys_j1.py: Custom cluster definition
        - _perform_calibration(): Uses this to get cluster access
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

    # Get device from gateway
    try:
        from zigpy.types import EUI64

        try:
            device_eui64 = EUI64.convert(device_ieee)
        except (ValueError, TypeError) as err:
            _LOGGER.error("Invalid IEEE address format: %s", device_ieee)
            raise HomeAssistantError(
                f"Invalid device IEEE address: {device_ieee}"
            ) from err

        # Handle both old API (gateway.application_controller.devices) and new API (gateway.gateway.devices)
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

        # CRITICAL FIX (v1.2.0): Probe EP1 first (per manual), then EP2 (fallback)
        # Try Endpoint 1 first (Window Covering Device - server)
        _LOGGER.debug("Probing endpoint 1 for WindowCovering cluster...")
        endpoint = device.endpoints.get(1)
        if endpoint:
            cluster = endpoint.in_clusters.get(0x0102)
            if cluster:
                _LOGGER.log(
                    logging.INFO if is_verbose_info_logging(hass) else logging.DEBUG,
                    "✓ Found WindowCovering cluster on endpoint 1 (server)",
                )
                return cluster
            _LOGGER.debug("WindowCovering cluster not found on endpoint 1")
        else:
            _LOGGER.debug("Endpoint 1 not found on device")

        # Fall back to Endpoint 2 (Window Covering Controller - may have cluster in some firmware)
        _LOGGER.debug("Probing endpoint 2 for WindowCovering cluster...")
        endpoint = device.endpoints.get(2)
        if endpoint:
            cluster = endpoint.in_clusters.get(0x0102)
            if cluster:
                _LOGGER.log(
                    logging.INFO if is_verbose_info_logging(hass) else logging.DEBUG,
                    "✓ Found WindowCovering cluster on endpoint 2 (controller)",
                )
                return cluster
            _LOGGER.debug("WindowCovering cluster not found on endpoint 2")
        else:
            _LOGGER.debug("Endpoint 2 not found on device")

        # Neither endpoint has the cluster - this is an error
        _LOGGER.error(
            "WindowCovering cluster (0x0102) not found on endpoints 1 or 2 for device: %s",
            device_ieee,
        )
        # Register a Repairs issue for cluster not found
        try:
            from homeassistant.helpers import issue_registry as ir

            ir.async_create_issue(
                hass,
                DOMAIN,
                issue_id=f"window_covering_cluster_missing_{device_ieee}",
                is_fixable=False,
                severity=ir.IssueSeverity.ERROR,
                learn_more_url="https://github.com/jihlenburg/homeassistant-ubisys",
                translation_key=None,
                data={"device_ieee": device_ieee},
            )
        except Exception:
            _LOGGER.debug(
                "Unable to create Repairs issue for missing WindowCovering cluster"
            )
        return None

    except Exception as err:
        _LOGGER.error("Error accessing device cluster: %s", err)
        return None
