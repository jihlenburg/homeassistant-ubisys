"""Test fixtures and configuration for Ubisys integration tests.

This module provides reusable fixtures for testing the Ubisys Home Assistant
integration. Fixtures are organized by complexity and use case.
"""

from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant import setup
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

# =============================================================================
# SIMPLE FIXTURES - For tests that don't need full Home Assistant
# =============================================================================


@pytest.fixture
def hass():
    """Minimal Home Assistant fixture for simple unit tests.

    This is a SimpleNamespace object that can be used for tests that only need
    to store data on hass (like hass.data) but don't need actual HA functionality.

    Use this for:
    - Unit tests of pure functions
    - Tests that just need hass as a data container

    For tests that need actual HA functionality, use hass_full instead.
    """
    return SimpleNamespace()


# =============================================================================
# HOME ASSISTANT FIXTURES - Full HA instance for integration tests
# =============================================================================


@pytest.fixture
async def hass_full():
    """Full Home Assistant instance for integration tests.

    Provides a real Home Assistant instance with core setup complete.
    Use this for:
    - Config flow tests
    - Platform tests (entity lifecycle)
    - Integration tests that need HA services/registry/etc.

    Note: This is slower than the simple hass fixture, so only use when needed.
    """
    hass_instance = HomeAssistant()
    await setup.async_setup_component(hass_instance, "homeassistant", {})
    await hass_instance.async_block_till_done()
    yield hass_instance
    await hass_instance.async_stop()


# =============================================================================
# ZIGBEE/ZHA MOCK FIXTURES - Mock Zigbee clusters and devices
# =============================================================================


@pytest.fixture
def mock_window_covering_cluster():
    """Mock WindowCovering cluster for J1 device testing.

    Returns a MagicMock cluster with:
    - cluster_id = 0x0102 (WindowCovering)
    - endpoint.endpoint_id = 2 (J1 uses EP2)
    - Mocked async methods: write_attributes, read_attributes, command

    Example:
        async def test_calibration(mock_window_covering_cluster):
            cluster = mock_window_covering_cluster
            await cluster.write_attributes({0x0017: 0x02})  # Enter calibration
            cluster.write_attributes.assert_called_once()
    """
    cluster = MagicMock()
    cluster.cluster_id = 0x0102
    cluster.name = "WindowCovering"

    # Mock endpoint
    cluster.endpoint = MagicMock()
    cluster.endpoint.endpoint_id = 2
    cluster.endpoint.device = MagicMock()

    # Mock async methods with sensible defaults
    cluster.write_attributes = AsyncMock(return_value=[{}])
    cluster.read_attributes = AsyncMock(return_value=[{0x0008: 50}])  # position=50
    cluster.command = AsyncMock()

    # Mock commands
    cluster.up_open = AsyncMock()
    cluster.down_close = AsyncMock()
    cluster.stop = AsyncMock()
    cluster.go_to_lift_percentage = AsyncMock()
    cluster.go_to_tilt_percentage = AsyncMock()

    return cluster


@pytest.fixture
def mock_level_control_cluster():
    """Mock LevelControl cluster for D1 dimmer testing.

    Returns a MagicMock cluster with:
    - cluster_id = 0x0008 (LevelControl)
    - endpoint.endpoint_id = 1 (D1 uses EP1)
    - Mocked async methods for dimming control
    """
    cluster = MagicMock()
    cluster.cluster_id = 0x0008
    cluster.name = "LevelControl"

    cluster.endpoint = MagicMock()
    cluster.endpoint.endpoint_id = 1

    cluster.write_attributes = AsyncMock(return_value=[{}])
    cluster.read_attributes = AsyncMock(return_value=[{0x0000: 128}])  # level=128
    cluster.command = AsyncMock()

    cluster.move_to_level = AsyncMock()
    cluster.move_to_level_with_on_off = AsyncMock()

    return cluster


@pytest.fixture
def mock_on_off_cluster():
    """Mock OnOff cluster for S1 switch testing.

    Returns a MagicMock cluster with:
    - cluster_id = 0x0006 (OnOff)
    - endpoint.endpoint_id = 1 (S1 uses EP1)
    - Mocked async methods for on/off control
    """
    cluster = MagicMock()
    cluster.cluster_id = 0x0006
    cluster.name = "OnOff"

    cluster.endpoint = MagicMock()
    cluster.endpoint.endpoint_id = 1

    cluster.write_attributes = AsyncMock(return_value=[{}])
    cluster.read_attributes = AsyncMock(return_value=[{0x0000: True}])  # on=True
    cluster.command = AsyncMock()

    cluster.on = AsyncMock()
    cluster.off = AsyncMock()
    cluster.toggle = AsyncMock()

    return cluster


@pytest.fixture
def mock_device_setup_cluster():
    """Mock DeviceSetup cluster (0xFC00) for input configuration testing.

    Returns a MagicMock cluster for Ubisys manufacturer-specific cluster.
    All Ubisys devices use this cluster on EP232 for input configuration.
    """
    cluster = MagicMock()
    cluster.cluster_id = 0xFC00
    cluster.name = "DeviceSetup"

    cluster.endpoint = MagicMock()
    cluster.endpoint.endpoint_id = 232

    # Mock with manufacturer code auto-injection
    cluster.write_attributes = AsyncMock(return_value=[{}])
    cluster.read_attributes = AsyncMock(
        return_value=[
            {
                0x0000: b"",  # input_configurations
                0x0001: b"\x48\x41\x01\x00\x01\x02\x00\x01\x06\x00\x02\x00",  # input_actions
            }
        ]
    )

    return cluster


