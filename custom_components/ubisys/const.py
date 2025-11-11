"""Constants for the Ubisys integration.

This module contains ALL constants used across the integration, organized by:
1. General integration constants
2. Device model categorization
3. J1 window covering constants
4. D1 dimmer constants
5. Shared Zigbee constants
6. Service names

Architecture Note:
    Centralizing constants here prevents duplication and makes it easy to
    see all configurable values in one place. Constants are grouped by
    device type to make it clear which constants apply to which devices.
"""

from enum import StrEnum
from typing import Final

from homeassistant.components.cover import CoverEntityFeature

# ============================================================================
# GENERAL INTEGRATION CONSTANTS
# ============================================================================

DOMAIN: Final = "ubisys"
MANUFACTURER: Final = "ubisys"
UBISYS_MANUFACTURER_CODE: Final = 0x10F2

# Configuration and options (used in config entries)
CONF_DEVICE_IEEE: Final = "device_ieee"
CONF_DEVICE_ID: Final = "device_id"
CONF_ZHA_CONFIG_ENTRY_ID: Final = "zha_config_entry_id"
CONF_ZHA_ENTITY_ID: Final = "zha_entity_id"
CONF_SHADE_TYPE: Final = "shade_type"  # J1-specific
CONF_PHASE_MODE: Final = "phase_mode"  # D1-specific
CONF_BALLAST_MIN_LEVEL: Final = "ballast_min_level"  # D1-specific
CONF_BALLAST_MAX_LEVEL: Final = "ballast_max_level"  # D1-specific

# ============================================================================
# DEVICE MODEL CATEGORIZATION
# ============================================================================
# Separate device models by type for easy categorization

# Window covering controllers (support calibration)
WINDOW_COVERING_MODELS: Final = ["J1", "J1-R"]

# Universal dimmers (support phase control, ballast config)
DIMMER_MODELS: Final = ["D1", "D1-R"]

# Power switches (future)
SWITCH_MODELS: Final = ["S1", "S1-R", "S2", "S2-R"]

# All supported models
SUPPORTED_MODELS: Final = (
    WINDOW_COVERING_MODELS
    + DIMMER_MODELS
    # + SWITCH_MODELS  # Uncomment when implementing S1/S2
)

# Shade types
SHADE_TYPE_ROLLER: Final = "roller"
SHADE_TYPE_CELLULAR: Final = "cellular"
SHADE_TYPE_VERTICAL: Final = "vertical"
SHADE_TYPE_VENETIAN: Final = "venetian"
SHADE_TYPE_EXTERIOR_VENETIAN: Final = "exterior_venetian"

SHADE_TYPES: Final = [
    SHADE_TYPE_ROLLER,
    SHADE_TYPE_CELLULAR,
    SHADE_TYPE_VERTICAL,
    SHADE_TYPE_VENETIAN,
    SHADE_TYPE_EXTERIOR_VENETIAN,
]


class ShadeType(StrEnum):
    """Shade type enumeration."""

    ROLLER = SHADE_TYPE_ROLLER
    CELLULAR = SHADE_TYPE_CELLULAR
    VERTICAL = SHADE_TYPE_VERTICAL
    VENETIAN = SHADE_TYPE_VENETIAN
    EXTERIOR_VENETIAN = SHADE_TYPE_EXTERIOR_VENETIAN


# Zigbee Window Covering Types
WINDOW_COVERING_TYPE_ROLLERSHADE: Final = 0x00
WINDOW_COVERING_TYPE_VERTICAL_BLIND: Final = 0x04
WINDOW_COVERING_TYPE_VENETIAN_BLIND: Final = 0x08

# Shade type to Zigbee WindowCoveringType mapping
SHADE_TYPE_TO_WINDOW_COVERING_TYPE: Final = {
    SHADE_TYPE_ROLLER: WINDOW_COVERING_TYPE_ROLLERSHADE,
    SHADE_TYPE_CELLULAR: WINDOW_COVERING_TYPE_ROLLERSHADE,
    SHADE_TYPE_VERTICAL: WINDOW_COVERING_TYPE_VERTICAL_BLIND,
    SHADE_TYPE_VENETIAN: WINDOW_COVERING_TYPE_VENETIAN_BLIND,
    SHADE_TYPE_EXTERIOR_VENETIAN: WINDOW_COVERING_TYPE_VENETIAN_BLIND,
}

