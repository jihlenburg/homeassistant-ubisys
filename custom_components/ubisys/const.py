"""Constants for the Ubisys integration."""

from enum import StrEnum
from typing import Final

from homeassistant.components.cover import CoverEntityFeature

DOMAIN: Final = "ubisys"

# Configuration and options
CONF_DEVICE_IEEE: Final = "device_ieee"
CONF_DEVICE_ID: Final = "device_id"
CONF_ZHA_CONFIG_ENTRY_ID: Final = "zha_config_entry_id"
CONF_ZHA_ENTITY_ID: Final = "zha_entity_id"
CONF_SHADE_TYPE: Final = "shade_type"

# Device identification
MANUFACTURER: Final = "ubisys"
SUPPORTED_MODELS: Final = ["J1"]

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

# Ubisys manufacturer-specific attributes
UBISYS_MANUFACTURER_CODE: Final = 0x10F2
UBISYS_ATTR_CONFIGURED_MODE: Final = 0x1000
UBISYS_ATTR_LIFT_TO_TILT_TRANSITION_STEPS: Final = 0x1001
UBISYS_ATTR_TOTAL_STEPS: Final = 0x1002

# Zigbee cluster IDs
CLUSTER_WINDOW_COVERING: Final = 0x0102

# Zigbee attribute IDs (standard)
ATTR_WINDOW_COVERING_TYPE: Final = 0x0000
ATTR_CURRENT_POSITION_LIFT: Final = 0x0008
ATTR_CURRENT_POSITION_TILT: Final = 0x0009

# Service names
SERVICE_CALIBRATE: Final = "calibrate_j1"

# Service parameters
ATTR_ENTITY_ID: Final = "entity_id"

# Events
EVENT_UBISYS_CALIBRATION_COMPLETE: Final = "ubisys_calibration_complete"
EVENT_UBISYS_CALIBRATION_FAILED: Final = "ubisys_calibration_failed"

# Shade type to tilt steps mapping
# These values determine how many motor steps are used for tilt operations
SHADE_TYPE_TILT_STEPS: Final = {
    SHADE_TYPE_ROLLER: 0,  # No tilt
    SHADE_TYPE_CELLULAR: 0,  # No tilt
    SHADE_TYPE_VERTICAL: 0,  # No tilt
    SHADE_TYPE_VENETIAN: 100,  # Typical venetian blind tilt range
    SHADE_TYPE_EXTERIOR_VENETIAN: 100,  # Typical exterior venetian blind tilt range
}
