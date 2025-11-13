"""Shared Ubisys ZHA Quirk Components.

This module contains common components used across multiple Ubisys device quirks:
- DeviceSetup cluster (0xFC00) - Used by D1, S1, and J1 for input configuration
- Common constants (manufacturer code, cluster IDs)

Architecture Note:
    This module follows the DRY (Don't Repeat Yourself) principle by extracting
    shared cluster definitions used by multiple device types. The DeviceSetup
    cluster is functionally identical across all Ubisys devices - only the
    endpoint number varies.

Usage:
    Import shared components in device-specific quirks:
    ```python
    from custom_zha_quirks.ubisys_common import (
        UBISYS_MANUFACTURER_CODE,
        UBISYS_DEVICE_SETUP_CLUSTER_ID,
        UBISYS_ATTR_INPUT_CONFIGS,
        UBISYS_ATTR_INPUT_ACTIONS,
        UbisysDeviceSetup,
    )
    ```

Compatibility:
    - Home Assistant ZHA integration
    - Compatible with both V1 (CustomDevice) and V2 (QuirkBuilder) registration
    - Tested with HA 2024.1+
"""

from __future__ import annotations

import logging
from typing import Any, Final, Optional, cast

from zigpy.quirks import CustomCluster
from zigpy.types import CharacterString
from zigpy.zcl import foundation
from zigpy.zcl.foundation import ZCLAttributeDef

_LOGGER = logging.getLogger(__name__)

# ============================================================================
# COMMON CONSTANTS
# ============================================================================
# Constants shared across all Ubisys device quirks

# Ubisys manufacturer code (required for all manufacturer-specific operations)
UBISYS_MANUFACTURER_CODE: Final[int] = 0x10F2

# DeviceSetup cluster ID (manufacturer-specific, common to all Ubisys devices)
UBISYS_DEVICE_SETUP_CLUSTER_ID: Final[int] = 0xFC00

# DeviceSetup cluster attribute IDs
UBISYS_ATTR_INPUT_CONFIGS: Final[int] = 0x0000  # Input configurations
UBISYS_ATTR_INPUT_ACTIONS: Final[int] = 0x0001  # Input actions (micro-code)


# ============================================================================
# SHARED CLUSTER DEFINITIONS
# ============================================================================


