from __future__ import annotations

from typing import Any

class CustomCluster:
    cluster_id: int
    attributes: dict[int, Any]
    async def read_attributes(
        self,
        attributes: list[Any],
        allow_cache: bool = ...,
        only_cache: bool = ...,
        manufacturer: int | None = ...,
    ) -> dict[Any, Any]: ...
    async def write_attributes(
        self, attributes: dict[Any, Any], manufacturer: int | None = ...
    ) -> list[Any]: ...

class CustomDevice: ...
