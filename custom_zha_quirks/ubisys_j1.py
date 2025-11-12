"""Ubisys J1 Window Covering Controller Quirk.

This quirk extends the WindowCovering cluster with Ubisys manufacturer-specific
attributes for proper calibration and control of window covering devices.

Manufacturer: Ubisys Technologies GmbH
Model: J1
Device Type: Window Covering Controller (0x0202)
Manufacturer Code: 0x10F2

Endpoints:
    1: Configuration and diagnostics (Basic, Identify, Groups, Scenes, OnOff, LevelControl)
    2: Window covering control (Basic, Identify, Groups, Scenes, WindowCovering)

Manufacturer-specific attributes (cluster 0x0102, endpoint 2, mfg code 0x10F2):
    CRITICAL FIX (v1.2.0): Corrected attribute IDs per Ubisys J1 Technical Reference Manual

    - 0x0000: window_covering_type (uint8) - Window covering operational mode
        0 = Roller shade
        4 = Vertical blind
        8 = Venetian blind
        (Previously incorrectly mapped to 0x1000)

    - 0x1000: turnaround_guard_time (uint16) - Time delay between direction reversals
        (Do NOT write during calibration - was being overwritten by mistake!)

    - 0x1001: lift_to_tilt_transition_steps (uint16) - Steps required for tilt transition
    - 0x1002: total_steps (uint16) - Total motor steps from fully open to fully closed
    - 0x1003: lift_to_tilt_transition_steps2 (uint16) - Second direction (bidirectional)
    - 0x1004: total_steps2 (uint16) - Second direction total steps
    - 0x1005: additional_steps (uint16) - Additional steps for overtravel
    - 0x1006: inactive_power_threshold (uint16) - Power threshold for stall detection
    - 0x1007: startup_steps (uint16) - Steps to run on startup

Usage:
    These manufacturer attributes enable precise calibration of the window covering
    motor and support for different shade types including those with tilt functionality.
    The quirk automatically injects the manufacturer code when reading or writing
    these attributes, simplifying integration development.

Compatibility:
    - Home Assistant ZHA integration
    - Compatible with both V1 (CustomDevice) and V2 (QuirkBuilder) registration
"""

from __future__ import annotations

import logging
from typing import Any, Final, Optional

from zigpy.quirks import CustomCluster, CustomDevice
from zigpy.quirks.v2 import QuirkBuilder
from zigpy.zcl import foundation
from zigpy.zcl.clusters.closures import WindowCovering
from zigpy.zcl.foundation import ZCLAttributeDef

from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)

_LOGGER = logging.getLogger(__name__)

# Ubisys manufacturer code
UBISYS_MANUFACTURER_CODE: Final[int] = 0x10F2

# Ubisys manufacturer-specific attribute IDs
# CRITICAL FIX (v1.2.0): Corrected per Ubisys J1 Technical Reference Manual
UBISYS_ATTR_WINDOW_COVERING_TYPE: Final[int] = 0x0000  # Correct attribute for window covering type
UBISYS_ATTR_TURNAROUND_GUARD_TIME: Final[int] = 0x1000  # Guard time (was incorrectly used for type!)
UBISYS_ATTR_LIFT_TO_TILT_TRANSITION_STEPS: Final[int] = 0x1001
UBISYS_ATTR_TOTAL_STEPS: Final[int] = 0x1002

# Additional attributes from manual (available for future use)
UBISYS_ATTR_LIFT_TO_TILT_TRANSITION_STEPS2: Final[int] = 0x1003
UBISYS_ATTR_TOTAL_STEPS2: Final[int] = 0x1004
UBISYS_ATTR_ADDITIONAL_STEPS: Final[int] = 0x1005
UBISYS_ATTR_INACTIVE_POWER_THRESHOLD: Final[int] = 0x1006
UBISYS_ATTR_STARTUP_STEPS: Final[int] = 0x1007

# Backward compatibility (DEPRECATED)
UBISYS_ATTR_CONFIGURED_MODE: Final[int] = UBISYS_ATTR_WINDOW_COVERING_TYPE