@pytest.fixture
def mock_zha_device():
    """Mock ZHA device for testing.

    Returns a MagicMock representing a ZHA device with:
    - IEEE address
    - Manufacturer and model
    - Device name
    - Available clusters

    Example:
        def test_device_info(mock_zha_device):
            assert mock_zha_device.ieee == "00:11:22:33:44:55:66:77"
            assert mock_zha_device.manufacturer == "ubisys"
    """
    device = MagicMock()
    device.ieee = "00:11:22:33:44:55:66:77"
    device.manufacturer = "ubisys"
    device.model = "J1 (5502)"
    device.name = "Test J1"
    device.quirk_applied = True

    return device


# =============================================================================
# CONFIG ENTRY FIXTURES - Mock Home Assistant config entries
# =============================================================================


@pytest.fixture
def mock_j1_config_entry():
    """Mock config entry for J1 window covering device.

    Returns a ConfigEntry with typical J1 configuration.
    """
    return ConfigEntry(
        version=1,
        domain="ubisys",
        title="Test J1",
        data={
            "name": "Test J1",
            "model": "J1",
            "device_ieee": "00:11:22:33:44:55:66:77",
            "device_id": "test_j1_device_id",
            "zha_entity_id": "cover.test_j1",
        },
        options={
            "shade_type": "roller",
            "verbose_info_logging": False,
            "verbose_input_logging": False,
        },
        source="user",
        unique_id="00:11:22:33:44:55:66:77",
    )


@pytest.fixture
def mock_d1_config_entry():
    """Mock config entry for D1 dimmer device.

    Returns a ConfigEntry with typical D1 configuration.
    """
    return ConfigEntry(
        version=1,
        domain="ubisys",
        title="Test D1",
        data={
            "name": "Test D1",
            "model": "D1",
            "device_ieee": "00:11:22:33:44:55:66:88",
            "device_id": "test_d1_device_id",
            "zha_entity_id": "light.test_d1",
        },
        options={
            "verbose_info_logging": False,
            "verbose_input_logging": False,
        },
        source="user",
        unique_id="00:11:22:33:44:55:66:88",
    )


@pytest.fixture
def mock_s1_config_entry():
    """Mock config entry for S1 switch device.

    Returns a ConfigEntry with typical S1 configuration.
    """
    return ConfigEntry(
        version=1,
        domain="ubisys",
        title="Test S1",
        data={
            "name": "Test S1",
            "model": "S1",
            "device_ieee": "00:11:22:33:44:55:66:99",
            "device_id": "test_s1_device_id",
            "zha_entity_id": "switch.test_s1",
        },
        options={
            "verbose_info_logging": False,
            "verbose_input_logging": False,
        },
        source="user",
        unique_id="00:11:22:33:44:55:66:99",
    )


# =============================================================================
# HELPER FIXTURES - Common testing patterns
# =============================================================================


@pytest.fixture
def mock_async_zcl_command():
    """Mock the async_zcl_command helper function.

    This fixture patches the async_zcl_command helper to avoid actual
    Zigbee communication during tests.

    Example:
        async def test_calibration(mock_async_zcl_command):
            # async_zcl_command is automatically mocked
            await some_function_that_uses_zcl_command()
            mock_async_zcl_command.assert_called()
    """
    with patch("custom_components.ubisys.helpers.async_zcl_command") as mock:
        mock.return_value = None
        yield mock


@pytest.fixture
def mock_async_write_and_verify_attrs():
    """Mock the async_write_and_verify_attrs helper function.

    This fixture patches the write-and-verify helper to avoid actual
    Zigbee attribute operations during tests.
    """
    with patch("custom_components.ubisys.helpers.async_write_and_verify_attrs") as mock:
        mock.return_value = None
        yield mock


@pytest.fixture
def mock_hass_states():
    """Mock Home Assistant state changes for monitoring position.

    Useful for testing functions that monitor entity state over time,
    like calibration stall detection.

    Example:
        def test_stall_detection(hass, mock_hass_states):
            # Configure state returns
            mock_hass_states.return_value.attributes = {"current_position": 100}
            position = await wait_for_stall(hass, "cover.test")
            assert position == 100
    """
    mock_state = MagicMock()
    mock_state.state = "open"
    mock_state.attributes = {"current_position": 50}
    return mock_state


# =============================================================================
# PARAMETRIZE HELPERS - Common test parameters
# =============================================================================


# Shade types for parametrized testing
SHADE_TYPES = ["roller", "venetian", "vertical", "cellular"]

# Device models for parametrized testing
DEVICE_MODELS = ["J1", "J1-R", "D1", "D1-R", "S1", "S1-R"]

# Press types for input testing
PRESS_TYPES = ["pressed", "released", "short_press", "long_press", "double_press"]
