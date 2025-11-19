"""Tests for J1 calibration module.

Tests cover the 5-phase automated calibration process with motor stall detection.
"""

import asyncio
from unittest.mock import MagicMock, patch

import pytest
from homeassistant.core import ServiceCall
from homeassistant.exceptions import HomeAssistantError

from custom_components.ubisys.const import (
    DOMAIN,
    MODE_ATTR,
    MODE_CALIBRATION,
    MODE_NORMAL,
)
from custom_components.ubisys.j1_calibration import (
    _enter_calibration_mode,
    _exit_calibration_mode,
    _wait_for_stall,
    async_calibrate_j1,
)

# =============================================================================
# Test Constants
# =============================================================================


@pytest.fixture
def mock_service_call():
    """Mock service call for calibration."""
    call = MagicMock(spec=ServiceCall)
    call.data = {"entity_id": "cover.test_j1"}
    return call


@pytest.fixture
def mock_entity_registry():
    """Mock entity registry with a valid J1 entity."""
    with patch("custom_components.ubisys.j1_calibration.er") as mock_er:
        mock_registry = MagicMock()
        mock_entry = MagicMock()
        mock_entry.platform = DOMAIN
        mock_entry.config_entry_id = "test_config_entry_id"
        mock_entry.device_id = "test_device_id"
        mock_registry.async_get.return_value = mock_entry
        mock_er.async_get.return_value = mock_registry
        yield mock_registry


@pytest.fixture
def mock_config_entry():
    """Mock config entry with J1 configuration."""
    entry = MagicMock()
    entry.domain = DOMAIN
    entry.data = {
        "device_ieee": "00:11:22:33:44:55:66:77",
        "shade_type": "roller",
    }
    entry.options = {
        "shade_type": "roller",
    }
    return entry


# =============================================================================
# Test Calibration Mode Functions
# =============================================================================


@pytest.mark.asyncio
async def test_enter_calibration_mode(mock_window_covering_cluster):
    """Test entering calibration mode."""
    cluster = mock_window_covering_cluster

    await _enter_calibration_mode(cluster)

    # Verify calibration mode was set to ENTER (0x02)
    cluster.write_attributes.assert_called_once()
    call_args = cluster.write_attributes.call_args[0][0]
    assert 0x0017 in call_args  # Calibration mode attribute (decimal 23)
    assert call_args[MODE_ATTR] == MODE_CALIBRATION


@pytest.mark.asyncio
async def test_exit_calibration_mode(mock_window_covering_cluster):
    """Test exiting calibration mode."""
    cluster = mock_window_covering_cluster

    await _exit_calibration_mode(cluster)

    # Verify calibration mode was set to EXIT (0x00)
    cluster.write_attributes.assert_called_once()
    call_args = cluster.write_attributes.call_args[0][0]
    assert 0x0017 in call_args  # Calibration mode attribute (decimal 23)
    assert call_args[MODE_ATTR] == MODE_NORMAL


# =============================================================================
# Test Stall Detection
# =============================================================================


@pytest.mark.asyncio
async def test_wait_for_stall_detects_stall():
    """Test that stall detection works when position stops changing."""
    mock_hass = MagicMock()
    entity_id = "cover.test_j1"

    # Mock state that shows position unchanging
    mock_state = MagicMock()
    mock_state.attributes = {"current_position": 100}
    mock_hass.states.get.return_value = mock_state

    # Should detect stall at position 100
    position = await _wait_for_stall(mock_hass, entity_id, "test phase", timeout=10)

    assert position == 100
    # Verify we checked the state multiple times
    assert mock_hass.states.get.call_count >= 2


@pytest.mark.asyncio
async def test_wait_for_stall_timeout():
    """Test that stall detection times out if position keeps changing."""
    mock_hass = MagicMock()
    entity_id = "cover.test_j1"

    # Mock state that keeps changing position
    position_values = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
    mock_states_list = []
    for pos in position_values:
        mock_state = MagicMock()
        mock_state.attributes = {"current_position": pos}
        mock_states_list.append(mock_state)

    # Return different positions each time
    mock_hass.states.get.side_effect = mock_states_list * 100  # Repeat many times

    # Should timeout after 5 seconds
    with pytest.raises(HomeAssistantError, match="Timeout"):
        await _wait_for_stall(mock_hass, entity_id, "test phase", timeout=5)


@pytest.mark.asyncio
async def test_wait_for_stall_entity_unavailable():
    """Test stall detection fails gracefully when entity unavailable."""
    mock_hass = MagicMock()
    entity_id = "cover.test_j1"
    mock_hass.states.get.return_value = None

    with pytest.raises(HomeAssistantError, match="not found"):
        await _wait_for_stall(mock_hass, entity_id, "test phase", timeout=5)


