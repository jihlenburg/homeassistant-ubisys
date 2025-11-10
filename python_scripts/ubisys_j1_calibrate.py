"""Ubisys J1 Calibration Script.

This script performs the calibration sequence for Ubisys J1 window covering controllers:
1. Set WindowCoveringType based on shade configuration
2. Move to fully open position
3. Reset position counter to zero
4. Move to fully closed while counting steps
5. Read and store total_steps (attribute 0x1002)
6. For venetian: also read tilt transition steps
7. Send completion notification

Usage:
  Call via Home Assistant service:
  python_script.ubisys_j1_calibrate entity_id="cover.bedroom_shade" shade_type="venetian"
"""

import asyncio
import logging

_LOGGER = logging.getLogger(__name__)

# Zigbee constants
CLUSTER_WINDOW_COVERING = 0x0102
ATTR_WINDOW_COVERING_TYPE = 0x0000
ATTR_CURRENT_POSITION_LIFT = 0x0008
UBISYS_MANUFACTURER_CODE = 0x10F2
UBISYS_ATTR_TOTAL_STEPS = 0x1002
UBISYS_ATTR_LIFT_TO_TILT_TRANSITION_STEPS = 0x1001

# Shade type to WindowCoveringType mapping
SHADE_TYPE_MAPPING = {
    "roller": 0x00,
    "cellular": 0x00,
    "vertical": 0x04,
    "venetian": 0x08,
    "exterior_venetian": 0x08,
}


def validate_inputs():
    """Validate required inputs."""
    if "entity_id" not in data:
        _LOGGER.error("entity_id is required")
        return False

    if "shade_type" not in data:
        _LOGGER.error("shade_type is required")
        return False

    if data["shade_type"] not in SHADE_TYPE_MAPPING:
        _LOGGER.error("Invalid shade_type: %s", data["shade_type"])
        return False

    return True


async def get_zha_device(entity_id):
    """Get ZHA device from entity_id."""
    try:
        # Get entity registry
        entity_registry = hass.helpers.entity_registry.async_get(hass)
        entity_entry = entity_registry.async_get(entity_id)

        if entity_entry is None:
            _LOGGER.error("Entity %s not found in registry", entity_id)
            return None

        # Get device from ZHA
        zha_gateway = hass.data.get("zha", {}).get("zha_gateway")
        if zha_gateway is None:
            _LOGGER.error("ZHA gateway not found")
            return None

        # Get the device
        ieee = entity_entry.unique_id.split("-")[0]
        device = zha_gateway.get_device(ieee)

        if device is None:
            _LOGGER.error("ZHA device not found for entity %s", entity_id)
            return None

        return device

    except Exception as e:
        _LOGGER.error("Error getting ZHA device: %s", str(e))
        return None


async def get_window_covering_cluster(device):
    """Get the Window Covering cluster from the device."""
    try:
        # Ubisys J1 uses endpoint 2 for window covering
        endpoint = device.endpoints.get(2)
        if endpoint is None:
            _LOGGER.error("Endpoint 2 not found on device")
            return None

        cluster = endpoint.in_clusters.get(CLUSTER_WINDOW_COVERING)
        if cluster is None:
            _LOGGER.error("Window Covering cluster not found on endpoint 2")
            return None

        return cluster

    except Exception as e:
        _LOGGER.error("Error getting Window Covering cluster: %s", str(e))
        return None


