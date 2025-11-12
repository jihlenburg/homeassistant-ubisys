"""Ubisys S1/S1-R Power Switch Quirk.

This quirk exposes the Ubisys manufacturer-specific DeviceSetup cluster for
proper physical input configuration on S1/S1-R power switches.

Manufacturer: Ubisys Technologies GmbH
Model: S1 (flush-mount), S1-R (DIN rail variant)
Device Type: On/Off Plug-in Unit (0x010A)
Manufacturer Code: 0x10F2

Endpoints (S1):
    1: On/Off control (Basic, Identify, Groups, Scenes, OnOff)
    2: Primary input (OnOff client, LevelControl client)
    3: Metering (Metering, Electrical Measurement)
    232: Device Management (DeviceSetup)
    242: Green Power

Endpoints (S1-R):
    1: On/Off control (Basic, Identify, Groups, Scenes, OnOff)
    2: Primary input (OnOff client, LevelControl client)
    3: Secondary input (OnOff client, LevelControl client)
    4: Metering (Metering, Electrical Measurement)
    232: Device Management (DeviceSetup)
    242: Green Power

Key Difference:
    S1 has 1 physical input and metering on endpoint 3
    S1-R has 2 physical inputs and metering on endpoint 4

Manufacturer-specific cluster:

1. DeviceSetup cluster (0xFC00, endpoint 232, mfg code 0x10F2):
   - 0x0000: input_configurations (CharacterString) - Physical input config
   - 0x0001: input_actions (CharacterString) - Input behavior config

   These attributes enable configuration of physical switch inputs:
   - Enable/disable inputs
   - Invert signal (normally open vs. normally closed)
   - Configure input actions (toggle, on/off, dimming, scenes)

Standard Clusters (ZHA Native Support):
    - On/Off (0x0006): ZHA creates switch entity automatically
    - Metering (0x0702): Power and energy tracking
    - Electrical Measurement (0x0B04): Voltage, current, power measurements
    - Groups (0x0004): Group membership
    - Scenes (0x0005): Scene storage and recall

Usage:
    This quirk enables:
    - Basic on/off control (handled by ZHA natively via switch entity)
    - Power and energy monitoring (handled by ZHA natively via sensor entities)
    - Physical switch configuration (via custom integration service)

    The custom Ubisys integration provides a service to configure input
    behaviors using the DeviceSetup cluster exposed by this quirk.

Compatibility:
    - Home Assistant ZHA integration
    - Uses QuirkBuilder V2 for modern HA versions (2023.3+)
    - Tested with HA 2024.1+

Debugging:
    Enable debug logging in configuration.yaml:
        logger:
          logs:
            custom_zha_quirks.ubisys_s1: debug

    This will log all cluster operations including manufacturer code injection.

Input Configuration Examples:
    S1 Default (rocker switch):
        Input 0: Toggle on released->pressed
        Input 0: Toggle on any->released

    S1-R Default (push buttons):
        Input 0: Toggle on press
        Input 1: Toggle on press

See Also:
    - Ubisys S1 Technical Reference Manual
    - custom_components/ubisys/s1_config.py (configuration service)
"""

from __future__ import annotations

import logging

from zigpy.quirks.v2 import QuirkBuilder

# Import the shared DeviceSetup cluster
# This cluster is identical for J1, D1, and S1 - all use DeviceSetup 0xFC00
from custom_zha_quirks.ubisys_common import UbisysDeviceSetup

_LOGGER = logging.getLogger(__name__)

# ============================================================================
# S1 QUIRK REGISTRATION
# ============================================================================
# The S1 is simpler than D1 - it only needs the DeviceSetup cluster.
# All other functionality (on/off, metering) is handled natively by ZHA.

# S1 (flush-mount, 1 input)
# Adds DeviceSetup cluster at endpoint 232 for input configuration
(
    QuirkBuilder("ubisys", "S1")
    .adds(UbisysDeviceSetup)
    .add_to_registry()
)

# S1-R (DIN rail, 2 inputs)
# Same as S1, just different endpoint layout (metering on EP4 instead of EP3)
(
    QuirkBuilder("ubisys", "S1-R")
    .adds(UbisysDeviceSetup)
    .add_to_registry()
)

_LOGGER.info(
    "Registered Ubisys S1/S1-R power switch quirks with DeviceSetup cluster for input configuration"
)
