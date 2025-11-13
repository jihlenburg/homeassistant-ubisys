from __future__ import annotations

from typing import Any, Callable, Mapping, Protocol

class ConfigEntry:
    entry_id: str
    data: Mapping[str, Any]
    options: Mapping[str, Any]
    title: str
    version: int
    domain: str
    state: Any
    async def async_on_unload(self, func: Callable[[], Any]) -> None: ...
    def add_update_listener(self, cb: Callable[[Any], Any]) -> Callable[[], None]: ...

class ConfigFlow:
    VERSION: int
    async def async_set_unique_id(self, unique_id: str | None = ...) -> None: ...
    def _abort_if_unique_id_configured(self) -> None: ...
    def async_show_form(self, *, step_id: str, data_schema: Any | None = ..., errors: Mapping[str, str] | None = ...) -> Any: ...
    def async_show_menu(self, *, step_id: str, menu_options: list[str]) -> Any: ...

class OptionsFlow:
    ...

