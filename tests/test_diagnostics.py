"""Tests for diagnostics helpers."""

from __future__ import annotations

import sys
import types
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from custom_components.ubisys import diagnostics
from custom_components.ubisys.const import DOMAIN


def _build_hass():
    return SimpleNamespace(data={})


def _install_fake_zigpy(monkeypatch):
    """Inject a lightweight zigpy.types module so diagnostics code can import it."""
    fake_pkg = types.ModuleType("zigpy")
    fake_types = types.ModuleType("zigpy.types")

    class FakeEUI64:
        @staticmethod
        def convert(value):
            return value

    fake_types.EUI64 = FakeEUI64
    fake_pkg.types = fake_types
    monkeypatch.setitem(sys.modules, "zigpy", fake_pkg)
    monkeypatch.setitem(sys.modules, "zigpy.types", fake_types)


@pytest.mark.asyncio
async def test_async_get_config_entry_diagnostics_builds_payload(monkeypatch):
    _install_fake_zigpy(monkeypatch)
    from zigpy.types import EUI64  # type: ignore[import-untyped]

    hass = _build_hass()
    entry = SimpleNamespace(
        title="Test J1",
        version=1,
        domain=DOMAIN,
        data={
            "device_id": "device-1",
            "device_ieee": "00:11:22:33:44:55:66:77",
        },
        options={"verbose": True},
    )

    # Mock device registry lookup
    device_entry = SimpleNamespace(
        id="device-1",
        name="Bedroom Shade",
        manufacturer="ubisys",
        model="J1",
        sw_version="1.0",
    )
    registry = SimpleNamespace(async_get=lambda device_id: device_entry)
    monkeypatch.setattr(
        "homeassistant.helpers.device_registry.async_get", lambda hass_: registry
    )

    # Mock diagnostics redaction to be identity so we can inspect the payload
    with patch(
        "custom_components.ubisys.diagnostics.diagnostics.async_redact_data",
        side_effect=lambda data, _: data,
    ):
        # Prepare ZHA data
        eui = EUI64.convert(entry.data["device_ieee"])
        endpoint = SimpleNamespace(
            in_clusters={0x0102: object()},
            out_clusters={0x000A: object()},
        )
        zha_device = SimpleNamespace(endpoints={1: endpoint})
        hass.data["zha"] = {
            "gateway": SimpleNamespace(
                application_controller=SimpleNamespace(devices={eui: zha_device})
            )
        }
        hass.data[DOMAIN] = {
            "calibration_history": {entry.data["device_ieee"]: {"duration_s": 12}}
        }

        payload = await diagnostics.async_get_config_entry_diagnostics(hass, entry)

    assert payload["entry"]["title"] == "Test J1"
    assert payload["device"]["model"] == "J1"
    assert 1 in payload["zha_endpoints"]
    assert payload["last_calibration"]["duration_s"] == 12


@pytest.mark.asyncio
async def test_async_get_device_diagnostics_adds_context():
    hass = _build_hass()
    entry = SimpleNamespace(
        title="Test",
        version=1,
        domain=DOMAIN,
        data={
            "device_id": "device-1",
            "device_ieee": "00:11:22:33:44:55:66:77",
        },
        options={},
    )
    device_obj = SimpleNamespace(id="device-1", identifiers={("ubisys", "test")})

    # Ensure base diagnostics returns predictable data
    with patch(
        "custom_components.ubisys.diagnostics.async_get_config_entry_diagnostics",
        AsyncMock(return_value={"entry": {"title": "Test"}}),
    ) as mock_base:
        with patch(
            "custom_components.ubisys.diagnostics.diagnostics.async_redact_data",
            side_effect=lambda data, _: data,
        ):
            payload = await diagnostics.async_get_device_diagnostics(
                hass, entry, device_obj
            )

    mock_base.assert_awaited_once()
    assert payload["device_context"]["ha_device_id"] == "device-1"
    assert ("ubisys", "test") in payload["device_context"]["identifiers"]
