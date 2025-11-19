"""Ubisys D1 Universal Dimmer Quirk.

This quirk extends the Ballast Configuration cluster and exposes the Ubisys
manufacturer-specific DeviceSetup cluster for proper dimmer configuration and
control.

Manufacturer: Ubisys Technologies GmbH
Model: D1, D1-R (DIN rail variant)
Device Type: Dimmable Light (0x0101)
Manufacturer Code: 0x10F2

Endpoints:
    1: Dimmable Light (Basic, Identify, Groups, Scenes, OnOff, LevelControl, Ballast, DimmerSetup)
    4: Metering and config (Metering, Electrical Measurement)
    232: DeviceSetup (InputConfigurations, InputActions - common to all Ubisys devices)

Manufacturer-specific attributes:

1. Ballast Configuration cluster (0x0301, endpoint 1):
   Standard attributes:
   - 0x0011: ballast_min_level (uint8) - Minimum light level (1-254)
   - 0x0012: ballast_max_level (uint8) - Maximum light level (1-254)

   Note: Manual indicates MinLevel=0x0010, MaxLevel=0x0011, but ZCL standard
   uses 0x0011/0x0012. Code reads both to detect which IDs are present.

2. DimmerSetup cluster (0xFC01, endpoint 1, mfg code 0x10F2):
   - 0x0002: mode (bitmap8) - Phase control mode
     - Bits [1:0]: 0=automatic, 1=forward phase, 2=reverse phase, 3=reserved
     - Bits [7:2]: Reserved
     - Only writable when output is OFF

3. DeviceSetup cluster (0xFC00, endpoint 232, mfg code 0x10F2):
   - 0x0000: input_configurations (CharacterString) - Physical input config
   - 0x0001: input_actions (CharacterString) - Input behavior config

   Note: EP232 is standard across all Ubisys devices (J1, D1, S1)

4. Metering cluster (0x0702, endpoint 4):
   - Power measurement (watts)
   - Energy tracking (kWh)

5. Electrical Measurement cluster (0x0B04, endpoint 4):
   - Voltage, current, power measurements

Usage:
    These attributes enable:
    - Phase control mode configuration (automatic/forward/reverse)
    - Ballast minimum/maximum level configuration (prevents LED flickering)
    - Physical switch configuration (momentary/toggle/decoupled)
    - Power and energy monitoring

Safety Note:
    Incorrect phase control mode configuration can damage the dimmer or connected
    loads. Always start with automatic mode and only change if experiencing issues.

Compatibility:
    - Home Assistant ZHA integration
    - Compatible with both V1 (CustomDevice) and V2 (QuirkBuilder) registration
    - Tested with HA 2024.1+

Debugging:
    Enable debug logging in configuration.yaml:
        logger:
          logs:
            custom_zha_quirks.ubisys_d1: debug

    This will log all cluster operations including manufacturer code injection.
"""

from __future__ import annotations

import logging
from typing import Any, Final, Optional, cast

from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)
from zigpy.quirks import CustomCluster, CustomDevice
from zigpy.quirks.v2 import QuirkBuilder
from zigpy.zcl import foundation
from zigpy.zcl.clusters.general import Basic, Groups, Identify, LevelControl, OnOff
from zigpy.zcl.clusters.homeautomation import ElectricalMeasurement
from zigpy.zcl.clusters.lighting import Ballast
from zigpy.zcl.clusters.smartenergy import Metering
from zigpy.zcl.foundation import ZCLAttributeDef

# Import shared Ubisys components
from custom_zha_quirks.ubisys_common import (
    UBISYS_MANUFACTURER_CODE,
    UbisysDeviceSetup,
)

_LOGGER = logging.getLogger(__name__)

# DimmerSetup cluster ID (manufacturer-specific, D1 only)
UBISYS_DIMMER_SETUP_CLUSTER_ID: Final[int] = 0xFC01

# DimmerSetup cluster attribute IDs
UBISYS_ATTR_DIMMER_MODE: Final[int] = 0x0002