async def calibrate():
    """Run the calibration sequence."""
    entity_id = data["entity_id"]
    shade_type = data["shade_type"]
    window_covering_type = SHADE_TYPE_MAPPING[shade_type]

    _LOGGER.info(
        "Starting calibration for %s with shade_type=%s (WindowCoveringType=0x%02x)",
        entity_id,
        shade_type,
        window_covering_type,
    )

    try:
        # Get ZHA device and cluster
        device = await get_zha_device(entity_id)
        if device is None:
            raise Exception("Could not get ZHA device")

        cluster = await get_window_covering_cluster(device)
        if cluster is None:
            raise Exception("Could not get Window Covering cluster")

        # Step 1: Set WindowCoveringType
        _LOGGER.info("Step 1: Setting WindowCoveringType to 0x%02x", window_covering_type)
        await cluster.write_attributes(
            {ATTR_WINDOW_COVERING_TYPE: window_covering_type}
        )
        await asyncio.sleep(1)

        # Step 2: Move to fully open position
        _LOGGER.info("Step 2: Moving to fully open position")
        await hass.services.async_call(
            "cover",
            "open_cover",
            {"entity_id": entity_id},
            blocking=False,
        )

        # Wait for movement to complete (poll position)
        await asyncio.sleep(2)
        for _ in range(60):  # Max 60 seconds
            state = hass.states.get(entity_id)
            if state and not state.attributes.get("is_opening"):
                break
            await asyncio.sleep(1)

        _LOGGER.info("Reached open position")
        await asyncio.sleep(2)

        # Step 3: Reset position counter (write 0 to current_position_lift)
        _LOGGER.info("Step 3: Resetting position counter to 0")
        await cluster.write_attributes(
            {ATTR_CURRENT_POSITION_LIFT: 0},
            manufacturer=UBISYS_MANUFACTURER_CODE,
        )
        await asyncio.sleep(1)

        # Step 4: Move to fully closed position
        _LOGGER.info("Step 4: Moving to fully closed position to count steps")
        await hass.services.async_call(
            "cover",
            "close_cover",
            {"entity_id": entity_id},
            blocking=False,
        )

        # Wait for movement to complete
        await asyncio.sleep(2)
        for _ in range(60):  # Max 60 seconds
            state = hass.states.get(entity_id)
            if state and not state.attributes.get("is_closing"):
                break
            await asyncio.sleep(1)

        _LOGGER.info("Reached closed position")
        await asyncio.sleep(2)

        # Step 5: Read total_steps
        _LOGGER.info("Step 5: Reading total_steps attribute (0x1002)")
        result = await cluster.read_attributes(
            [UBISYS_ATTR_TOTAL_STEPS],
            manufacturer=UBISYS_MANUFACTURER_CODE,
        )

        total_steps = result[0].get(UBISYS_ATTR_TOTAL_STEPS)
        if total_steps is None:
            raise Exception("Failed to read total_steps attribute")

        _LOGGER.info("Total steps: %d", total_steps)

        # Step 6: For venetian blinds, also read tilt transition steps
        tilt_steps = None
        if shade_type in ["venetian", "exterior_venetian"]:
            _LOGGER.info("Step 6: Reading lift_to_tilt_transition_steps (0x1001)")
            result = await cluster.read_attributes(
                [UBISYS_ATTR_LIFT_TO_TILT_TRANSITION_STEPS],
                manufacturer=UBISYS_MANUFACTURER_CODE,
            )

            tilt_steps = result[0].get(UBISYS_ATTR_LIFT_TO_TILT_TRANSITION_STEPS)
            if tilt_steps is not None:
                _LOGGER.info("Tilt transition steps: %d", tilt_steps)

        # Step 7: Send completion notification
        notification_data = {
            "title": "Calibration Complete",
            "message": f"Ubisys device {entity_id} has been calibrated successfully.\n\n"
            f"Shade type: {shade_type}\n"
            f"Total steps: {total_steps}",
        }

        if tilt_steps is not None:
            notification_data["message"] += f"\nTilt transition steps: {tilt_steps}"

        hass.bus.async_fire(
            "ubisys_calibration_complete",
            {
                "entity_id": entity_id,
                "shade_type": shade_type,
                "total_steps": total_steps,
                "tilt_steps": tilt_steps,
            },
        )

        await hass.services.async_call(
            "persistent_notification",
            "create",
            notification_data,
        )

        _LOGGER.info("Calibration completed successfully")

    except Exception as e:
        error_msg = f"Calibration failed: {str(e)}"
        _LOGGER.error(error_msg)

        # Send error notification
        hass.bus.async_fire(
            "ubisys_calibration_failed",
            {
                "entity_id": entity_id,
                "error": str(e),
            },
        )

        await hass.services.async_call(
            "persistent_notification",
            "create",
            {
                "title": "Calibration Failed",
                "message": f"Failed to calibrate {entity_id}:\n\n{str(e)}",
            },
        )


# Main execution
if validate_inputs():
    # Schedule the async calibration
    hass.async_create_task(calibrate())
else:
    _LOGGER.error("Input validation failed")
