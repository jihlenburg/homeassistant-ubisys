from __future__ import annotations

from typing import Any, Callable, Iterable, Protocol

AddEntitiesCallback = Callable[[Iterable[Any], bool], None]