# Shade type to supported features mapping
# Position-only shades
_POSITION_ONLY_FEATURES = (
    CoverEntityFeature.OPEN
    | CoverEntityFeature.CLOSE
    | CoverEntityFeature.STOP
    | CoverEntityFeature.SET_POSITION
)

# Position + Tilt shades
_POSITION_TILT_FEATURES = (
    _POSITION_ONLY_FEATURES
    | CoverEntityFeature.OPEN_TILT
    | CoverEntityFeature.CLOSE_TILT
    | CoverEntityFeature.STOP_TILT
    | CoverEntityFeature.SET_TILT_POSITION
)

SHADE_TYPE_TO_FEATURES: Final = {
    SHADE_TYPE_ROLLER: _POSITION_ONLY_FEATURES,
    SHADE_TYPE_CELLULAR: _POSITION_ONLY_FEATURES,
    SHADE_TYPE_VERTICAL: _POSITION_ONLY_FEATURES,
    SHADE_TYPE_VENETIAN: _POSITION_TILT_FEATURES,
    SHADE_TYPE_EXTERIOR_VENETIAN: _POSITION_TILT_FEATURES,
}

# J1-specific manufacturer attributes (WindowCovering cluster extensions)
UBISYS_ATTR_CONFIGURED_MODE: Final = 0x1000              # Window covering type
UBISYS_ATTR_LIFT_TO_TILT_TRANSITION_STEPS: Final = 0x1001  # Tilt transition steps
UBISYS_ATTR_TOTAL_STEPS: Final = 0x1002                  # Total motor steps

# Window covering attribute IDs (standard ZCL)
ATTR_WINDOW_COVERING_TYPE: Final = 0x0000        # Window covering type attribute
ATTR_CURRENT_POSITION_LIFT: Final = 0x0008       # Current lift position
ATTR_CURRENT_POSITION_TILT: Final = 0x0009       # Current tilt position

# Calibration mode attribute (J1-specific manufacturer attribute)
CALIBRATION_MODE_ATTR: Final = 0x0017    # Mode attribute in WindowCovering cluster
CALIBRATION_MODE_ENTER: Final = 0x02     # Value to enter calibration mode
CALIBRATION_MODE_EXIT: Final = 0x00      # Value to exit calibration mode

# Calibration timing constants (used by calibration.py)
STALL_DETECTION_INTERVAL: Final = 0.5    # Check position every 0.5 seconds
STALL_DETECTION_TIME: Final = 3.0        # Position unchanged for 3s = stall
PER_MOVE_TIMEOUT: Final = 120            # Maximum 120s per movement
SETTLE_TIME: Final = 1.0                 # Wait 1s after stopping

# Service parameters
ATTR_ENTITY_ID: Final = "entity_id"

# Events
EVENT_UBISYS_CALIBRATION_COMPLETE: Final = "ubisys_calibration_complete"
EVENT_UBISYS_CALIBRATION_FAILED: Final = "ubisys_calibration_failed"

# Backward compatibility alias
SERVICE_CALIBRATE: Final = SERVICE_CALIBRATE_J1  # Points to deprecated name

# Shade type to tilt steps mapping
# These values determine how many motor steps are used for tilt operations
SHADE_TYPE_TILT_STEPS: Final = {
    SHADE_TYPE_ROLLER: 0,  # No tilt
    SHADE_TYPE_CELLULAR: 0,  # No tilt
    SHADE_TYPE_VERTICAL: 0,  # No tilt
    SHADE_TYPE_VENETIAN: 100,  # Typical venetian blind tilt range
    SHADE_TYPE_EXTERIOR_VENETIAN: 100,  # Typical exterior venetian blind tilt range
}

# ============================================================================
# D1 DIMMER CONSTANTS
# ============================================================================
# Universal dimmer-specific constants

# Phase control modes
# The D1 supports three dimming modes for different load types
PHASE_MODE_AUTOMATIC: Final = 0  # Auto-detect load type (default)
PHASE_MODE_FORWARD: Final = 1     # Forward phase (leading edge) - for resistive/inductive
PHASE_MODE_REVERSE: Final = 2     # Reverse phase (trailing edge) - for capacitive

