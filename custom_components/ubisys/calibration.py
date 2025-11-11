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
from typing import TYPE_CHECKING

from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er

from .const import (
    CONF_DEVICE_IEEE,
    CONF_SHADE_TYPE,
    DOMAIN,
    SHADE_TYPE_TILT_STEPS,
    UBISYS_ATTR_CONFIGURED_MODE,
    UBISYS_ATTR_LIFT_TO_TILT_TRANSITION_STEPS,
    UBISYS_ATTR_TOTAL_STEPS,
    UBISYS_MANUFACTURER_CODE,
)

if TYPE_CHECKING:
    from zigpy.zcl import Cluster

_LOGGER = logging.getLogger(__name__)

# Calibration constants
CALIBRATION_MODE_ATTR = 0x0017  # mode attribute for entering/exiting calibration
CALIBRATION_MODE_ENTER = 0x02  # Value to enter calibration mode
CALIBRATION_MODE_EXIT = 0x00  # Value to exit calibration mode

STALL_DETECTION_INTERVAL = 0.5  # Check position every 0.5 seconds
STALL_DETECTION_TIME = 3.0  # Position must be unchanged for 3 seconds to detect stall
PER_MOVE_TIMEOUT = 120  # Maximum 120 seconds per movement
TOTAL_CALIBRATION_TIMEOUT = 300  # Maximum 5 minutes total

SETTLE_TIME = 1.0  # Wait 1 second after stopping before next move


async def async_calibrate_j1(hass: HomeAssistant, call: ServiceCall) -> None:
    """Service handler for J1 calibration.

    Validates input parameters and delegates to calibration logic.

    Service data:
        entity_id: Entity ID of the Ubisys cover to calibrate

    Raises:
        HomeAssistantError: If parameters invalid or entity not found
    """
    entity_id = call.data.get("entity_id")

    # Validate entity_id parameter
    if not entity_id:
        raise HomeAssistantError("Missing required parameter: entity_id")

    if not isinstance(entity_id, str):
        raise HomeAssistantError(
            f"entity_id must be a string, got {type(entity_id).__name__}"
        )

    _LOGGER.info("Starting calibration for entity: %s", entity_id)

    # Verify entity exists and is a Ubisys entity
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

    _LOGGER.debug(
        "Service call validated: entity_id=%s, platform=%s",
        entity_id,
        entity_entry.platform,
    )

    # Get device information
    device_ieee = config_entry.data.get(CONF_DEVICE_IEEE)
    shade_type = config_entry.data.get(CONF_SHADE_TYPE)

    if not device_ieee or not shade_type:
        raise HomeAssistantError("Missing device information in config entry")

    # Find ZHA cover entity
    zha_entity_id = await _find_zha_cover_entity(hass, entity_entry.device_id)
    if not zha_entity_id:
        raise HomeAssistantError(f"ZHA cover entity not found for: {entity_id}")

    # Initialize device locks dict if needed
    if "calibration_locks" not in hass.data.setdefault(DOMAIN, {}):
        hass.data[DOMAIN]["calibration_locks"] = {}

    locks = hass.data[DOMAIN]["calibration_locks"]

    # Get or create lock for this specific device
    if device_ieee not in locks:
        locks[device_ieee] = asyncio.Lock()

    device_lock = locks[device_ieee]

    # Check if calibration already in progress (non-blocking check)
    if device_lock.locked():
        raise HomeAssistantError(
            f"Calibration already in progress for device {device_ieee}. "
            f"Please wait for the current calibration to complete."
        )

    # Acquire lock and perform calibration
    async with device_lock:
        _LOGGER.info(
            "Acquired calibration lock for device %s - starting calibration",
            device_ieee,
        )
        calibration_start = time.time()

        try:
            await _perform_calibration(
                hass, zha_entity_id, device_ieee, shade_type
            )
            elapsed = time.time() - calibration_start
            _LOGGER.info(
                "Calibration completed successfully for %s in %.1f seconds",
                entity_id,
                elapsed
            )
        except Exception as err:
            _LOGGER.error("Calibration failed for %s: %s", entity_id, err)
            # Try to exit calibration mode on error
            try:
                cluster = await _get_window_covering_cluster(hass, device_ieee)
                if cluster:
                    await _exit_calibration_mode(cluster)
            except Exception as cleanup_err:
                _LOGGER.error("Failed to exit calibration mode during cleanup: %s", cleanup_err)
            raise HomeAssistantError(f"Calibration failed: {err}") from err
        finally:
            _LOGGER.debug("Released calibration lock for device %s", device_ieee)