# =============================================================================
# Test Service Validation
# =============================================================================


@pytest.mark.asyncio
async def test_calibrate_service_validates_entity_id_type(
    hass, mock_service_call, mock_entity_registry
):
    """Test that service validates entity_id is a string."""
    mock_service_call.data = {"entity_id": 123}  # Wrong type

    with pytest.raises(HomeAssistantError, match="entity_id must be"):
        await async_calibrate_j1(hass, mock_service_call)


@pytest.mark.asyncio
async def test_calibrate_service_validates_entity_exists(hass, mock_service_call):
    """Test that service validates entity exists in registry."""
    with patch("custom_components.ubisys.j1_calibration.er") as mock_er:
        mock_registry = MagicMock()
        mock_registry.async_get.return_value = None  # Entity doesn't exist
        mock_er.async_get.return_value = mock_registry

        with pytest.raises(HomeAssistantError, match="not found"):
            await async_calibrate_j1(hass, mock_service_call)


@pytest.mark.asyncio
async def test_calibrate_service_validates_platform(hass, mock_service_call):
    """Test that service validates entity belongs to ubisys platform."""
    with patch("custom_components.ubisys.j1_calibration.er") as mock_er:
        mock_registry = MagicMock()
        mock_entry = MagicMock()
        mock_entry.platform = "zha"  # Wrong platform
        mock_registry.async_get.return_value = mock_entry
        mock_er.async_get.return_value = mock_registry

        with pytest.raises(HomeAssistantError, match="not a Ubisys entity"):
            await async_calibrate_j1(hass, mock_service_call)


# =============================================================================
# Test Concurrency Control
# =============================================================================


@pytest.mark.asyncio
async def test_calibrate_prevents_concurrent_calibration(
    mock_service_call, mock_entity_registry, mock_config_entry
):
    """Test that concurrent calibration on same device is prevented."""
    # Setup mock hass
    mock_hass = MagicMock()
    mock_hass.data = {DOMAIN: {}}

    # Mock config_entries properly
    mock_hass.config_entries = MagicMock()
    mock_hass.config_entries.async_get_entry.return_value = mock_config_entry

    with patch("custom_components.ubisys.j1_calibration.er") as mock_er:
        mock_er.async_get.return_value = mock_entity_registry

        with patch(
            "custom_components.ubisys.j1_calibration._find_zha_cover_entity"
        ) as mock_find_zha:
            # Mock finding the ZHA entity
            mock_find_zha.return_value = "cover.zha_test_j1"

            with patch(
                "custom_components.ubisys.j1_calibration._get_window_covering_cluster"
            ) as mock_get_cluster:
                # Mock the cluster
                mock_cluster = MagicMock()
                mock_get_cluster.return_value = mock_cluster

                with patch(
                    "custom_components.ubisys.j1_calibration._perform_calibration"
                ) as mock_perform:
                    # Make calibration take some time
                    async def slow_calibration(*args):
                        await asyncio.sleep(1)

                    mock_perform.side_effect = slow_calibration

                    # Start first calibration (non-blocking)
                    task1 = asyncio.create_task(
                        async_calibrate_j1(mock_hass, mock_service_call)
                    )

                    # Wait a bit to ensure first calibration acquires lock
                    await asyncio.sleep(0.1)

                    # Try to start second calibration (should fail immediately)
                    with pytest.raises(HomeAssistantError, match="already in progress"):
                        await async_calibrate_j1(mock_hass, mock_service_call)

                    # Cancel first task to clean up
                    task1.cancel()
                    try:
                        await task1
                    except (asyncio.CancelledError, HomeAssistantError):
                        pass


# =============================================================================
# Test Error Handling
# =============================================================================


@pytest.mark.asyncio
async def test_calibration_handles_cluster_errors(mock_window_covering_cluster):
    """Test that calibration handles cluster write errors gracefully."""
    cluster = mock_window_covering_cluster
    cluster.write_attributes.side_effect = Exception("Cluster communication failed")

    with pytest.raises(Exception, match="Cluster communication failed"):
        await _enter_calibration_mode(cluster)


@pytest.mark.asyncio
async def test_wait_for_stall_handles_missing_position():
    """Test stall detection handles missing current_position attribute."""
    mock_hass = MagicMock()
    entity_id = "cover.test_j1"

    mock_state = MagicMock()
    mock_state.attributes = {}  # No current_position
    mock_hass.states.get.return_value = mock_state

    # Should timeout after warning about missing position
    with pytest.raises(HomeAssistantError, match="Timeout"):
        await _wait_for_stall(mock_hass, entity_id, "test phase", timeout=5)
