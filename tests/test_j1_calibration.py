"""Tests for J1 calibration module.

Tests cover the 5-phase automated calibration process with motor stall detection.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

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
    _calibration_phase_1_enter_mode,
    _calibration_phase_1b_prepare_position,
    _calibration_phase_2_find_top,
    _calibration_phase_3_find_bottom,
    _calibration_phase_4_verify,
    _calibration_phase_5_finalize,
    _enter_calibration_mode,
    _exit_calibration_mode,
    _perform_calibration,
    _wait_for_motor_stop,
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


# =============================================================================
# Test Calibration Phase Functions
# =============================================================================


@pytest.mark.asyncio
async def test_calibration_phase_1_enter_mode_success(mock_window_covering_cluster):
    """Test phase 1 successfully enters calibration mode."""
    cluster = mock_window_covering_cluster

    with patch(
        "custom_components.ubisys.j1_calibration.async_write_and_verify_attrs"
    ) as mock_write:
        mock_write.return_value = None

        with patch(
            "custom_components.ubisys.j1_calibration._prepare_calibration_limits"
        ) as mock_limits:
            mock_limits.return_value = False  # Not a re-calibration

            with patch(
                "custom_components.ubisys.j1_calibration._enter_calibration_mode"
            ) as mock_enter:
                mock_enter.return_value = None

                result = await _calibration_phase_1_enter_mode(cluster, "roller")

                assert result is False  # Not a re-calibration
                mock_write.assert_called_once()
                mock_limits.assert_called_once()
                mock_enter.assert_called_once()


@pytest.mark.asyncio
async def test_calibration_phase_1_enter_mode_recalibration(
    mock_window_covering_cluster,
):
    """Test phase 1 detects re-calibration scenario."""
    cluster = mock_window_covering_cluster

    with patch(
        "custom_components.ubisys.j1_calibration.async_write_and_verify_attrs"
    ) as mock_write:
        mock_write.return_value = None

        with patch(
            "custom_components.ubisys.j1_calibration._prepare_calibration_limits"
        ) as mock_limits:
            mock_limits.return_value = True  # Is a re-calibration

            with patch(
                "custom_components.ubisys.j1_calibration._enter_calibration_mode"
            ) as mock_enter:
                mock_enter.return_value = None

                result = await _calibration_phase_1_enter_mode(cluster, "venetian")

                assert result is True  # Is re-calibration


@pytest.mark.asyncio
async def test_calibration_phase_1_enter_mode_write_failure(
    mock_window_covering_cluster,
):
    """Test phase 1 handles WindowCoveringType write failure."""
    cluster = mock_window_covering_cluster

    with patch(
        "custom_components.ubisys.j1_calibration.async_write_and_verify_attrs"
    ) as mock_write:
        mock_write.side_effect = Exception("Cluster write failed")

        with pytest.raises(
            HomeAssistantError, match="Failed to set WindowCoveringType"
        ):
            await _calibration_phase_1_enter_mode(cluster, "roller")


@pytest.mark.asyncio
async def test_calibration_phase_1b_prepare_position():
    """Test phase 1b moves shade away from top position."""
    mock_hass = MagicMock()
    cluster = MagicMock()

    with patch("custom_components.ubisys.j1_calibration.async_zcl_command") as mock_cmd:
        mock_cmd.return_value = None

        with patch(
            "custom_components.ubisys.j1_calibration.is_verbose_info_logging"
        ) as mock_verbose:
            mock_verbose.return_value = False

            await _calibration_phase_1b_prepare_position(mock_hass, cluster)

            # Should call down_close and stop commands
            assert mock_cmd.call_count == 2
            calls = [call[0][1] for call in mock_cmd.call_args_list]
            assert "down_close" in calls
            assert "stop" in calls


@pytest.mark.asyncio
async def test_calibration_phase_1b_command_failure():
    """Test phase 1b handles command failure."""
    mock_hass = MagicMock()
    cluster = MagicMock()

    with patch("custom_components.ubisys.j1_calibration.async_zcl_command") as mock_cmd:
        mock_cmd.side_effect = Exception("Command failed")

        with patch(
            "custom_components.ubisys.j1_calibration.is_verbose_info_logging"
        ) as mock_verbose:
            mock_verbose.return_value = False

            with pytest.raises(HomeAssistantError, match="down_close"):
                await _calibration_phase_1b_prepare_position(mock_hass, cluster)


@pytest.mark.asyncio
async def test_calibration_phase_2_find_top_success():
    """Test phase 2 finds top limit successfully."""
    mock_hass = MagicMock()
    cluster = MagicMock()
    entity_id = "cover.test_j1"

    with patch("custom_components.ubisys.j1_calibration.async_zcl_command") as mock_cmd:
        mock_cmd.return_value = None

        with patch(
            "custom_components.ubisys.j1_calibration._wait_for_motor_stop"
        ) as mock_wait:
            mock_wait.return_value = None

            with patch(
                "custom_components.ubisys.j1_calibration.is_verbose_info_logging"
            ) as mock_verbose:
                mock_verbose.return_value = False

                result = await _calibration_phase_2_find_top(
                    mock_hass, cluster, entity_id
                )

                assert result == 100
                mock_cmd.assert_called_once()
                # Verify up_open command was sent
                assert mock_cmd.call_args[0][1] == "up_open"
                mock_wait.assert_called_once()


@pytest.mark.asyncio
async def test_calibration_phase_2_command_failure():
    """Test phase 2 handles up_open command failure."""
    mock_hass = MagicMock()
    cluster = MagicMock()
    entity_id = "cover.test_j1"

    with patch("custom_components.ubisys.j1_calibration.async_zcl_command") as mock_cmd:
        mock_cmd.side_effect = Exception("up_open failed")

        with patch(
            "custom_components.ubisys.j1_calibration.is_verbose_info_logging"
        ) as mock_verbose:
            mock_verbose.return_value = False

            with pytest.raises(HomeAssistantError, match="up_open"):
                await _calibration_phase_2_find_top(mock_hass, cluster, entity_id)


@pytest.mark.asyncio
async def test_calibration_phase_3_find_bottom_success():
    """Test phase 3 finds bottom limit and reads total_steps."""
    mock_hass = MagicMock()
    cluster = MagicMock()
    # read_attributes returns tuple: (success_dict, failure_dict)
    cluster.read_attributes = AsyncMock(return_value=({0x1002: 5000}, {}))
    entity_id = "cover.test_j1"

    with patch("custom_components.ubisys.j1_calibration.async_zcl_command") as mock_cmd:
        mock_cmd.return_value = None

        with patch(
            "custom_components.ubisys.j1_calibration._wait_for_motor_stop"
        ) as mock_wait:
            mock_wait.return_value = None

            with patch(
                "custom_components.ubisys.j1_calibration.is_verbose_info_logging"
            ) as mock_verbose:
                mock_verbose.return_value = False

                result = await _calibration_phase_3_find_bottom(
                    mock_hass, cluster, entity_id
                )

                # Should return total_steps read from device
                assert result == 5000
                # Verify down_close command was sent
                calls = [call[0][1] for call in mock_cmd.call_args_list]
                assert "down_close" in calls


@pytest.mark.asyncio
async def test_calibration_phase_4_verify_success():
    """Test phase 4 verification run completes successfully."""
    mock_hass = MagicMock()
    cluster = MagicMock()
    entity_id = "cover.test_j1"

    with patch("custom_components.ubisys.j1_calibration.async_zcl_command") as mock_cmd:
        mock_cmd.return_value = None

        with patch(
            "custom_components.ubisys.j1_calibration._wait_for_motor_stop"
        ) as mock_wait:
            mock_wait.return_value = None

            with patch(
                "custom_components.ubisys.j1_calibration.is_verbose_info_logging"
            ) as mock_verbose:
                mock_verbose.return_value = False

                result = await _calibration_phase_4_verify(
                    mock_hass, cluster, entity_id
                )

                # Phase 4 always returns 100 (fixed position for verification)
                assert result == 100
                # Verify up_open command was sent for verification
                mock_cmd.assert_called_once()


@pytest.mark.asyncio
async def test_calibration_phase_5_finalize_roller():
    """Test phase 5 finalizes calibration for roller shade (lift-only, no tilt)."""
    cluster = MagicMock()

    with patch(
        "custom_components.ubisys.j1_calibration.async_write_and_verify_attrs"
    ) as mock_write:
        mock_write.return_value = None

        with patch(
            "custom_components.ubisys.j1_calibration._exit_calibration_mode"
        ) as mock_exit:
            mock_exit.return_value = None

            await _calibration_phase_5_finalize(cluster, "roller", 5000, False)

            # Roller shades are lift-only, no tilt capability
            # So tilt steps should NOT be written
            mock_write.assert_not_called()
            # But exit calibration mode should always be called
            mock_exit.assert_called_once()


@pytest.mark.asyncio
async def test_calibration_phase_5_finalize_venetian():
    """Test phase 5 finalizes calibration for venetian blind with tilt."""
    cluster = MagicMock()

    with patch(
        "custom_components.ubisys.j1_calibration.async_write_and_verify_attrs"
    ) as mock_write:
        mock_write.return_value = None

        with patch(
            "custom_components.ubisys.j1_calibration._exit_calibration_mode"
        ) as mock_exit:
            mock_exit.return_value = None

            await _calibration_phase_5_finalize(cluster, "venetian", 5000, False)

            # Should write lift_to_tilt_transition_steps (non-zero for venetian)
            mock_write.assert_called_once()
            call_args = mock_write.call_args[0][1]
            # Venetian blinds have tilt steps > 0
            assert 0x1001 in call_args  # UBISYS_ATTR_LIFT_TO_TILT_TRANSITION_STEPS


# =============================================================================
# Test Motor Stop Detection
# =============================================================================


@pytest.mark.asyncio
async def test_wait_for_motor_stop_immediate_stop():
    """Test motor stop detection when motor already stopped."""
    cluster = MagicMock()
    # Motor already stopped (OperationalStatus = 0x00)
    # read_attributes returns tuple: (success_dict, failure_dict)
    cluster.read_attributes = AsyncMock(return_value=({0x000A: 0x00}, {}))

    await _wait_for_motor_stop(cluster, "test phase")

    # Should return immediately without long polling
    cluster.read_attributes.assert_called()


@pytest.mark.asyncio
async def test_wait_for_motor_stop_delayed_stop():
    """Test motor stop detection with delayed stop."""
    cluster = MagicMock()
    # First few reads show motor running, then stopped
    # read_attributes returns tuple: (success_dict, failure_dict)
    cluster.read_attributes = AsyncMock(
        side_effect=[
            ({0x000A: 0x01}, {}),  # Running
            ({0x000A: 0x01}, {}),  # Running
            ({0x000A: 0x00}, {}),  # Stopped
        ]
    )

    await _wait_for_motor_stop(cluster, "test phase", timeout=10)

    # Should have polled multiple times
    assert cluster.read_attributes.call_count == 3


@pytest.mark.asyncio
async def test_wait_for_motor_stop_timeout():
    """Test motor stop detection timeout."""
    cluster = MagicMock()
    # Motor never stops - read_attributes returns tuple: (success_dict, failure_dict)
    cluster.read_attributes = AsyncMock(return_value=({0x000A: 0x01}, {}))

    with pytest.raises(HomeAssistantError, match="Timeout"):
        await _wait_for_motor_stop(cluster, "test phase", timeout=2)


# =============================================================================
# Test Service Handler (async_calibrate_j1)
# =============================================================================


@pytest.mark.asyncio
async def test_async_calibrate_j1_missing_entity_id():
    """Test service handler raises error when entity_id is missing."""
    mock_hass = MagicMock()
    mock_call = MagicMock()
    mock_call.data = {}

    with pytest.raises(HomeAssistantError, match="Missing required parameter"):
        await async_calibrate_j1(mock_hass, mock_call)


@pytest.mark.asyncio
async def test_async_calibrate_j1_empty_entity_list():
    """Test service handler raises error when entity_id list is empty."""
    mock_hass = MagicMock()
    mock_call = MagicMock()
    mock_call.data = {"entity_id": []}

    with pytest.raises(HomeAssistantError, match="list cannot be empty"):
        await async_calibrate_j1(mock_hass, mock_call)


@pytest.mark.asyncio
async def test_async_calibrate_j1_invalid_entity_id_type():
    """Test service handler raises error for invalid entity_id type."""
    mock_hass = MagicMock()
    mock_call = MagicMock()
    mock_call.data = {"entity_id": 12345}  # Invalid type

    with pytest.raises(HomeAssistantError, match="must be a string or list"):
        await async_calibrate_j1(mock_hass, mock_call)


@pytest.mark.asyncio
async def test_async_calibrate_j1_invalid_entity_in_list():
    """Test service handler raises error for non-string in entity list."""
    mock_hass = MagicMock()
    mock_call = MagicMock()
    mock_call.data = {"entity_id": ["cover.valid", 123]}  # Invalid entry

    with pytest.raises(HomeAssistantError, match="must be non-empty strings"):
        await async_calibrate_j1(mock_hass, mock_call)


@pytest.mark.asyncio
async def test_async_calibrate_j1_empty_string_in_list():
    """Test service handler raises error for empty string in entity list."""
    mock_hass = MagicMock()
    mock_call = MagicMock()
    mock_call.data = {"entity_id": ["cover.valid", ""]}  # Empty string

    with pytest.raises(HomeAssistantError, match="must be non-empty strings"):
        await async_calibrate_j1(mock_hass, mock_call)


# =============================================================================
# Test Perform Calibration Orchestrator
# =============================================================================


@pytest.mark.asyncio
async def test_perform_calibration_success():
    """Test full calibration orchestrator success path."""
    mock_hass = MagicMock()
    mock_hass.data = {DOMAIN: {}}
    mock_hass.services = MagicMock()
    mock_hass.services.async_call = AsyncMock()

    with patch(
        "custom_components.ubisys.j1_calibration._get_window_covering_cluster"
    ) as mock_get_cluster:
        cluster = MagicMock()
        mock_get_cluster.return_value = cluster

        with patch(
            "custom_components.ubisys.j1_calibration._calibration_phase_1_enter_mode"
        ) as mock_p1:
            mock_p1.return_value = True  # Not recalibration

            with patch(
                "custom_components.ubisys.j1_calibration._calibration_phase_1b_prepare_position"
            ) as mock_p1b:
                mock_p1b.return_value = None

                with patch(
                    "custom_components.ubisys.j1_calibration._calibration_phase_2_find_top"
                ) as mock_p2:
                    mock_p2.return_value = 100

                    with patch(
                        "custom_components.ubisys.j1_calibration._calibration_phase_3_find_bottom"
                    ) as mock_p3:
                        mock_p3.return_value = 5000

                        with patch(
                            "custom_components.ubisys.j1_calibration._calibration_phase_4_verify"
                        ) as mock_p4:
                            mock_p4.return_value = 100

                            with patch(
                                "custom_components.ubisys.j1_calibration._calibration_phase_5_finalize"
                            ) as mock_p5:
                                mock_p5.return_value = None

                                with patch(
                                    "custom_components.ubisys.j1_calibration.is_verbose_info_logging"
                                ) as mock_verbose:
                                    mock_verbose.return_value = False

                                    total, tilt = await _perform_calibration(
                                        mock_hass,
                                        "cover.zha_test",
                                        "00:11:22:33",
                                        "roller",
                                    )

                                    assert total == 5000
                                    # All phases should be called
                                    mock_p1.assert_called_once()
                                    mock_p1b.assert_called_once()
                                    mock_p2.assert_called_once()
                                    mock_p3.assert_called_once()
                                    mock_p4.assert_called_once()
                                    mock_p5.assert_called_once()


@pytest.mark.asyncio
async def test_perform_calibration_cluster_not_found():
    """Test orchestrator raises error when cluster not found."""
    mock_hass = MagicMock()
    mock_hass.data = {DOMAIN: {}}
    mock_hass.services = MagicMock()
    mock_hass.services.async_call = AsyncMock()

    with patch(
        "custom_components.ubisys.j1_calibration._get_window_covering_cluster"
    ) as mock_get_cluster:
        mock_get_cluster.return_value = None  # Cluster not found

        with pytest.raises(HomeAssistantError, match="WindowCovering cluster"):
            await _perform_calibration(
                mock_hass, "cover.zha_test", "00:11:22:33", "roller"
            )


@pytest.mark.asyncio
async def test_perform_calibration_phase_1_failure():
    """Test orchestrator handles phase 1 failure."""
    mock_hass = MagicMock()
    mock_hass.data = {DOMAIN: {}}
    mock_hass.services = MagicMock()
    mock_hass.services.async_call = AsyncMock()

    with patch(
        "custom_components.ubisys.j1_calibration._get_window_covering_cluster"
    ) as mock_get_cluster:
        cluster = MagicMock()
        mock_get_cluster.return_value = cluster

        with patch(
            "custom_components.ubisys.j1_calibration._calibration_phase_1_enter_mode"
        ) as mock_p1:
            mock_p1.side_effect = HomeAssistantError("Phase 1 failed")

            with pytest.raises(HomeAssistantError, match="Phase 1 failed"):
                await _perform_calibration(
                    mock_hass, "cover.zha_test", "00:11:22:33", "roller"
                )


# =============================================================================
# Test Helper Functions
# =============================================================================


@pytest.mark.asyncio
async def test_validate_device_ready_success(monkeypatch):
    """Test device validation passes for available entity."""
    from custom_components.ubisys.j1_calibration import _validate_device_ready

    mock_hass = MagicMock()
    mock_state = MagicMock()
    mock_state.state = "open"
    mock_hass.states.get.return_value = mock_state

    # Should not raise
    await _validate_device_ready(mock_hass, "cover.test")

    mock_hass.states.get.assert_called_once_with("cover.test")


@pytest.mark.asyncio
async def test_validate_device_ready_unavailable():
    """Test device validation fails for unavailable entity."""
    from custom_components.ubisys.j1_calibration import _validate_device_ready

    mock_hass = MagicMock()
    mock_state = MagicMock()
    mock_state.state = "unavailable"
    mock_hass.states.get.return_value = mock_state

    with pytest.raises(HomeAssistantError, match="unavailable"):
        await _validate_device_ready(mock_hass, "cover.test")


@pytest.mark.asyncio
async def test_validate_device_ready_not_found():
    """Test device validation fails when entity not found."""
    from custom_components.ubisys.j1_calibration import _validate_device_ready

    mock_hass = MagicMock()
    mock_hass.states.get.return_value = None

    with pytest.raises(HomeAssistantError, match="not found"):
        await _validate_device_ready(mock_hass, "cover.test")


@pytest.mark.asyncio
async def test_find_zha_cover_entity_success():
    """Test finding ZHA cover entity for device."""
    from types import SimpleNamespace

    from custom_components.ubisys.j1_calibration import _find_zha_cover_entity

    mock_hass = MagicMock()

    # Create mock entity entry
    entity_entry = SimpleNamespace(
        entity_id="cover.zha_test",
        platform="zha",
        domain="cover",
    )

    # Mock entity registry and async_entries_for_device
    with patch("custom_components.ubisys.j1_calibration.er.async_get") as mock_er:
        mock_registry = MagicMock()
        mock_er.return_value = mock_registry

        with patch(
            "custom_components.ubisys.j1_calibration.er.async_entries_for_device"
        ) as mock_entries:
            mock_entries.return_value = [entity_entry]

            result = await _find_zha_cover_entity(mock_hass, "device_123")

            assert result == "cover.zha_test"


@pytest.mark.asyncio
async def test_find_zha_cover_entity_not_found():
    """Test finding ZHA cover entity when none exists."""
    from custom_components.ubisys.j1_calibration import _find_zha_cover_entity

    mock_hass = MagicMock()

    # Mock entity registry with no matching entities
    with patch("custom_components.ubisys.j1_calibration.er.async_get") as mock_er:
        mock_registry = MagicMock()
        mock_er.return_value = mock_registry

        with patch(
            "custom_components.ubisys.j1_calibration.er.async_entries_for_device"
        ) as mock_entries:
            mock_entries.return_value = []

            result = await _find_zha_cover_entity(mock_hass, "device_123")

            assert result is None


# =============================================================================
# Test Additional Phase Error Paths
# =============================================================================


@pytest.mark.asyncio
async def test_calibration_phase_3_invalid_total_steps():
    """Test phase 3 raises error for invalid total_steps."""
    mock_hass = MagicMock()
    cluster = MagicMock()
    # Return invalid total_steps (0xFFFF is invalid)
    cluster.read_attributes = AsyncMock(return_value=({0x1002: 0xFFFF}, {}))
    entity_id = "cover.test_j1"

    with patch("custom_components.ubisys.j1_calibration.async_zcl_command") as mock_cmd:
        mock_cmd.return_value = None

        with patch(
            "custom_components.ubisys.j1_calibration._wait_for_motor_stop"
        ) as mock_wait:
            mock_wait.return_value = None

            with patch(
                "custom_components.ubisys.j1_calibration.is_verbose_info_logging"
            ) as mock_verbose:
                mock_verbose.return_value = False

                with pytest.raises(HomeAssistantError, match="Invalid total_steps"):
                    await _calibration_phase_3_find_bottom(
                        mock_hass, cluster, entity_id
                    )


@pytest.mark.asyncio
async def test_calibration_phase_2_command_failure_exception():
    """Test phase 2 handles command failure with exception."""
    mock_hass = MagicMock()
    cluster = MagicMock()
    entity_id = "cover.test_j1"

    with patch("custom_components.ubisys.j1_calibration.async_zcl_command") as mock_cmd:
        mock_cmd.side_effect = Exception("Command failed")

        with patch(
            "custom_components.ubisys.j1_calibration.is_verbose_info_logging"
        ) as mock_verbose:
            mock_verbose.return_value = False

            with pytest.raises(HomeAssistantError, match="Failed to send"):
                await _calibration_phase_2_find_top(mock_hass, cluster, entity_id)
