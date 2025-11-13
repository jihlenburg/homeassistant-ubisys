from __future__ import annotations

from homeassistant.helpers.entity import Entity

class LightEntity(Entity): ...

class ColorMode: ...

ATTR_BRIGHTNESS: str
ATTR_TRANSITION: str