async def _find_zha_cover_entity(hass: HomeAssistant, device_id: str) -> str | None:
    """Find the ZHA cover entity for a device."""
    entity_registry = er.async_get(hass)
    entities = er.async_entries_for_device(entity_registry, device_id)

    for entity_entry in entities:
        if entity_entry.platform == "zha" and entity_entry.domain == "cover":
            return entity_entry.entity_id

    return None



async def _validate_device_ready(hass: HomeAssistant, entity_id: str) -> None:
    """Validate device is ready for calibration.

    Pre-flight checks:
    - Device exists in Home Assistant
    - Device is available (not offline)
    - Device reports current_position attribute

    Args:
        hass: Home Assistant instance
        entity_id: Entity ID of the cover to validate

    Raises:
        HomeAssistantError: If device is not ready for calibration
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


async def _calibration_phase_1_enter_mode(
    cluster: Cluster,
    shade_type: str,
) -> None:
    """PHASE 1: Enter calibration mode and configure shade type.

    Steps:
    1. Enter calibration mode (mode=0x02)
    2. Write configured_mode based on shade type

    Args:
        cluster: WindowCovering cluster instance
        shade_type: Type of shade being calibrated

    Raises:
        HomeAssistantError: If any step fails
    """
    _LOGGER.info("═══ PHASE 1: Entering calibration mode ═══")

    # Step 1: Enter calibration mode
    _LOGGER.debug("Step 1: Writing calibration mode = 0x02")
    await _enter_calibration_mode(cluster)
    await asyncio.sleep(SETTLE_TIME)

    # Step 2: Write configured_mode based on shade type
    configured_mode = SHADE_TYPE_TO_WINDOW_COVERING_TYPE.get(shade_type, 0x00)
    _LOGGER.debug(
        "Step 2: Writing configured_mode = 0x%02X (shade type: %s)",
        configured_mode,
        shade_type,
    )

    try:
        await cluster.write_attributes(
            {UBISYS_ATTR_CONFIGURED_MODE: configured_mode},
            manufacturer=UBISYS_MANUFACTURER_CODE,
        )
    except Exception as err:
        raise HomeAssistantError(
            f"Failed to write configured_mode: {err}"
        ) from err

    await asyncio.sleep(SETTLE_TIME)
    _LOGGER.info("✓ PHASE 1 Complete: Calibration mode active")


async def _calibration_phase_2_find_top(
    hass: HomeAssistant,
    cluster: Cluster,
    entity_id: str,
) -> int:
    """PHASE 2: Find top limit via motor stall detection.

    Moves blind UP until motor stalls, indicating fully open position.

    Args:
        hass: Home Assistant instance
        cluster: WindowCovering cluster instance
        entity_id: Entity ID for stall detection

    Returns:
        Final position when motor stalled (fully open)

    Raises:
        HomeAssistantError: If movement times out or fails
    """
    _LOGGER.info("═══ PHASE 2: Finding top limit (fully open) ═══")

    # Step 3: Send up_open command
    _LOGGER.debug("Step 3: Sending up_open command")
    try:
        await cluster.command("up_open")
    except Exception as err:
        raise HomeAssistantError(
            f"Failed to send up_open command: {err}"
        ) from err

    # Step 4: Wait for motor stall
    _LOGGER.debug("Step 4: Waiting for motor stall at top position")
    final_position = await _wait_for_stall(
        hass, entity_id, "finding top limit (up)"
    )

    # Step 5: Send stop command
    _LOGGER.debug(
        "Step 5: Motor stalled at position %s - sending stop",
        final_position
    )
    try:
        await cluster.command("stop")
    except Exception as err:
        _LOGGER.warning("Failed to send stop command: %s", err)

    await asyncio.sleep(SETTLE_TIME)
    _LOGGER.info("✓ PHASE 2 Complete: Top limit found at position %s", final_position)

    return final_position


async def _calibration_phase_3_find_bottom(
    hass: HomeAssistant,
    cluster: Cluster,
    entity_id: str,
) -> int:
    """PHASE 3: Find bottom limit and read total_steps.

    Moves blind DOWN until motor stalls, then reads device-calculated total_steps.

    Args:
        hass: Home Assistant instance
        cluster: WindowCovering cluster instance
        entity_id: Entity ID for stall detection

    Returns:
        Total motor steps measured by device (e.g., 5000)

    Raises:
        HomeAssistantError: If movement fails or total_steps invalid
    """
    _LOGGER.info("═══ PHASE 3: Finding bottom limit (fully closed) ═══")

    # Step 6: Send down_close command
    _LOGGER.debug("Step 6: Sending down_close command")
    try:
        await cluster.command("down_close")
    except Exception as err:
        raise HomeAssistantError(
            f"Failed to send down_close command: {err}"
        ) from err

    # Step 7: Wait for motor stall
    _LOGGER.debug("Step 7: Waiting for motor stall at bottom position")
    final_position = await _wait_for_stall(
        hass, entity_id, "finding bottom limit (down)"
    )

    # Step 8: Send stop command
    _LOGGER.debug(
        "Step 8: Motor stalled at position %s - sending stop",
        final_position
    )
    try:
        await cluster.command("stop")
    except Exception as err:
        _LOGGER.warning("Failed to send stop command: %s", err)

    await asyncio.sleep(SETTLE_TIME)

    # Step 9: Read total_steps from device
    _LOGGER.debug("Step 9: Reading total_steps attribute from device")
    try:
        result = await cluster.read_attributes(
            ["total_steps"],
            manufacturer=UBISYS_MANUFACTURER_CODE,
        )

        # Handle both name and ID in response
        total_steps = result.get("total_steps") or result.get(UBISYS_ATTR_TOTAL_STEPS)

        if total_steps is None or total_steps == 0xFFFF:
            raise HomeAssistantError(
                f"Invalid total_steps value: {total_steps}. "
                f"Device may not have completed calibration correctly."
            )

        _LOGGER.info(
            "✓ PHASE 3 Complete: Bottom limit found, total_steps = %s",
            total_steps
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

    Moves blind back UP to verify calibration was successful.

    Args:
        hass: Home Assistant instance
        cluster: WindowCovering cluster instance
        entity_id: Entity ID for stall detection

    Returns:
        Final position after verification (should be top)

    Raises:
        HomeAssistantError: If verification movement fails
    """
    _LOGGER.info("═══ PHASE 4: Verification - returning to top ═══")

    # Step 10: Send up_open command
    _LOGGER.debug("Step 10: Sending up_open command for verification")
    try:
        await cluster.command("up_open")
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
        await cluster.command("stop")
    except Exception as err:
        _LOGGER.warning("Failed to send stop command: %s", err)

    await asyncio.sleep(SETTLE_TIME)
    _LOGGER.info("✓ PHASE 4 Complete: Verification successful")

    return final_position


