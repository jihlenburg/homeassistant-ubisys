"""Ubisys J1 Window Covering Controller Quirk.

This quirk extends the WindowCovering cluster with Ubisys manufacturer-specific
attributes for proper calibration and control of window covering devices.
"""

import logging
from typing import Any, Optional

from zigpy.quirks import CustomCluster, CustomDevice
from zigpy.quirks.registry import DeviceRegistry
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
UBISYS_MANUFACTURER_CODE = 0x10F2

# Ubisys manufacturer-specific attributes
UBISYS_ATTR_CONFIGURED_MODE = 0x1000
UBISYS_ATTR_LIFT_TO_TILT_TRANSITION_STEPS = 0x1001
UBISYS_ATTR_TOTAL_STEPS = 0x1002


class UbisysWindowCovering(CustomCluster, WindowCovering):
    """Ubisys Window Covering cluster with manufacturer-specific attributes."""

    cluster_id = WindowCovering.cluster_id

    # Extend manufacturer-specific attributes
    manufacturer_attributes = {
        UBISYS_ATTR_CONFIGURED_MODE: ZCLAttributeDef(
            id=UBISYS_ATTR_CONFIGURED_MODE,
            name="configured_mode",
            type=0x20,  # uint8
            is_manufacturer_specific=True,
        ),
        UBISYS_ATTR_LIFT_TO_TILT_TRANSITION_STEPS: ZCLAttributeDef(
            id=UBISYS_ATTR_LIFT_TO_TILT_TRANSITION_STEPS,
            name="lift_to_tilt_transition_steps",
            type=0x21,  # uint16
            is_manufacturer_specific=True,
        ),
        UBISYS_ATTR_TOTAL_STEPS: ZCLAttributeDef(
            id=UBISYS_ATTR_TOTAL_STEPS,
            name="total_steps",
            type=0x21,  # uint16
            is_manufacturer_specific=True,
        ),
    }

    # Merge with base attributes
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
        the manufacturer code if not provided.
        """
        # Check if any requested attributes are manufacturer-specific
        attr_ids = []
        for attr in attributes:
            if isinstance(attr, str):
                # Convert name to ID
                for attr_id, attr_def in self.attributes.items():
                    if attr_def.name == attr:
                        attr_ids.append(attr_id)
                        break
            else:
                attr_ids.append(attr)

        # If any attribute is manufacturer-specific and no manufacturer code provided,
        # inject Ubisys manufacturer code
        needs_mfg_code = any(
            attr_id in self.manufacturer_attributes for attr_id in attr_ids
        )

        if needs_mfg_code and manufacturer is None:
            manufacturer = UBISYS_MANUFACTURER_CODE
            _LOGGER.debug(
                "Injecting Ubisys manufacturer code (0x%04X) for read_attributes",
                UBISYS_MANUFACTURER_CODE,
            )

        return await super().read_attributes(
            attributes, allow_cache, only_cache, manufacturer
        )

    async def write_attributes(
        self,
        attributes: dict[str | int, Any],
        manufacturer: Optional[int] = None,
    ) -> list[Any]:
        """Write attributes with automatic manufacturer code injection.

        For Ubisys manufacturer-specific attributes, automatically inject
        the manufacturer code if not provided.
        """
        # Check if any attributes being written are manufacturer-specific
        attr_ids = []
        for attr in attributes.keys():
            if isinstance(attr, str):
                # Convert name to ID
                for attr_id, attr_def in self.attributes.items():
                    if attr_def.name == attr:
                        attr_ids.append(attr_id)
                        break
            else:
                attr_ids.append(attr)

        needs_mfg_code = any(
            attr_id in self.manufacturer_attributes for attr_id in attr_ids
        )

        if needs_mfg_code and manufacturer is None:
            manufacturer = UBISYS_MANUFACTURER_CODE
            _LOGGER.debug(
                "Injecting Ubisys manufacturer code (0x%04X) for write_attributes",
                UBISYS_MANUFACTURER_CODE,
            )

        return await super().write_attributes(attributes, manufacturer)


class UbisysJ1(CustomDevice):
    """Ubisys J1 Window Covering Controller custom device."""

    signature = {
        MODELS_INFO: [("ubisys", "J1")],
        ENDPOINTS: {
            # Endpoint 1: Configuration and diagnostics
            1: {
                PROFILE_ID: 0x0104,
                DEVICE_TYPE: 0x0104,
                INPUT_CLUSTERS: [0x0000, 0x0003, 0x0004, 0x0005, 0x0006, 0x0008],
                OUTPUT_CLUSTERS: [0x0019],
            },
            # Endpoint 2: Window covering control
            2: {
                PROFILE_ID: 0x0104,
                DEVICE_TYPE: 0x0202,  # Window covering device
                INPUT_CLUSTERS: [0x0000, 0x0003, 0x0004, 0x0005, 0x0102],
                OUTPUT_CLUSTERS: [],
            },
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: 0x0104,
                DEVICE_TYPE: 0x0104,
                INPUT_CLUSTERS: [0x0000, 0x0003, 0x0004, 0x0005, 0x0006, 0x0008],
                OUTPUT_CLUSTERS: [0x0019],
            },
            2: {
                PROFILE_ID: 0x0104,
                DEVICE_TYPE: 0x0202,
                INPUT_CLUSTERS: [
                    0x0000,
                    0x0003,
                    0x0004,
                    0x0005,
                    UbisysWindowCovering,  # Replace standard cluster with custom
                ],
                OUTPUT_CLUSTERS: [],
            },
        }
    }


# Register the quirk in the device registry
def register_quirks(registry: DeviceRegistry) -> None:
    """Register Ubisys quirks with the device registry."""
    registry.add_to_registry(UbisysJ1)
    _LOGGER.info("Registered Ubisys J1 quirk")
