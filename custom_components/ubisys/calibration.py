"""Calibration module for Ubisys J1 window covering controller.

This module provides automated calibration of Ubisys J1 devices to determine
the total motor steps and configure tilt transition steps based on shade type.
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import device_registry as dr, entity_registry as er

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
CALIBRATION_TIMEOUT = 120  # seconds
MOVE_COMPLETE_CHECK_INTERVAL = 2  # seconds
MOVE_COMPLETE_POSITION_THRESHOLD = 2  # percent


async def async_calibrate_j1(hass: HomeAssistant, call: ServiceCall) -> None:
    """Service handler for J1 calibration.

    Service data:
        entity_id: Entity ID of the Ubisys cover to calibrate
    """
    entity_id = call.data.get("entity_id")

    if not entity_id:
        raise HomeAssistantError("Missing required parameter: entity_id")

    _LOGGER.info("Starting calibration for entity: %s", entity_id)

    # Find the config entry for this entity
    entity_registry = er.async_get(hass)
    entity_entry = entity_registry.async_get(entity_id)

    if not entity_entry:
        raise HomeAssistantError(f"Entity not found: {entity_id}")

    config_entry_id = entity_entry.config_entry_id
    if not config_entry_id:
        raise HomeAssistantError(f"Entity has no config entry: {entity_id}")

    config_entry = hass.config_entries.async_get_entry(config_entry_id)
    if not config_entry or config_entry.domain != DOMAIN:
        raise HomeAssistantError(f"Invalid config entry for entity: {entity_id}")

    # Get device information
    device_ieee = config_entry.data.get(CONF_DEVICE_IEEE)
    shade_type = config_entry.data.get(CONF_SHADE_TYPE)

    if not device_ieee or not shade_type:
        raise HomeAssistantError("Missing device information in config entry")

    # Find ZHA cover entity
    zha_entity_id = await _find_zha_cover_entity(hass, entity_entry.device_id)
    if not zha_entity_id:
        raise HomeAssistantError(f"ZHA cover entity not found for: {entity_id}")

    # Perform calibration
    try:
        await _perform_calibration(
            hass, zha_entity_id, device_ieee, shade_type
        )
        _LOGGER.info("Calibration completed successfully for: %s", entity_id)
    except Exception as err:
        _LOGGER.error("Calibration failed for %s: %s", entity_id, err)
        raise HomeAssistantError(f"Calibration failed: {err}") from err


async def _find_zha_cover_entity(hass: HomeAssistant, device_id: str) -> str | None:
    """Find the ZHA cover entity for a device."""
    entity_registry = er.async_get(hass)
    entities = er.async_entries_for_device(entity_registry, device_id)

    for entity_entry in entities:
        if entity_entry.platform == "zha" and entity_entry.domain == "cover":
            return entity_entry.entity_id

    return None


async def _perform_calibration(
    hass: HomeAssistant,
    zha_entity_id: str,
    device_ieee: str,
    shade_type: str,
) -> None:
    """Perform the calibration sequence.

    Steps:
        1. Store current position
        2. Move to 100% open
        3. Wait for move to complete
        4. Read current_position_lift_percentage (should be 0 = fully open)
        5. Move to 0% closed
        6. Wait for move to complete
        7. Read total steps from manufacturer attribute
        8. Calculate and write tilt transition steps
        9. Write configured_mode
        10. Restore original position (optional)
    """
    _LOGGER.info("Starting calibration sequence for %s", device_ieee)

    # Get ZHA cluster access
    window_covering_cluster = await _get_window_covering_cluster(hass, device_ieee)
    if not window_covering_cluster:
        raise HomeAssistantError(
            f"Could not access WindowCovering cluster for {device_ieee}"
        )

    # Step 1: Store current position
    current_state = hass.states.get(zha_entity_id)
    original_position = current_state.attributes.get("current_position") if current_state else None
    _LOGGER.debug("Original position: %s", original_position)

    # Step 2: Move to 100% open (position 100 in HA = fully open)
    _LOGGER.info("Calibration step 1/5: Moving to fully open position")
    await hass.services.async_call(
        "cover",
        "set_cover_position",
        {"entity_id": zha_entity_id, "position": 100},
        blocking=False,
    )

    # Step 3: Wait for move to complete
    await _wait_for_move_complete(hass, zha_entity_id, target_position=100)
    _LOGGER.info("Move to open position complete")

    # Step 4: Small delay to ensure position is settled
    await asyncio.sleep(2)

    # Step 5: Move to 0% closed (position 0 in HA = fully closed)
    _LOGGER.info("Calibration step 2/5: Moving to fully closed position")
    await hass.services.async_call(
        "cover",
        "set_cover_position",
        {"entity_id": zha_entity_id, "position": 0},
        blocking=False,
    )

    # Step 6: Wait for move to complete
    await _wait_for_move_complete(hass, zha_entity_id, target_position=0)
    _LOGGER.info("Move to closed position complete")

    # Step 7: Small delay before reading attributes
    await asyncio.sleep(2)

    # Step 8: Read total_steps
    _LOGGER.info("Calibration step 3/5: Reading total_steps from device")
    try:
        result = await window_covering_cluster.read_attributes(
            ["total_steps"],
            manufacturer=UBISYS_MANUFACTURER_CODE,
        )
        total_steps = result.get("total_steps") or result.get(UBISYS_ATTR_TOTAL_STEPS)

        if total_steps is None or total_steps == 0:
            raise HomeAssistantError(
                "Failed to read valid total_steps from device. "
                "Ensure the device has been manually operated through its full range at least once."
            )

        _LOGGER.info("Total steps read from device: %s", total_steps)

    except Exception as err:
        _LOGGER.error("Failed to read total_steps: %s", err)
        raise HomeAssistantError(f"Failed to read calibration data: {err}") from err

    # Step 9: Calculate and write tilt transition steps
    tilt_steps = SHADE_TYPE_TILT_STEPS.get(shade_type, 0)
    _LOGGER.info("Calibration step 4/5: Writing tilt transition steps: %s", tilt_steps)

    try:
        await window_covering_cluster.write_attributes(
            {UBISYS_ATTR_LIFT_TO_TILT_TRANSITION_STEPS: tilt_steps},
            manufacturer=UBISYS_MANUFACTURER_CODE,
        )
        _LOGGER.debug("Successfully wrote lift_to_tilt_transition_steps: %s", tilt_steps)
    except Exception as err:
        _LOGGER.error("Failed to write tilt transition steps: %s", err)
        raise HomeAssistantError(f"Failed to write tilt transition steps: {err}") from err

    # Step 10: Write configured_mode
    # Mode mapping: roller=0, cellular=1, vertical=2, venetian=3, exterior_venetian=4
    mode_mapping = {
        "roller": 0,
        "cellular": 1,
        "vertical": 2,
        "venetian": 3,
        "exterior_venetian": 4,
    }
    configured_mode = mode_mapping.get(shade_type, 0)
    _LOGGER.info("Calibration step 5/5: Writing configured_mode: %s (%s)", configured_mode, shade_type)

    try:
        await window_covering_cluster.write_attributes(
            {UBISYS_ATTR_CONFIGURED_MODE: configured_mode},
            manufacturer=UBISYS_MANUFACTURER_CODE,
        )
        _LOGGER.debug("Successfully wrote configured_mode: %s", configured_mode)
    except Exception as err:
        _LOGGER.error("Failed to write configured_mode: %s", err)
        raise HomeAssistantError(f"Failed to write configured_mode: {err}") from err

    # Optional: Restore original position
    if original_position is not None:
        _LOGGER.info("Restoring original position: %s", original_position)
        await hass.services.async_call(
            "cover",
            "set_cover_position",
            {"entity_id": zha_entity_id, "position": original_position},
            blocking=False,
        )

    _LOGGER.info("Calibration sequence completed successfully")


async def _wait_for_move_complete(
    hass: HomeAssistant,
    entity_id: str,
    target_position: int,
    timeout: int = CALIBRATION_TIMEOUT,
) -> None:
    """Wait for cover to reach target position.

    Args:
        hass: Home Assistant instance
        entity_id: Cover entity ID to monitor
        target_position: Target position to wait for (0-100)
        timeout: Maximum time to wait in seconds

    Raises:
        HomeAssistantError: If timeout is reached
    """
    _LOGGER.debug(
        "Waiting for %s to reach position %s (timeout: %ss)",
        entity_id,
        target_position,
        timeout,
    )

    start_time = asyncio.get_event_loop().time()

    while True:
        # Check timeout
        elapsed = asyncio.get_event_loop().time() - start_time
        if elapsed > timeout:
            raise HomeAssistantError(
                f"Timeout waiting for cover to reach position {target_position}"
            )

        # Get current state
        state = hass.states.get(entity_id)
        if not state:
            raise HomeAssistantError(f"Entity not found: {entity_id}")

        # Check if still moving
        is_closing = state.attributes.get("is_closing", False)
        is_opening = state.attributes.get("is_opening", False)
        current_position = state.attributes.get("current_position")

        if current_position is None:
            _LOGGER.warning("No current_position attribute, waiting...")
            await asyncio.sleep(MOVE_COMPLETE_CHECK_INTERVAL)
            continue

        # Check if target reached
        position_diff = abs(current_position - target_position)
        is_moving = is_closing or is_opening

        if not is_moving and position_diff <= MOVE_COMPLETE_POSITION_THRESHOLD:
            _LOGGER.debug(
                "Target position reached: current=%s, target=%s",
                current_position,
                target_position,
            )
            return

        # Log progress
        _LOGGER.debug(
            "Move in progress: current=%s, target=%s, moving=%s, elapsed=%.1fs",
            current_position,
            target_position,
            is_moving,
            elapsed,
        )

        # Wait before next check
        await asyncio.sleep(MOVE_COMPLETE_CHECK_INTERVAL)


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

        device_eui64 = EUI64.convert(device_ieee)
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
