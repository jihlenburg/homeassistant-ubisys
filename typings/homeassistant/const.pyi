from __future__ import annotations

from enum import Enum

class Platform(Enum):
    COVER = "cover"
    LIGHT = "light"
    SWITCH = "switch"
    SENSOR = "sensor"
    BUTTON = "button"

EVENT_HOMEASSISTANT_STARTED: str