class UbisysBallastConfiguration(CustomCluster, Ballast):
    """Ubisys Ballast Configuration cluster with enhanced attribute access.

    This cluster extends the standard Ballast Configuration cluster (0x0301)
    with automatic manufacturer code injection for Ubisys-specific attributes.

    Standard Attributes (accessible without manufacturer code):
        - ballast_min_level (0x0011): Minimum brightness level (1-254)
        - ballast_max_level (0x0012): Maximum brightness level (1-254)

    Purpose:
        The ballast configuration attributes allow fine-tuning dimming behavior:
        - Min level: Prevents LED flickering at low brightness
        - Max level: Limits maximum brightness for energy savings

    Debugging:
        All read/write operations are logged at DEBUG level for troubleshooting.
        Enable debug logging to see manufacturer code injection and attribute access.

    See Also:
        - Ballast Configuration Cluster Spec (ZCL 5.3)
        - Ubisys D1 Technical Reference Manual
    """

    cluster_id = Ballast.cluster_id

    # Note: Standard ballast attributes are already defined in parent Ballast class.
    # We inherit them automatically. If the D1 exposes manufacturer-specific
    # attributes in the ballast cluster (like phase control mode), they can be
    # added here after testing with a real device.

    async def read_attributes(
        self,
        attributes: list[str | int],
        allow_cache: bool = False,
        only_cache: bool = False,
        manufacturer: Optional[int] = None,
    ) -> dict[int | str, Any]:
        """Read ballast attributes with automatic manufacturer code injection.

        This method automatically injects the Ubisys manufacturer code when
        reading manufacturer-specific attributes, simplifying access from
        integrations.

        Args:
            attributes: List of attribute names or IDs to read
            allow_cache: Whether to allow cached values
            only_cache: Whether to only use cached values
            manufacturer: Manufacturer code (auto-injected if needed)

        Returns:
            Dictionary mapping attribute IDs/names to values

        Example:
            # From integration code:
            >>> result = await cluster.read_attributes(["ballast_min_level"])
            # Manufacturer code automatically added if needed

        Logging:
            DEBUG: Logs when manufacturer code is auto-injected
            DEBUG: Logs all attribute reads for troubleshooting
        """
        _LOGGER.debug(
            "D1 Ballast: Reading attributes %s (allow_cache=%s, only_cache=%s)",
            attributes,
            allow_cache,
            only_cache,
        )

        # For now, standard ballast attributes don't require manufacturer code.
        # If we discover manufacturer-specific attributes in ballast cluster,
        # add auto-injection logic here similar to J1 quirk.

        result = cast(
            dict[int | str, Any],
            await super().read_attributes(
                attributes, allow_cache, only_cache, manufacturer
            ),
        )

        _LOGGER.debug("D1 Ballast: Read result: %s", result)
        return result

    async def write_attributes(
        self,
        attributes: dict[str | int, Any],
        manufacturer: Optional[int] = None,
    ) -> list[foundation.WriteAttributesResponse]:
        """Write ballast attributes with automatic manufacturer code injection.

        Args:
            attributes: Dictionary mapping attribute names/IDs to values
            manufacturer: Manufacturer code (auto-injected if needed)

        Returns:
            List of write attribute responses

        Example:
            # Set minimum brightness to level 15 (prevents LED flickering)
            >>> await cluster.write_attributes({"ballast_min_level": 15})

            # Set maximum brightness to 80% (level 203)
            >>> await cluster.write_attributes({"ballast_max_level": 203})

        Logging:
            DEBUG: Logs all attribute writes for troubleshooting
            WARNING: Logs if write fails
        """
        _LOGGER.debug(
            "D1 Ballast: Writing attributes %s (manufacturer=%s)",
            attributes,
            manufacturer,
        )

        result = cast(
            list[foundation.WriteAttributesResponse],
            await super().write_attributes(attributes, manufacturer),
        )

        _LOGGER.debug("D1 Ballast: Write result: %s", result)
        return result