async def _calibration_phase_5_finalize(
    cluster: Cluster,
    shade_type: str,
    total_steps: int,
) -> None:
    """PHASE 5: Write tilt steps and exit calibration mode.

    Configures tilt settings based on shade type and exits calibration mode.

    Args:
        cluster: WindowCovering cluster instance
        shade_type: Type of shade (determines tilt steps)
        total_steps: Total steps measured during calibration (for logging)

    Raises:
        HomeAssistantError: If finalization fails
    """
    _LOGGER.info("═══ PHASE 5: Finalizing calibration ═══")

    # Step 13: Write tilt transition steps
    tilt_steps = SHADE_TYPE_TILT_STEPS.get(shade_type, 0)
    _LOGGER.debug(
        "Step 13: Writing tilt_steps = %s (shade type: %s)",
        tilt_steps,
        shade_type,
    )

    try:
        await cluster.write_attributes(
            {UBISYS_ATTR_LIFT_TO_TILT_TRANSITION_STEPS: tilt_steps},
            manufacturer=UBISYS_MANUFACTURER_CODE,
        )
    except Exception as err:
        raise HomeAssistantError(
            f"Failed to write tilt_steps attribute: {err}"
        ) from err

    await asyncio.sleep(SETTLE_TIME)

    # Step 14: Exit calibration mode
    _LOGGER.debug("Step 14: Exiting calibration mode (mode=0x00)")
    await _exit_calibration_mode(cluster)

    _LOGGER.info(
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
    """Perform complete 5-phase calibration sequence.

    This function orchestrates the automated calibration process using motor
    stall detection to find physical limits and configure the device.

    Calibration Sequence:
        1. Enter calibration mode and configure shade type
        2. Find top limit (fully open) via stall detection
        3. Find bottom limit (fully closed) and read total_steps
        4. Verification move back to top
        5. Write tilt settings and exit calibration mode

    Args:
        hass: Home Assistant instance
        zha_entity_id: Entity ID of the ZHA cover entity
        device_ieee: IEEE address of the device
        shade_type: Type of shade being calibrated

    Raises:
        HomeAssistantError: If any calibration phase fails

    Duration:
        Typically 60-120 seconds depending on blind size and motor speed.
    """
    _LOGGER.info("╔═══════════════════════════════════════════════════════╗")
    _LOGGER.info("║  Starting Calibration for %s", device_ieee.ljust(24) + "║")
    _LOGGER.info("║  Shade Type: %s", shade_type.ljust(38) + "║")
    _LOGGER.info("╚═══════════════════════════════════════════════════════╝")

    try:
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
        await _calibration_phase_2_find_top(hass, cluster, zha_entity_id)
        total_steps = await _calibration_phase_3_find_bottom(hass, cluster, zha_entity_id)
        await _calibration_phase_4_verify(hass, cluster, zha_entity_id)
        await _calibration_phase_5_finalize(cluster, shade_type, total_steps)

        # Success!
        _LOGGER.info("╔═══════════════════════════════════════════════════════╗")
        _LOGGER.info("║  ✅ Calibration Completed Successfully!              ║")
        _LOGGER.info("║  Total Steps: %s", str(total_steps).ljust(38) + "║")
        _LOGGER.info("║  Device: %s", device_ieee.ljust(43) + "║")
        _LOGGER.info("╚═══════════════════════════════════════════════════════╝")

    except Exception as err:
        _LOGGER.error("╔═══════════════════════════════════════════════════════╗")
        _LOGGER.error("║  ❌ Calibration Failed                                ║")
        _LOGGER.error("║  Error: %s", str(err)[:45].ljust(45) + "║")
        _LOGGER.error("╚═══════════════════════════════════════════════════════╝")

        # Attempt cleanup
        try:
            _LOGGER.debug("Attempting to exit calibration mode after error")
            cluster = await _get_window_covering_cluster(hass, device_ieee)
            if cluster:
                await _exit_calibration_mode(cluster)
        except Exception as cleanup_err:
            _LOGGER.warning(
                "Failed to exit calibration mode during cleanup: %s",
                cleanup_err
            )

        # Re-raise original error
        raise


async def _enter_calibration_mode(cluster: Cluster) -> None:
    """Enter calibration mode by setting mode attribute to 0x02.

    Args:
        cluster: WindowCovering cluster instance

    Raises:
        HomeAssistantError: If entering calibration mode fails
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
    """Exit calibration mode by setting mode attribute to 0x00.

    Args:
        cluster: WindowCovering cluster instance

    Raises:
        HomeAssistantError: If exiting calibration mode fails
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
    """Wait for motor to stall (reach limit) by monitoring position.

    Stall is detected when the position hasn't changed for STALL_DETECTION_TIME seconds.

    Args:
        hass: Home Assistant instance
        entity_id: Cover entity ID to monitor
        phase_description: Description of current phase (for logging)
        timeout: Maximum time to wait in seconds

    Returns:
        Final position when stall was detected

    Raises:
        HomeAssistantError: If timeout is reached or entity not found
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
            raise HomeAssistantError(f"Entity not found during calibration: {entity_id}")

        current_position = state.attributes.get("current_position")

        if current_position is None:
            _LOGGER.warning(
                "No current_position attribute during %s, waiting...",
                phase_description
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
                    current_position
                )
            else:
                stall_duration = current_time - stall_start_time
                if stall_duration >= STALL_DETECTION_TIME:
                    # Stalled! Motor has reached limit
                    _LOGGER.info(
                        "%s: Motor stalled at position %s after %.1fs",
                        phase_description,
                        current_position,
                        stall_duration
                    )
                    return current_position
        else:
            # Position changed - motor still moving
            if last_position is not None:
                _LOGGER.debug(
                    "%s: Position changed from %s to %s (elapsed: %.1fs)",
                    phase_description,
                    last_position,
                    current_position,
                    elapsed
                )
            stall_start_time = None
            last_position = current_position

        # Log progress every 5 seconds
        if current_time - last_log_time >= 5.0:
            _LOGGER.info(
                "%s: Still moving, position=%s, elapsed=%.1fs",
                phase_description,
                current_position,
                elapsed
            )
            last_log_time = current_time

        # Wait before next check
        await asyncio.sleep(STALL_DETECTION_INTERVAL)


async def _get_window_covering_cluster(
    hass: HomeAssistant, device_ieee: str
) -> Cluster | None:
    """Get the WindowCovering cluster for a device.

    Args:
        hass: Home Assistant instance
        device_ieee: IEEE address of the device

    Returns:
        WindowCovering cluster instance or None if not found
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

        device = gateway.application_controller.devices.get(device_eui64)

        if not device:
            _LOGGER.error("Device not found in ZHA gateway: %s", device_ieee)
            return None

        # Get WindowCovering cluster from endpoint 2
        endpoint = device.endpoints.get(2)
        if not endpoint:
            _LOGGER.error("Endpoint 2 not found for device: %s", device_ieee)
            return None

        cluster = endpoint.in_clusters.get(0x0102)  # WindowCovering cluster ID
        if not cluster:
            _LOGGER.error("WindowCovering cluster not found for device: %s", device_ieee)
            return None

        return cluster

    except Exception as err:
        _LOGGER.error("Error accessing device cluster: %s", err)
        return None
