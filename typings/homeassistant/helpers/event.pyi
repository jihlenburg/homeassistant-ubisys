from __future__ import annotations

from typing import Any, Callable

def async_track_state_change_event(
    hass: Any, entity_ids: list[str], action: Callable[..., Any]
) -> Callable[[], None]: ...