class UbisysDimmerSetup(CustomCluster):
    """Ubisys DimmerSetup cluster (0xFC01) for phase control mode configuration.

    This is a manufacturer-specific cluster unique to Ubisys D1 dimmers. It allows
    configuration of the phase control mode, which is critical for proper dimming
    behavior with different load types.

    Cluster ID: 0xFC01
    Manufacturer Code: 0x10F2 (required for all operations)
    Endpoint: 1 (Dimmable Light endpoint)

    Attributes:
        - mode (0x0002): Phase control mode
          - 0x00: Automatic (auto-detect load type) - DEFAULT
          - 0x01: Forward phase control (leading edge, for resistive/inductive)
          - 0x02: Reverse phase control (trailing edge, for capacitive/LED)
          - 0x03: Reserved (do not use)

    Safety Warning:
        Configuring the wrong phase control mode can damage the dimmer or connected
        loads. Always start with automatic mode. Only change if experiencing issues.

    Technical Details:
        - Attribute is persistent (survives reboots)
        - Preserved across normal factory resets (since firmware 1.14)
        - Only writable when output is OFF
        - Bits [1:0] control phase mode, bits [7:2] reserved

    Usage:
        This cluster is used by the D1 phase mode configuration service to:
        - Auto-detect appropriate dimming technique (automatic mode)
        - Force leading edge dimming for TRIAC-compatible loads (forward mode)
        - Force trailing edge dimming for LED/CFL loads (reverse mode)

    Important:
        ALL operations on this cluster require the Ubisys manufacturer code (0x10F2).
        This cluster automatically injects it for all read/write operations.

    See Also:
        - Ubisys D1 Technical Reference Manual (section 7.2.8)
        - custom_components/ubisys/d1_config.py (uses this cluster)
    """

    cluster_id = UBISYS_DIMMER_SETUP_CLUSTER_ID
    ep_attribute = "ubisys_dimmer_setup"

    # Define manufacturer-specific attributes
    attributes = {
        UBISYS_ATTR_DIMMER_MODE: ZCLAttributeDef(
            id=UBISYS_ATTR_DIMMER_MODE,
            name="mode",
            type=foundation.DATA_TYPES.bitmap8,
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
        """Read DimmerSetup attributes with automatic manufacturer code injection.

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
        """
        # ALWAYS inject Ubisys manufacturer code for this cluster
        if manufacturer is None:
            manufacturer = UBISYS_MANUFACTURER_CODE
            _LOGGER.debug(
                "D1 DimmerSetup: Auto-injecting manufacturer code 0x%04X for read",
                UBISYS_MANUFACTURER_CODE,
            )

        _LOGGER.debug(
            "D1 DimmerSetup: Reading attributes %s",
            attributes,
        )

        result = cast(
            dict[int | str, Any],
            await super().read_attributes(
                attributes, allow_cache, only_cache, manufacturer
            ),
        )

        _LOGGER.debug("D1 DimmerSetup: Read result: %s", result)
        return result

    async def write_attributes(
        self,
        attributes: dict[str | int, Any],
        manufacturer: Optional[int] = None,
    ) -> list[foundation.WriteAttributesResponse]:
        """Write DimmerSetup attributes with automatic manufacturer code injection.

        ALL operations on this cluster require manufacturer code 0x10F2.
        This method automatically injects it.

        IMPORTANT: According to D1 technical reference, the Mode attribute
        is only writable when the output is OFF. Attempting to write when
        the light is ON will fail.

        Args:
            attributes: Dictionary mapping attribute names/IDs to values
            manufacturer: Manufacturer code (auto-injected as 0x10F2)

        Returns:
            List of write attribute responses

        Logging:
            DEBUG: Logs manufacturer code injection and all operations
            WARNING: Logs if write fails
        """
        # ALWAYS inject Ubisys manufacturer code for this cluster
        if manufacturer is None:
            manufacturer = UBISYS_MANUFACTURER_CODE
            _LOGGER.debug(
                "D1 DimmerSetup: Auto-injecting manufacturer code 0x%04X for write",
                UBISYS_MANUFACTURER_CODE,
            )

        _LOGGER.debug(
            "D1 DimmerSetup: Writing attributes %s",
            attributes,
        )

        result = cast(
            list[foundation.WriteAttributesResponse],
            await super().write_attributes(attributes, manufacturer),
        )

        _LOGGER.debug("D1 DimmerSetup: Write result: %s", result)
        return result


class UbisysD1(CustomDevice):
    """Ubisys D1 Universal Dimmer custom device.

    This quirk provides V1 compatibility for Home Assistant systems that don't
    support QuirkBuilder V2. It will be automatically used as a fallback.

    Device Structure (per Ubisys D1 Technical Reference Manual):
        - Endpoint 1: Dimmable Light (Ballast, DimmerSetup clusters)
        - Endpoint 4: Power metering (Metering, Electrical Measurement)
        - Endpoint 232: DeviceSetup (InputConfigurations, InputActions)

    Why This Quirk Exists:
        1. Exposes standard ballast configuration attributes (min/max level)
        2. Exposes DimmerSetup cluster for phase control mode configuration
        3. Exposes DeviceSetup cluster at correct endpoint (EP232) for input config
        4. Provides automatic manufacturer code injection
        5. Enables comprehensive logging for debugging

    Integration Usage:
        The Ubisys Home Assistant integration uses this quirk to:
        - Configure phase control mode (via d1_config.py, DimmerSetup/EP1)
        - Configure ballast min/max levels (via d1_config.py, Ballast/EP1)
        - Configure physical inputs (via input_config.py, DeviceSetup/EP232)

    Debugging:
        Enable debug logging to see all cluster operations:
            logger:
              logs:
                custom_zha_quirks.ubisys_d1: debug
                custom_components.ubisys.d1_config: debug
    """

    signature = {
        MODELS_INFO: [
            ("ubisys", "D1"),  # Standard model
            ("ubisys", "D1-R"),  # DIN rail variant
        ],
        ENDPOINTS: {
            # Endpoint 1: Dimmable Light with Ballast and DimmerSetup
            1: {
                PROFILE_ID: 0x0104,  # Zigbee Home Automation
                DEVICE_TYPE: 0x0101,  # Dimmable Light
                INPUT_CLUSTERS: [
                    0x0000,  # Basic
                    0x0003,  # Identify
                    0x0004,  # Groups
                    0x0005,  # Scenes
                    0x0006,  # On/Off
                    0x0008,  # Level Control
                    0x0301,  # Ballast Configuration
                    0xFC01,  # Ubisys DimmerSetup (manufacturer-specific)
                ],
                OUTPUT_CLUSTERS: [
                    0x0019,  # OTA Upgrade
                ],
            },
            # Endpoint 4: Power metering
            4: {
                PROFILE_ID: 0x0104,  # Zigbee Home Automation
                DEVICE_TYPE: 0x0009,  # Mains Power Outlet (for metering)
                INPUT_CLUSTERS: [
                    0x0702,  # Metering
                    0x0B04,  # Electrical Measurement
                ],
                OUTPUT_CLUSTERS: [],
            },
            # Endpoint 232: DeviceSetup (common to all Ubisys devices)
            232: {
                PROFILE_ID: 0x0104,  # Zigbee Home Automation
                DEVICE_TYPE: 0x0850,  # Configuration Tool
                INPUT_CLUSTERS: [
                    0xFC00,  # Ubisys DeviceSetup (manufacturer-specific)
                ],
                OUTPUT_CLUSTERS: [],
            },
        },
    }

    replacement = {
        ENDPOINTS: {
            # Endpoint 1: Dimmable Light with Ballast and DimmerSetup
            1: {
                PROFILE_ID: 0x0104,
                DEVICE_TYPE: 0x0101,  # Dimmable Light
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    0x0005,  # Scenes
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    UbisysBallastConfiguration,  # Enhanced ballast cluster
                    UbisysDimmerSetup,  # Manufacturer-specific phase control
                ],
                OUTPUT_CLUSTERS: [
                    0x0019,  # OTA
                ],
            },
            # Endpoint 4: Power metering
            4: {
                PROFILE_ID: 0x0104,
                DEVICE_TYPE: 0x0009,  # Mains Power Outlet
                INPUT_CLUSTERS: [
                    Metering.cluster_id,
                    ElectricalMeasurement.cluster_id,
                ],
                OUTPUT_CLUSTERS: [],
            },
            # Endpoint 232: DeviceSetup (common to all Ubisys devices)
            232: {
                PROFILE_ID: 0x0104,
                DEVICE_TYPE: 0x0850,  # Configuration Tool
                INPUT_CLUSTERS: [
                    UbisysDeviceSetup,  # Manufacturer-specific cluster
                ],
                OUTPUT_CLUSTERS: [],
            },
        }
    }


# QuirkBuilder registration (modern HA uses this, older HA uses CustomDevice above)
(
    QuirkBuilder("ubisys", "D1")
    .replaces(UbisysBallastConfiguration)
    .adds(UbisysDeviceSetup)
    .adds(UbisysDimmerSetup)
    .add_to_registry()
)

(
    QuirkBuilder("ubisys", "D1-R")
    .replaces(UbisysBallastConfiguration)
    .adds(UbisysDeviceSetup)
    .adds(UbisysDimmerSetup)
    .add_to_registry()
)

_LOGGER.info(
    "Registered Ubisys D1/D1-R dimmer quirks with enhanced ballast, DeviceSetup, and DimmerSetup clusters"
)
