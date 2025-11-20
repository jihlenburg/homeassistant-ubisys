"""Tests for D1 configuration services."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, Dict, cast
from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.exceptions import HomeAssistantError

from custom_components.ubisys.const import (
    BALLAST_ATTR_MAX_LEVEL,
    BALLAST_ATTR_MIN_LEVEL,
    DIMMER_SETUP_ATTR_MODE,
    LEVEL_CONTROL_ATTR_ON_LEVEL,
    LEVEL_CONTROL_ATTR_ON_OFF_TRANSITION_TIME,
    LEVEL_CONTROL_ATTR_STARTUP_LEVEL,
    ON_OFF_ATTR_STARTUP_ON_OFF,
    UBISYS_MANUFACTURER_CODE,
)
from custom_components.ubisys.d1_config import (
    async_configure_ballast,
    async_configure_inputs,
    async_configure_on_level,
    async_configure_phase_mode,
    async_configure_startup,
    async_configure_transition_time,
    async_get_status,
)


def _make_hass(entity_state: str = "off") -> SimpleNamespace:
    """Return a lightweight hass surrogate with state + service helpers."""

    def _get_state(entity_id: str) -> SimpleNamespace:
        return SimpleNamespace(entity_id=entity_id, state=entity_state)

    hass = SimpleNamespace()
    hass.data = cast(Dict[str, Any], {})
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


# =============================================================================
# async_configure_transition_time tests
# =============================================================================


@pytest.mark.asyncio
async def test_async_configure_transition_time_writes_value(monkeypatch):
    """Test transition time is written to Level Control cluster."""
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

    await async_configure_transition_time(hass, "light.test_d1", 20)  # 2 seconds

    write_mock.assert_awaited_once()
    call = write_mock.await_args
    assert call.args[0] is cluster
    assert call.args[1] == {LEVEL_CONTROL_ATTR_ON_OFF_TRANSITION_TIME: 20}


@pytest.mark.asyncio
async def test_async_configure_transition_time_rejects_invalid_range(monkeypatch):
    """Test transition time validation rejects out-of-range values."""
    hass = _make_hass()

    monkeypatch.setattr(
        "custom_components.ubisys.d1_config.validate_ubisys_entity",
        AsyncMock(return_value=None),
    )

    # Too large value
    with pytest.raises(HomeAssistantError, match="transition_time must be between"):
        await async_configure_transition_time(hass, "light.test_d1", 100000)


@pytest.mark.asyncio
async def test_async_configure_transition_time_rejects_non_d1(monkeypatch):
    """Test transition time rejects non-D1 models."""
    hass = _make_hass()

    monkeypatch.setattr(
        "custom_components.ubisys.d1_config.validate_ubisys_entity",
        AsyncMock(return_value=None),
    )
    monkeypatch.setattr(
        "custom_components.ubisys.d1_config.get_entity_device_info",
        AsyncMock(return_value=("device-1", "00:11", "J1")),  # Not a D1
    )

    with pytest.raises(HomeAssistantError, match="is not a D1 dimmer"):
        await async_configure_transition_time(hass, "light.test_d1", 20)


@pytest.mark.asyncio
async def test_async_configure_transition_time_cluster_missing(monkeypatch):
    """Test transition time raises error when cluster missing."""
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

    with pytest.raises(HomeAssistantError, match="Could not access Level Control"):
        await async_configure_transition_time(hass, "light.test_d1", 20)


# =============================================================================
# async_configure_on_level tests
# =============================================================================


@pytest.mark.asyncio
async def test_async_configure_on_level_writes_values(monkeypatch):
    """Test on_level and startup_level are written to cluster."""
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

    await async_configure_on_level(
        hass, "light.test_d1", on_level=128, startup_level=200
    )

    write_mock.assert_awaited_once()
    call = write_mock.await_args
    assert call.args[0] is cluster
    assert LEVEL_CONTROL_ATTR_ON_LEVEL in call.args[1]
    assert LEVEL_CONTROL_ATTR_STARTUP_LEVEL in call.args[1]
    assert call.args[1][LEVEL_CONTROL_ATTR_ON_LEVEL] == 128
    assert call.args[1][LEVEL_CONTROL_ATTR_STARTUP_LEVEL] == 200


@pytest.mark.asyncio
async def test_async_configure_on_level_only_on_level(monkeypatch):
    """Test on_level can be set without startup_level."""
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

    await async_configure_on_level(hass, "light.test_d1", on_level=100)

    write_mock.assert_awaited_once()
    call = write_mock.await_args
    assert LEVEL_CONTROL_ATTR_ON_LEVEL in call.args[1]
    assert LEVEL_CONTROL_ATTR_STARTUP_LEVEL not in call.args[1]


@pytest.mark.asyncio
async def test_async_configure_on_level_requires_at_least_one(monkeypatch):
    """Test on_level requires at least one parameter."""
    hass = _make_hass()

    monkeypatch.setattr(
        "custom_components.ubisys.d1_config.validate_ubisys_entity",
        AsyncMock(return_value=None),
    )

    with pytest.raises(HomeAssistantError, match="At least one of"):
        await async_configure_on_level(hass, "light.test_d1")


@pytest.mark.asyncio
async def test_async_configure_on_level_rejects_invalid_range(monkeypatch):
    """Test on_level rejects out-of-range values."""
    hass = _make_hass()

    monkeypatch.setattr(
        "custom_components.ubisys.d1_config.validate_ubisys_entity",
        AsyncMock(return_value=None),
    )

    # Value too high
    with pytest.raises(HomeAssistantError, match="on_level must be between"):
        await async_configure_on_level(hass, "light.test_d1", on_level=300)


# =============================================================================
# async_configure_startup tests
# =============================================================================


@pytest.mark.asyncio
async def test_async_configure_startup_writes_on_off(monkeypatch):
    """Test startup on/off configuration is written."""
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

    await async_configure_startup(hass, "light.test_d1", startup_on_off="on")

    write_mock.assert_awaited_once()
    call = write_mock.await_args
    assert ON_OFF_ATTR_STARTUP_ON_OFF in call.args[1]


@pytest.mark.asyncio
async def test_async_configure_startup_rejects_invalid_value(monkeypatch):
    """Test startup rejects invalid on_off value."""
    hass = _make_hass()

    monkeypatch.setattr(
        "custom_components.ubisys.d1_config.validate_ubisys_entity",
        AsyncMock(return_value=None),
    )

    with pytest.raises(HomeAssistantError, match="Invalid startup_on_off"):
        await async_configure_startup(hass, "light.test_d1", startup_on_off="invalid")


@pytest.mark.asyncio
async def test_async_configure_startup_cluster_missing(monkeypatch):
    """Test startup raises error when cluster missing."""
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

    with pytest.raises(HomeAssistantError, match="Could not access"):
        await async_configure_startup(hass, "light.test_d1", startup_on_off="on")


# =============================================================================
# async_get_status tests
# =============================================================================


@pytest.mark.asyncio
async def test_async_get_status_reads_clusters(monkeypatch):
    """Test status reads from multiple clusters."""
    hass = _make_hass()

    # Create mock clusters with read_attributes returning appropriate data
    dimmer_cluster = MagicMock()
    dimmer_cluster.read_attributes = AsyncMock(
        return_value=({0x0000: 1, 0x0001: 0}, {})
    )

    ballast_cluster = MagicMock()
    ballast_cluster.read_attributes = AsyncMock(
        return_value=({BALLAST_ATTR_MIN_LEVEL: 10, BALLAST_ATTR_MAX_LEVEL: 254}, {})
    )

    level_cluster = MagicMock()
    level_cluster.read_attributes = AsyncMock(
        return_value=({0x0011: 128, 0x4000: 255}, {})
    )

    on_off_cluster = MagicMock()
    on_off_cluster.read_attributes = AsyncMock(return_value=({0x4003: 1}, {}))

    def get_cluster_side_effect(hass, ieee, cluster_id, endpoint, name):
        cluster_map = {
            0xFC01: dimmer_cluster,
            0x0301: ballast_cluster,
            0x0008: level_cluster,
            0x0006: on_off_cluster,
        }
        return cluster_map.get(cluster_id)

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
        AsyncMock(side_effect=get_cluster_side_effect),
    )

    result = await async_get_status(hass, "light.test_d1")

    # Result should be a dictionary with status information
    assert isinstance(result, dict)
    # Check for expected status keys
    assert "forward_phase_control" in result or "ballast_min_level" in result


@pytest.mark.asyncio
async def test_async_get_status_handles_missing_cluster(monkeypatch):
    """Test status raises error when DimmerSetup cluster missing."""
    hass = _make_hass()

    monkeypatch.setattr(
        "custom_components.ubisys.d1_config.validate_ubisys_entity",
        AsyncMock(return_value=None),
    )
    monkeypatch.setattr(
        "custom_components.ubisys.d1_config.get_entity_device_info",
        AsyncMock(return_value=("device-1", "00:11", "D1")),
    )
    # All clusters return None
    monkeypatch.setattr(
        "custom_components.ubisys.d1_config.get_cluster",
        AsyncMock(return_value=None),
    )

    # Should raise error when DimmerSetup cluster is missing
    with pytest.raises(
        HomeAssistantError, match="Could not access DimmerSetup cluster"
    ):
        await async_get_status(hass, "light.test_d1")


# =============================================================================
# Additional edge case tests
# =============================================================================


@pytest.mark.asyncio
async def test_async_configure_phase_mode_reverse(monkeypatch):
    """Test reverse phase mode configuration."""
    hass = _make_hass(entity_state="off")
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

    await async_configure_phase_mode(hass, "light.test_d1", "reverse")

    write_mock.assert_awaited_once_with(
        cluster,
        {DIMMER_SETUP_ATTR_MODE: 2},  # Reverse = 2
        manufacturer=UBISYS_MANUFACTURER_CODE,
    )


@pytest.mark.asyncio
async def test_async_configure_phase_mode_cluster_missing(monkeypatch):
    """Test phase mode raises error when cluster missing."""
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

    with pytest.raises(HomeAssistantError, match="DimmerSetup cluster"):
        await async_configure_phase_mode(hass, "light.test_d1", "forward")