class UbisysWindowCovering(CustomCluster, WindowCovering):
    """Ubisys Window Covering cluster with manufacturer-specific attributes.

    This cluster extends the standard WindowCovering cluster (0x0102) with
    Ubisys manufacturer-specific attributes that enable advanced calibration
    and configuration features for window covering devices.

    The cluster automatically injects the Ubisys manufacturer code (0x10F2)
    when reading or writing manufacturer-specific attributes, eliminating
    the need for integrations to manually specify it.
    """

    cluster_id = WindowCovering.cluster_id

    # Manufacturer-specific attributes
    # CRITICAL FIX (v1.2.0): Updated attribute IDs per technical manual
    manufacturer_attributes = {
        UBISYS_ATTR_WINDOW_COVERING_TYPE: ZCLAttributeDef(
            id=UBISYS_ATTR_WINDOW_COVERING_TYPE,
            name="window_covering_type",
            type=foundation.DATA_TYPES.uint8,
            is_manufacturer_specific=True,
        ),
        UBISYS_ATTR_TURNAROUND_GUARD_TIME: ZCLAttributeDef(
            id=UBISYS_ATTR_TURNAROUND_GUARD_TIME,
            name="turnaround_guard_time",
            type=foundation.DATA_TYPES.uint16,
            is_manufacturer_specific=True,
        ),
        UBISYS_ATTR_LIFT_TO_TILT_TRANSITION_STEPS: ZCLAttributeDef(
            id=UBISYS_ATTR_LIFT_TO_TILT_TRANSITION_STEPS,
            name="lift_to_tilt_transition_steps",
            type=foundation.DATA_TYPES.uint16,
            is_manufacturer_specific=True,
        ),
        UBISYS_ATTR_TOTAL_STEPS: ZCLAttributeDef(
            id=UBISYS_ATTR_TOTAL_STEPS,
            name="total_steps",
            type=foundation.DATA_TYPES.uint16,
            is_manufacturer_specific=True,
        ),
        # Additional attributes from manual (exposed but not yet used by integration)
        UBISYS_ATTR_LIFT_TO_TILT_TRANSITION_STEPS2: ZCLAttributeDef(
            id=UBISYS_ATTR_LIFT_TO_TILT_TRANSITION_STEPS2,
            name="lift_to_tilt_transition_steps2",
            type=foundation.DATA_TYPES.uint16,
            is_manufacturer_specific=True,
        ),
        UBISYS_ATTR_TOTAL_STEPS2: ZCLAttributeDef(
            id=UBISYS_ATTR_TOTAL_STEPS2,
            name="total_steps2",
            type=foundation.DATA_TYPES.uint16,
            is_manufacturer_specific=True,
        ),
        UBISYS_ATTR_ADDITIONAL_STEPS: ZCLAttributeDef(
            id=UBISYS_ATTR_ADDITIONAL_STEPS,
            name="additional_steps",
            type=foundation.DATA_TYPES.uint16,
            is_manufacturer_specific=True,
        ),
        UBISYS_ATTR_INACTIVE_POWER_THRESHOLD: ZCLAttributeDef(
            id=UBISYS_ATTR_INACTIVE_POWER_THRESHOLD,
            name="inactive_power_threshold",
            type=foundation.DATA_TYPES.uint16,
            is_manufacturer_specific=True,
        ),
        UBISYS_ATTR_STARTUP_STEPS: ZCLAttributeDef(
            id=UBISYS_ATTR_STARTUP_STEPS,
            name="startup_steps",
            type=foundation.DATA_TYPES.uint16,
            is_manufacturer_specific=True,
        ),
    }

    # Merge with base WindowCovering attributes
    attributes = {**WindowCovering.attributes, **manufacturer_attributes}

    async def read_attributes(
        self,
        attributes: list[str | int],
        allow_cache: bool = False,
        only_cache: bool = False,
        manufacturer: Optional[int] = None,
    ) -> dict[int | str, Any]:
        """Read attributes with automatic manufacturer code injection.

        For Ubisys manufacturer-specific attributes, automatically inject
        the manufacturer code if not provided. This simplifies access to
        manufacturer attributes from both the quirk and external integrations.

        Args:
            attributes: List of attribute names or IDs to read
            allow_cache: Whether to allow cached values
            only_cache: Whether to only use cached values
            manufacturer: Manufacturer code (auto-injected for Ubisys attributes)

        Returns:
            Dictionary mapping attribute IDs/names to values
        """
        # Convert attribute names to IDs
        attr_ids = []
        for attr in attributes:
            if isinstance(attr, str):
                # Convert name to ID by searching attributes dict
                for attr_id, attr_def in self.attributes.items():
                    if hasattr(attr_def, "name") and attr_def.name == attr:
                        attr_ids.append(attr_id)
                        break
            else:
                attr_ids.append(attr)

        # Check if any requested attributes are manufacturer-specific
        needs_mfg_code = any(
            attr_id in self.manufacturer_attributes for attr_id in attr_ids
        )

        # Auto-inject Ubisys manufacturer code if needed
        if needs_mfg_code and manufacturer is None:
            manufacturer = UBISYS_MANUFACTURER_CODE
            _LOGGER.debug(
                "Auto-injecting Ubisys manufacturer code (0x%04X) for read_attributes",
                UBISYS_MANUFACTURER_CODE,
            )

        return await super().read_attributes(
            attributes, allow_cache, only_cache, manufacturer
        )

    async def write_attributes(
        self,
        attributes: dict[str | int, Any],
        manufacturer: Optional[int] = None,
    ) -> list[foundation.WriteAttributesResponse]:
        """Write attributes with automatic manufacturer code injection.

        For Ubisys manufacturer-specific attributes, automatically inject
        the manufacturer code if not provided.

        Args:
            attributes: Dictionary mapping attribute names/IDs to values
            manufacturer: Manufacturer code (auto-injected for Ubisys attributes)

        Returns:
            List of write attribute responses
        """
        # Convert attribute names to IDs
        attr_ids = []
        for attr in attributes.keys():
            if isinstance(attr, str):
                # Convert name to ID by searching attributes dict
                for attr_id, attr_def in self.attributes.items():
                    if hasattr(attr_def, "name") and attr_def.name == attr:
                        attr_ids.append(attr_id)
                        break
            else:
                attr_ids.append(attr)

        # Check if any attributes being written are manufacturer-specific
        needs_mfg_code = any(
            attr_id in self.manufacturer_attributes for attr_id in attr_ids
        )

        # Auto-inject Ubisys manufacturer code if needed
        if needs_mfg_code and manufacturer is None:
            manufacturer = UBISYS_MANUFACTURER_CODE
            _LOGGER.debug(
                "Auto-injecting Ubisys manufacturer code (0x%04X) for write_attributes",
                UBISYS_MANUFACTURER_CODE,
            )

        return await super().write_attributes(attributes, manufacturer)


