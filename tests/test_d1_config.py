"""Tests for D1 configuration services."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.exceptions import HomeAssistantError

from custom_components.ubisys.d1_config import (
    BALLAST_ATTR_MAX_LEVEL,
    BALLAST_ATTR_MIN_LEVEL,
    DIMMER_SETUP_ATTR_MODE,
    UBISYS_MANUFACTURER_CODE,
    async_configure_ballast,
    async_configure_inputs,
    async_configure_phase_mode,
)


def _make_hass(entity_state: str = "off"):
    """Return a lightweight hass surrogate with state + service helpers."""

    def _get_state(entity_id: str):
        return SimpleNamespace(state=entity_state)

    hass = SimpleNamespace()
    hass.data = {}
    hass.states = SimpleNamespace(get=_get_state)
    hass.services = SimpleNamespace(async_call=AsyncMock())
    return hass


@pytest.mark.asyncio
async def test_async_configure_phase_mode_turns_off_light_when_needed(monkeypatch):
    hass = _make_hass(entity_state="on")
    cluster = MagicMock()

    monkeypatch.setattr(
        "custom_components.ubisys.d1_config.validate_ubisys_entity",
        AsyncMock(return_value=None),
    )
    monkeypatch.setattr(
        "custom_components.ubisys.d1_config.get_entity_device_info",
        AsyncMock(return_value=("device-1", "00:11", "D1")),
    )
    monkeypatch.setattr(
        "custom_components.ubisys.d1_config.get_cluster",
        AsyncMock(return_value=cluster),
    )
    write_mock = AsyncMock()
    monkeypatch.setattr(
        "custom_components.ubisys.d1_config.async_write_and_verify_attrs",
        write_mock,
    )
    sleep_mock = AsyncMock()
    monkeypatch.setattr("custom_components.ubisys.d1_config.asyncio.sleep", sleep_mock)

    await async_configure_phase_mode(hass, "light.test_d1", "forward")

    hass.services.async_call.assert_awaited_once_with(
        "light", "turn_off", {"entity_id": "light.test_d1"}, blocking=True
    )
    sleep_mock.assert_awaited_once()
    write_mock.assert_awaited_once_with(
        cluster,
        {DIMMER_SETUP_ATTR_MODE: 1},
        manufacturer=UBISYS_MANUFACTURER_CODE,
    )


@pytest.mark.asyncio
async def test_async_configure_phase_mode_rejects_invalid_mode(monkeypatch):
    hass = _make_hass()
    monkeypatch.setattr(
        "custom_components.ubisys.d1_config.validate_ubisys_entity",
        AsyncMock(return_value=None),
    )

    with pytest.raises(HomeAssistantError, match="Invalid phase mode"):
        await async_configure_phase_mode(hass, "light.test_d1", "invalid")


@pytest.mark.asyncio
async def test_async_configure_ballast_writes_requested_levels(monkeypatch):
    hass = _make_hass()
    cluster = MagicMock()

    monkeypatch.setattr(
        "custom_components.ubisys.d1_config.validate_ubisys_entity",
        AsyncMock(return_value=None),
    )
    monkeypatch.setattr(
        "custom_components.ubisys.d1_config.get_entity_device_info",
        AsyncMock(return_value=("device-1", "00:11", "D1")),
    )
    monkeypatch.setattr(
        "custom_components.ubisys.d1_config.get_cluster",
        AsyncMock(return_value=cluster),
    )
    write_mock = AsyncMock()
    monkeypatch.setattr(
        "custom_components.ubisys.d1_config.async_write_and_verify_attrs",
        write_mock,
    )

    await async_configure_ballast(hass, "light.test_d1", min_level=10, max_level=200)

    write_mock.assert_awaited_once()
    call = write_mock.await_args
    assert call.args[0] is cluster
    assert call.args[1] == {
        BALLAST_ATTR_MIN_LEVEL: 10,
        BALLAST_ATTR_MAX_LEVEL: 200,
    }
    assert call.kwargs == {}


@pytest.mark.asyncio
async def test_async_configure_ballast_requires_values(monkeypatch):
    hass = _make_hass()
    monkeypatch.setattr(
        "custom_components.ubisys.d1_config.validate_ubisys_entity",
        AsyncMock(return_value=None),
    )

    with pytest.raises(HomeAssistantError, match="At least one of"):
        await async_configure_ballast(hass, "light.test_d1")


@pytest.mark.asyncio
async def test_async_configure_ballast_raises_when_cluster_missing(monkeypatch):
    hass = _make_hass()

    monkeypatch.setattr(
        "custom_components.ubisys.d1_config.validate_ubisys_entity",
        AsyncMock(return_value=None),
    )
    monkeypatch.setattr(
        "custom_components.ubisys.d1_config.get_entity_device_info",
        AsyncMock(return_value=("device-1", "00:11", "D1")),
    )
    monkeypatch.setattr(
        "custom_components.ubisys.d1_config.get_cluster",
        AsyncMock(return_value=None),
    )

    with pytest.raises(HomeAssistantError, match="Ballast cluster"):
        await async_configure_ballast(hass, "light.test_d1", min_level=15)


@pytest.mark.asyncio
async def test_async_configure_inputs_not_yet_implemented(monkeypatch):
    hass = _make_hass()
    monkeypatch.setattr(
        "custom_components.ubisys.d1_config.validate_ubisys_entity",
        AsyncMock(return_value=None),
    )

    with pytest.raises(HomeAssistantError, match="not yet implemented"):
        await async_configure_inputs(hass, "light.test_d1", "config")
