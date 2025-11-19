"""Home Assistant typing helpers and shims.

Provides typed aliases for decorators that come from third-party packages
without type information when running mypy with strict settings.
"""

from __future__ import annotations

from typing import Any, Callable, Mapping, Protocol, TypeVar, cast

F = TypeVar("F", bound=Callable[..., Any])


try:
    from homeassistant.core import callback as _ha_callback

    # Provide a typed alias for HA's callback decorator. When mypy runs with
    # ignore_missing_imports, the imported decorator is typed as Any; casting
    # gives it a precise decorator type and avoids "untyped decorator" errors.
    callback = cast(Callable[[F], F], _ha_callback)
except Exception:
    # Fallback no-op decorator for type checking without HA installed.
    def callback(func: F) -> F:
        return func


class HAEvent(Protocol):
    """Minimal Home Assistant Event protocol for typing callbacks.

    Only includes attributes accessed by this integration so we avoid relying
    on third-party stubs while keeping strict typing with mypy.
    """

    data: Mapping[str, object]