class UbisysJ1(CustomDevice):
    """Ubisys J1 Window Covering Controller custom device.

    This class provides V1 quirk compatibility for systems that don't support
    QuirkBuilder V2. It will be automatically used if V2 is not available.
    """

    signature = {
        MODELS_INFO: [("ubisys", "J1")],
        ENDPOINTS: {
            # Endpoint 1: Configuration and diagnostics
            1: {
                PROFILE_ID: 0x0104,  # Zigbee Home Automation
                DEVICE_TYPE: 0x0104,  # Dimmer Switch
                INPUT_CLUSTERS: [
                    0x0000,  # Basic
                    0x0003,  # Identify
                    0x0004,  # Groups
                    0x0005,  # Scenes
                    0x0006,  # On/Off
                    0x0008,  # Level Control
                ],
                OUTPUT_CLUSTERS: [
                    0x0019,  # OTA Upgrade
                ],
            },
            # Endpoint 2: Window covering control
            2: {
                PROFILE_ID: 0x0104,  # Zigbee Home Automation
                DEVICE_TYPE: 0x0202,  # Window Covering
                INPUT_CLUSTERS: [
                    0x0000,  # Basic
                    0x0003,  # Identify
                    0x0004,  # Groups
                    0x0005,  # Scenes
                    0x0102,  # Window Covering
                ],
                OUTPUT_CLUSTERS: [],
            },
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: 0x0104,
                DEVICE_TYPE: 0x0104,
                INPUT_CLUSTERS: [
                    0x0000,
                    0x0003,
                    0x0004,
                    0x0005,
                    0x0006,
                    0x0008,
                ],
                OUTPUT_CLUSTERS: [
                    0x0019,
                ],
            },
            2: {
                PROFILE_ID: 0x0104,
                DEVICE_TYPE: 0x0202,
                INPUT_CLUSTERS: [
                    0x0000,
                    0x0003,
                    0x0004,
                    0x0005,
                    UbisysWindowCovering,  # Replace with enhanced cluster
                ],
                OUTPUT_CLUSTERS: [],
            },
        }
    }


# V2 QuirkBuilder registration (preferred for modern Home Assistant)
# This will be used if the system supports QuirkBuilder V2 (HA 2023.3+)
(
    QuirkBuilder("ubisys", "J1")
    .replaces(UbisysWindowCovering)
    .add_to_registry()
)

_LOGGER.info("Registered Ubisys J1 quirk")
