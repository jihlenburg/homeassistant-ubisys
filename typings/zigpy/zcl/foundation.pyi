from __future__ import annotations

from typing import Any

class WriteAttributesResponse: ...

class _DataTypes:
    uint8: Any
    uint16: Any
    bitmap8: Any

DATA_TYPES: _DataTypes

class ZCLAttributeDef:
    def __init__(self, *, id: int, name: str, type: Any, is_manufacturer_specific: bool = ...) -> None: ...

