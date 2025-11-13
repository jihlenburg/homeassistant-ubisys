from __future__ import annotations

from typing import Any, Callable

def async_dispatcher_connect(hass: Any, signal: str, target: Callable[..., Any]) -> Callable[[], None]: ...