# Phase mode string to value mapping
PHASE_MODES: Final = {
    "automatic": PHASE_MODE_AUTOMATIC,
    "forward": PHASE_MODE_FORWARD,
    "reverse": PHASE_MODE_REVERSE,
}

# Reverse mapping for display
PHASE_MODE_NAMES: Final = {
    PHASE_MODE_AUTOMATIC: "automatic",
    PHASE_MODE_FORWARD: "forward",
    PHASE_MODE_REVERSE: "reverse",
}

# Ballast configuration limits
# These are the valid ranges for ballast min/max level attributes
BALLAST_LEVEL_MIN: Final = 1    # Minimum valid value
BALLAST_LEVEL_MAX: Final = 254  # Maximum valid value

# Default ballast levels
BALLAST_DEFAULT_MIN_LEVEL: Final = 1    # Factory default minimum
BALLAST_DEFAULT_MAX_LEVEL: Final = 254  # Factory default maximum

# ============================================================================
# SHARED ZIGBEE CONSTANTS
# ============================================================================
# Standard Zigbee cluster IDs and attributes used by multiple devices

# Cluster IDs (standard Zigbee)
CLUSTER_BASIC: Final = 0x0000
CLUSTER_IDENTIFY: Final = 0x0003
CLUSTER_GROUPS: Final = 0x0004
CLUSTER_ON_OFF: Final = 0x0006
CLUSTER_LEVEL_CONTROL: Final = 0x0008
CLUSTER_WINDOW_COVERING: Final = 0x0102
CLUSTER_BALLAST: Final = 0x0301
CLUSTER_METERING: Final = 0x0702
CLUSTER_ELECTRICAL_MEASUREMENT: Final = 0x0B04

# Manufacturer-specific clusters (Ubisys)
CLUSTER_DEVICE_SETUP: Final = 0xFC00  # Ubisys DeviceSetup cluster

# Ballast cluster attributes (standard ZCL)
BALLAST_ATTR_MIN_LEVEL: Final = 0x0011      # Minimum light level
BALLAST_ATTR_MAX_LEVEL: Final = 0x0012      # Maximum light level
BALLAST_ATTR_PHYSICAL_MIN_LEVEL: Final = 0x0000

# DeviceSetup cluster attributes (Ubisys manufacturer-specific)
DEVICE_SETUP_ATTR_INPUT_CONFIGS: Final = 0x0000
DEVICE_SETUP_ATTR_INPUT_ACTIONS: Final = 0x0001

# Endpoint IDs for different devices
J1_WINDOW_COVERING_ENDPOINT: Final = 2  # J1 WindowCovering cluster endpoint
D1_DIMMER_ENDPOINT: Final = 4             # D1 dimmer control endpoint
D1_METERING_ENDPOINT: Final = 5           # D1 power metering endpoint

# ============================================================================
# SERVICE NAMES
# ============================================================================
# Service identifiers used by the integration

# Window covering services (J1)
SERVICE_CALIBRATE_COVER: Final = "calibrate_cover"     # New generic name
SERVICE_CALIBRATE_J1: Final = "calibrate_j1"           # Deprecated alias

# Dimmer services (D1)
SERVICE_CONFIGURE_D1_PHASE_MODE: Final = "configure_d1_phase_mode"
SERVICE_CONFIGURE_D1_BALLAST: Final = "configure_d1_ballast"
SERVICE_CONFIGURE_D1_INPUTS: Final = "configure_d1_inputs"

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================
# Utility functions that depend on constants


def get_device_type(model: str) -> str:
    """Get device type category from model string.

    Args:
        model: Device model (e.g., "J1", "D1", "S1")

    Returns:
        Device type: "window_covering", "dimmer", "switch", or "unknown"

    Example:
        >>> get_device_type("J1")
        "window_covering"
        >>> get_device_type("D1")
        "dimmer"
    """
    if model in WINDOW_COVERING_MODELS:
        return "window_covering"
    if model in DIMMER_MODELS:
        return "dimmer"
    if model in SWITCH_MODELS:
        return "switch"
    return "unknown"


def supports_calibration(model: str) -> bool:
    """Check if device model supports calibration.

    Args:
        model: Device model string

    Returns:
        True if device supports calibration (window covering devices only)

    Example:
        >>> supports_calibration("J1")
        True
        >>> supports_calibration("D1")
        False
    """
    return model in WINDOW_COVERING_MODELS