class UbisysDeviceSetup(CustomCluster):
    """Ubisys DeviceSetup cluster (0xFC00) for physical input configuration.

    This is a manufacturer-specific cluster shared by all Ubisys devices that
    support physical input configuration (J1, D1, S1). It allows configuration
    of physical switch inputs (e.g., wall switches connected to the device).

    Cluster ID: 0xFC00
    Manufacturer Code: 0x10F2 (required for all operations)
    Endpoint: 232 (standard across all Ubisys devices)

    Attributes:
        - input_configurations (0x0000): Configure input types
          (momentary/stationary/decoupled/enable/disable/invert)
        - input_actions (0x0001): Configure input behaviors (micro-code format)

    Usage:
        This cluster is used to configure how physical switches interact with
        the device. For example:
        - Momentary switches (push buttons) vs toggle switches
        - Decoupled mode (physical switch controls Zigbee bindings, not local output)
        - Custom actions triggered by button presses

    Devices Using This Cluster:
        - J1/J1-R (window covering): 2 physical inputs
        - D1/D1-R (dimmer): 2 physical inputs
        - S1 (power switch): 1 physical input
        - S1-R (power switch): 2 physical inputs

    Important:
        ALL operations on this cluster require the Ubisys manufacturer code (0x10F2).
        This cluster automatically injects it for all read/write operations.

    Why This is Shared:
        The DeviceSetup cluster is functionally identical across all Ubisys devices.
        The only difference is the endpoint number (always 232) and the number of
        physical inputs available (device-dependent). By sharing this cluster
        definition, we:
        - Avoid code duplication across device quirks
        - Ensure consistent behavior across all device types
        - Simplify maintenance (fix bugs once, all devices benefit)

    See Also:
        - Ubisys Technical Reference Manuals (all models)
        - custom_components/ubisys/d1_config.py (uses this for D1 input config)
        - custom_components/ubisys/s1_config.py (uses this for S1 input config)
        - custom_components/ubisys/input_config.py (generates micro-code)
    """

    cluster_id = UBISYS_DEVICE_SETUP_CLUSTER_ID
    ep_attribute = "ubisys_device_setup"

    # Define manufacturer-specific attributes
    attributes = {
        UBISYS_ATTR_INPUT_CONFIGS: ZCLAttributeDef(
            id=UBISYS_ATTR_INPUT_CONFIGS,
            name="input_configurations",
            type=CharacterString,
            is_manufacturer_specific=True,
        ),
        UBISYS_ATTR_INPUT_ACTIONS: ZCLAttributeDef(
            id=UBISYS_ATTR_INPUT_ACTIONS,
            name="input_actions",
            type=CharacterString,
            is_manufacturer_specific=True,
        ),
    }

    async def read_attributes(
        self,
        attributes: list[str | int],
        allow_cache: bool = False,
        only_cache: bool = False,
        manufacturer: Optional[int] = None,
    ) -> dict[int | str, Any]:
        """Read DeviceSetup attributes with automatic manufacturer code injection.

        ALL operations on this cluster require manufacturer code 0x10F2.
        This method automatically injects it.

        Args:
            attributes: List of attribute names or IDs
            allow_cache: Whether to allow cached values
            only_cache: Whether to only use cached values
            manufacturer: Manufacturer code (auto-injected as 0x10F2)

        Returns:
            Dictionary mapping attribute IDs/names to values

        Logging:
            DEBUG: Logs manufacturer code injection and all operations

        Example:
            # From integration code:
            >>> cluster = await get_device_setup_cluster(hass, device_ieee)
            >>> result = await cluster.read_attributes([0x0001])  # InputActions
            # Manufacturer code 0x10F2 automatically injected
        """
        # ALWAYS inject Ubisys manufacturer code for this cluster
        if manufacturer is None:
            manufacturer = UBISYS_MANUFACTURER_CODE
            _LOGGER.debug(
                "DeviceSetup: Auto-injecting manufacturer code 0x%04X for read",
                UBISYS_MANUFACTURER_CODE,
            )

        _LOGGER.debug(
            "DeviceSetup: Reading attributes %s",
            attributes,
        )

        result = cast(
            dict[int | str, Any],
            await super().read_attributes(
                attributes, allow_cache, only_cache, manufacturer
            ),
        )

        _LOGGER.debug("DeviceSetup: Read result: %s", result)
        return result

    async def write_attributes(
        self,
        attributes: dict[str | int, Any],
        manufacturer: Optional[int] = None,
    ) -> list[foundation.WriteAttributesResponse]:
        """Write DeviceSetup attributes with automatic manufacturer code injection.

        ALL operations on this cluster require manufacturer code 0x10F2.
        This method automatically injects it.

        Args:
            attributes: Dictionary mapping attribute names/IDs to values
            manufacturer: Manufacturer code (auto-injected as 0x10F2)

        Returns:
            List of write attribute responses

        Logging:
            DEBUG: Logs manufacturer code injection and all operations
            WARNING: Logs if write fails

        Example:
            # Write InputActions micro-code
            >>> cluster = await get_device_setup_cluster(hass, device_ieee)
            >>> micro_code = bytes([0x01, 0x02, ...])  # Generated by input_config.py
            >>> await cluster.write_attributes({0x0001: micro_code})
            # Manufacturer code 0x10F2 automatically injected
        """
        # ALWAYS inject Ubisys manufacturer code for this cluster
        if manufacturer is None:
            manufacturer = UBISYS_MANUFACTURER_CODE
            _LOGGER.debug(
                "DeviceSetup: Auto-injecting manufacturer code 0x%04X for write",
                UBISYS_MANUFACTURER_CODE,
            )

        _LOGGER.debug(
            "DeviceSetup: Writing attributes %s",
            attributes,
        )

        result = cast(
            list[foundation.WriteAttributesResponse],
            await super().write_attributes(attributes, manufacturer),
        )

        _LOGGER.debug("DeviceSetup: Write result: %s", result)
        return result


_LOGGER.debug("Loaded shared Ubisys DeviceSetup cluster definition")
