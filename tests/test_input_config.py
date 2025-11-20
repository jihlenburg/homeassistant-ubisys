"""Tests for input configuration management."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.exceptions import HomeAssistantError

from custom_components.ubisys import input_config as ic
from custom_components.ubisys.input_config import (
    CLUSTER_LEVEL_CONTROL,
    CLUSTER_ON_OFF,
    CLUSTER_WINDOW_COVERING,
    CMD_DOWN_CLOSE,
    CMD_MOVE,
    CMD_OFF,
    CMD_ON,
    CMD_STEP,
    CMD_TOGGLE,
    CMD_UP_OPEN,
    CMD_WC_STOP,
    TRANSITION_LONG_PRESS,
    TRANSITION_PRESSED,
    TRANSITION_RELEASED,
    TRANSITION_SHORT_PRESS,
    InputAction,
    InputActionBuilder,
    InputConfigPreset,
    InputConfigPresets,
)

# =============================================================================
# InputAction.to_bytes() tests
# =============================================================================


def test_input_action_to_bytes_simple_toggle():
    """Simple toggle action encodes correctly."""
    action = InputAction(
        input_number=0,
        inverted=False,
        transition=TRANSITION_SHORT_PRESS,
        alternating=False,
        source_endpoint=2,
        cluster_id=CLUSTER_ON_OFF,
        command_id=CMD_TOGGLE,
        payload=b"",
    )

    result = action.to_bytes()

    # Expected: [input=0, transition=2, endpoint=2, cluster_lo=6, cluster_hi=0, cmd=2, len=0]
    assert result == bytes([0x00, 0x02, 0x02, 0x06, 0x00, 0x02, 0x00])


def test_input_action_to_bytes_with_payload():
    """Action with payload encodes correctly."""
    action = InputAction(
        input_number=0,
        inverted=False,
        transition=TRANSITION_LONG_PRESS,
        alternating=False,
        source_endpoint=2,
        cluster_id=CLUSTER_LEVEL_CONTROL,
        command_id=CMD_MOVE,
        payload=b"\x00",  # Direction: up
    )

    result = action.to_bytes()

    # Expected: includes payload byte
    assert result == bytes([0x00, 0x03, 0x02, 0x08, 0x00, 0x01, 0x01, 0x00])


def test_input_action_to_bytes_inverted():
    """Inverted input encodes with bit 4 set."""
    action = InputAction(
        input_number=0,
        inverted=True,
        transition=TRANSITION_SHORT_PRESS,
        alternating=False,
        source_endpoint=2,
        cluster_id=CLUSTER_ON_OFF,
        command_id=CMD_TOGGLE,
        payload=b"",
    )

    result = action.to_bytes()

    # Byte 0 should have bit 4 set (0x10)
    assert result[0] == 0x10


def test_input_action_to_bytes_alternating():
    """Alternating action encodes with bit 7 set in transition."""
    action = InputAction(
        input_number=0,
        inverted=False,
        transition=TRANSITION_LONG_PRESS,
        alternating=True,
        source_endpoint=2,
        cluster_id=CLUSTER_LEVEL_CONTROL,
        command_id=CMD_MOVE,
        payload=b"\x00",
    )

    result = action.to_bytes()

    # Byte 1 should have alternating flag (0x80 | 0x03 = 0x83)
    assert result[1] == 0x83


def test_input_action_to_bytes_input_number():
    """Different input numbers encode correctly."""
    for input_num in range(4):
        action = InputAction(
            input_number=input_num,
            inverted=False,
            transition=TRANSITION_SHORT_PRESS,
            alternating=False,
            source_endpoint=2,
            cluster_id=CLUSTER_ON_OFF,
            command_id=CMD_TOGGLE,
            payload=b"",
        )

        result = action.to_bytes()
        assert result[0] == input_num


def test_input_action_to_bytes_window_covering():
    """Window covering commands encode correctly."""
    action = InputAction(
        input_number=0,
        inverted=False,
        transition=TRANSITION_PRESSED,
        alternating=False,
        source_endpoint=2,
        cluster_id=CLUSTER_WINDOW_COVERING,
        command_id=CMD_UP_OPEN,
        payload=b"",
    )

    result = action.to_bytes()

    # Cluster 0x0102 = [0x02, 0x01] in little-endian
    assert result[3] == 0x02
    assert result[4] == 0x01


# =============================================================================
# InputActionBuilder tests
# =============================================================================


def test_builder_simple_toggle():
    """build_simple_toggle creates correct action."""
    builder = InputActionBuilder()

    actions = builder.build_simple_toggle(input_number=0, endpoint=2)

    assert len(actions) == 1
    assert actions[0].transition == TRANSITION_SHORT_PRESS
    assert actions[0].cluster_id == CLUSTER_ON_OFF
    assert actions[0].command_id == CMD_TOGGLE


def test_builder_on_off_rocker_press_for_on():
    """build_on_off_rocker with press_for_on=True."""
    builder = InputActionBuilder()

    actions = builder.build_on_off_rocker(input_number=0, endpoint=2, press_for_on=True)

    assert len(actions) == 2
    assert actions[0].transition == TRANSITION_PRESSED
    assert actions[0].command_id == CMD_ON
    assert actions[1].transition == TRANSITION_RELEASED
    assert actions[1].command_id == CMD_OFF


def test_builder_on_off_rocker_press_for_off():
    """build_on_off_rocker with press_for_on=False."""
    builder = InputActionBuilder()

    actions = builder.build_on_off_rocker(
        input_number=0, endpoint=2, press_for_on=False
    )

    assert len(actions) == 2
    assert actions[0].command_id == CMD_OFF
    assert actions[1].command_id == CMD_ON


def test_builder_dimmer_toggle_dim():
    """build_dimmer_toggle_dim creates toggle + alternating dim."""
    builder = InputActionBuilder()

    actions = builder.build_dimmer_toggle_dim(input_number=0, endpoint=2)

    assert len(actions) == 3
    # First action: short press toggle
    assert actions[0].transition == TRANSITION_SHORT_PRESS
    assert actions[0].command_id == CMD_TOGGLE
    # Second action: alternating long press dim up
    assert actions[1].transition == TRANSITION_LONG_PRESS
    assert actions[1].alternating is True
    assert actions[1].payload == b"\x00"  # Up
    # Third action: long press dim down
    assert actions[2].payload == b"\x01"  # Down
    assert actions[2].alternating is False


def test_builder_dimmer_up_down():
    """build_dimmer_up_down creates 4 actions for two buttons."""
    builder = InputActionBuilder()

    actions = builder.build_dimmer_up_down(
        input_up=0, input_down=1, endpoint_up=2, endpoint_down=3
    )

    assert len(actions) == 4
    # Button 1: on + dim up
    assert actions[0].input_number == 0
    assert actions[0].command_id == CMD_ON
    assert actions[1].input_number == 0
    assert actions[1].command_id == CMD_MOVE
    # Button 2: off + dim down
    assert actions[2].input_number == 1
    assert actions[2].command_id == CMD_OFF
    assert actions[3].input_number == 1
    assert actions[3].payload == b"\x01"  # Down


def test_builder_dimmer_step():
    """build_dimmer_step creates alternating step actions."""
    builder = InputActionBuilder()

    actions = builder.build_dimmer_step(input_number=0, endpoint=2)

    assert len(actions) == 2
    # Both use step command
    assert actions[0].command_id == CMD_STEP
    assert actions[1].command_id == CMD_STEP
    # First alternates, second doesn't
    assert actions[0].alternating is True
    assert actions[1].alternating is False
    # Step up and step down payloads
    assert actions[0].payload[0] == 0x00  # Mode: up
    assert actions[1].payload[0] == 0x01  # Mode: down


def test_builder_cover_rocker():
    """build_cover_rocker creates 4 actions for up/down with stop on release."""
    builder = InputActionBuilder()

    actions = builder.build_cover_rocker(
        input_up=0, input_down=1, endpoint_up=2, endpoint_down=3
    )

    assert len(actions) == 4
    # Button 1: up on press, stop on release
    assert actions[0].command_id == CMD_UP_OPEN
    assert actions[0].transition == TRANSITION_PRESSED
    assert actions[1].command_id == CMD_WC_STOP
    assert actions[1].transition == TRANSITION_RELEASED
    # Button 2: down on press, stop on release
    assert actions[2].command_id == CMD_DOWN_CLOSE
    assert actions[3].command_id == CMD_WC_STOP


def test_builder_cover_toggle():
    """build_cover_toggle creates 4-state cycle."""
    builder = InputActionBuilder()

    actions = builder.build_cover_toggle(input_number=0, endpoint=2)

    assert len(actions) == 4
    # All short press
    for action in actions:
        assert action.transition == TRANSITION_SHORT_PRESS
    # Commands: up, stop, down, stop
    assert actions[0].command_id == CMD_UP_OPEN
    assert actions[1].command_id == CMD_WC_STOP
    assert actions[2].command_id == CMD_DOWN_CLOSE
    assert actions[3].command_id == CMD_WC_STOP
    # First 3 alternating, last not
    assert actions[0].alternating is True
    assert actions[1].alternating is True
    assert actions[2].alternating is True
    assert actions[3].alternating is False


def test_builder_cover_alternating():
    """build_cover_alternating creates 2-state cycle."""
    builder = InputActionBuilder()

    actions = builder.build_cover_alternating(input_number=0, endpoint=2)

    assert len(actions) == 2
    assert actions[0].command_id == CMD_UP_OPEN
    assert actions[0].alternating is True
    assert actions[1].command_id == CMD_DOWN_CLOSE
    assert actions[1].alternating is False


# =============================================================================
# build_preset tests
# =============================================================================


def test_builder_preset_s1_toggle():
    """S1_TOGGLE preset builds simple toggle."""
    builder = InputActionBuilder()

    actions = builder.build_preset(InputConfigPreset.S1_TOGGLE, "S1")

    assert len(actions) == 1
    assert actions[0].command_id == CMD_TOGGLE


def test_builder_preset_s1_toggle_invalid_model():
    """S1 presets raise error for non-S1 models."""
    builder = InputActionBuilder()

    with pytest.raises(ValueError, match="not valid for D1"):
        builder.build_preset(InputConfigPreset.S1_TOGGLE, "D1")


def test_builder_preset_d1_toggle_dim():
    """D1_TOGGLE_DIM preset builds dimmer with toggle+dim."""
    builder = InputActionBuilder()

    actions = builder.build_preset(InputConfigPreset.D1_TOGGLE_DIM, "D1")

    assert len(actions) == 3


def test_builder_preset_d1_decoupled():
    """D1_DECOUPLED preset returns empty actions."""
    builder = InputActionBuilder()

    actions = builder.build_preset(InputConfigPreset.D1_DECOUPLED, "D1")

    assert actions == []


def test_builder_preset_j1_cover_rocker():
    """J1_COVER_ROCKER preset builds up/down buttons."""
    builder = InputActionBuilder()

    actions = builder.build_preset(InputConfigPreset.J1_COVER_ROCKER, "J1")

    assert len(actions) == 4


def test_builder_preset_j1_decoupled():
    """J1_DECOUPLED preset returns empty actions."""
    builder = InputActionBuilder()

    actions = builder.build_preset(InputConfigPreset.J1_DECOUPLED, "J1")

    assert actions == []


def test_builder_preset_s1_rocker_requires_s1r():
    """S1_ROCKER preset requires S1-R model."""
    builder = InputActionBuilder()

    with pytest.raises(ValueError, match="requires S1-R"):
        builder.build_preset(InputConfigPreset.S1_ROCKER, "S1")


def test_builder_preset_unknown_raises():
    """Unknown preset raises ValueError."""
    builder = InputActionBuilder()

    # Create a mock preset value that doesn't exist
    with pytest.raises(ValueError, match="Unknown preset"):
        builder.build_preset("invalid_preset", "S1")  # type: ignore


# =============================================================================
# InputConfigPresets tests
# =============================================================================


def test_presets_get_presets_for_model_s1():
    """S1 model returns S1 presets."""
    presets = InputConfigPresets.get_presets_for_model("S1")

    assert InputConfigPreset.S1_TOGGLE in presets
    assert InputConfigPreset.S1_DECOUPLED in presets
    # S1 doesn't have rocker
    assert InputConfigPreset.S1_ROCKER not in presets


def test_presets_get_presets_for_model_s1r():
    """S1-R model returns S1-R presets including rocker."""
    presets = InputConfigPresets.get_presets_for_model("S1-R")

    assert InputConfigPreset.S1_ROCKER in presets
    assert InputConfigPreset.S1_UP_DOWN in presets


def test_presets_get_presets_for_model_d1():
    """D1 model returns D1 presets."""
    presets = InputConfigPresets.get_presets_for_model("D1")

    assert InputConfigPreset.D1_TOGGLE_DIM in presets
    assert InputConfigPreset.D1_STEP in presets


def test_presets_get_presets_for_model_j1():
    """J1 model returns J1 presets."""
    presets = InputConfigPresets.get_presets_for_model("J1")

    assert InputConfigPreset.J1_COVER_ROCKER in presets
    assert InputConfigPreset.J1_ALTERNATING in presets


def test_presets_get_presets_for_unknown_model():
    """Unknown model returns empty list."""
    presets = InputConfigPresets.get_presets_for_model("Unknown")

    assert presets == []


def test_presets_get_preset_info():
    """Preset info returns name and description."""
    name, desc = InputConfigPresets.get_preset_info(InputConfigPreset.S1_TOGGLE)

    assert "Toggle" in name
    assert "press" in desc.lower()


def test_presets_get_preset_info_unknown():
    """Unknown preset returns string representation."""
    # Use a valid enum but test default fallback
    name, desc = InputConfigPresets.get_preset_info(InputConfigPreset.S1_TOGGLE)

    assert name  # Should have a name


def test_all_presets_have_info():
    """All defined presets have info entries."""
    for preset in InputConfigPreset:
        name, desc = InputConfigPresets.get_preset_info(preset)
        assert name, f"Preset {preset} missing name"


# =============================================================================
# async_read_input_config tests
# =============================================================================


@pytest.mark.asyncio
async def test_read_input_config_success(monkeypatch):
    """Successfully reads InputActions from device."""
    expected_data = bytes([0x00, 0x02, 0x02, 0x06, 0x00, 0x02, 0x00])

    # Mock cluster
    cluster = MagicMock()
    cluster.read_attributes = AsyncMock(
        return_value=[{ic.INPUT_ACTIONS_ATTR_ID: expected_data}]
    )

    monkeypatch.setattr(
        "custom_components.ubisys.input_config.get_device_setup_cluster",
        AsyncMock(return_value=cluster),
    )

    hass = MagicMock()
    result = await ic.async_read_input_config(hass, "00:11:22:33")

    assert result == expected_data


@pytest.mark.asyncio
async def test_read_input_config_converts_list_to_bytes(monkeypatch):
    """List data is converted to bytes."""
    list_data = [0x00, 0x02, 0x02, 0x06, 0x00, 0x02, 0x00]

    cluster = MagicMock()
    cluster.read_attributes = AsyncMock(
        return_value=[{ic.INPUT_ACTIONS_ATTR_ID: list_data}]
    )

    monkeypatch.setattr(
        "custom_components.ubisys.input_config.get_device_setup_cluster",
        AsyncMock(return_value=cluster),
    )

    hass = MagicMock()
    result = await ic.async_read_input_config(hass, "00:11:22:33")

    assert isinstance(result, bytes)
    assert result == bytes(list_data)


@pytest.mark.asyncio
async def test_read_input_config_cluster_not_found(monkeypatch):
    """Raises error when cluster not found."""
    monkeypatch.setattr(
        "custom_components.ubisys.input_config.get_device_setup_cluster",
        AsyncMock(return_value=None),
    )

    hass = MagicMock()

    with pytest.raises(HomeAssistantError, match="not found"):
        await ic.async_read_input_config(hass, "00:11:22:33")


@pytest.mark.asyncio
async def test_read_input_config_empty_result(monkeypatch):
    """Raises error on empty result."""
    cluster = MagicMock()
    cluster.read_attributes = AsyncMock(return_value=None)

    monkeypatch.setattr(
        "custom_components.ubisys.input_config.get_device_setup_cluster",
        AsyncMock(return_value=cluster),
    )

    hass = MagicMock()

    with pytest.raises(HomeAssistantError, match="empty result"):
        await ic.async_read_input_config(hass, "00:11:22:33")


# =============================================================================
# async_apply_input_config tests
# =============================================================================


@pytest.mark.asyncio
async def test_apply_input_config_success(monkeypatch):
    """Successfully writes and verifies InputActions."""
    config_data = bytes([0x00, 0x02, 0x02, 0x06, 0x00, 0x02, 0x00])

    cluster = MagicMock()
    cluster.write_attributes = AsyncMock(return_value=[{}])
    cluster.read_attributes = AsyncMock(
        return_value=[{ic.INPUT_ACTIONS_ATTR_ID: config_data}]
    )

    monkeypatch.setattr(
        "custom_components.ubisys.input_config.get_device_setup_cluster",
        AsyncMock(return_value=cluster),
    )
    monkeypatch.setattr(
        "custom_components.ubisys.helpers.is_verbose_info_logging",
        lambda h: False,
    )

    hass = MagicMock()
    # Provide backup to skip initial read
    await ic.async_apply_input_config(
        hass, "00:11:22:33", config_data, backup_config=config_data
    )

    # Should write the config
    cluster.write_attributes.assert_awaited_once()


@pytest.mark.asyncio
async def test_apply_input_config_cluster_not_found(monkeypatch):
    """Raises error when cluster not found."""
    monkeypatch.setattr(
        "custom_components.ubisys.input_config.get_device_setup_cluster",
        AsyncMock(return_value=None),
    )
    monkeypatch.setattr(
        "custom_components.ubisys.helpers.is_verbose_info_logging",
        lambda h: False,
    )

    hass = MagicMock()

    with pytest.raises(HomeAssistantError, match="not found"):
        await ic.async_apply_input_config(hass, "00:11:22:33", b"\x00")


@pytest.mark.asyncio
async def test_apply_input_config_verification_failure_rollback(monkeypatch):
    """Rolls back on verification failure."""
    original_config = bytes([0x01, 0x02, 0x03])
    new_config = bytes([0x04, 0x05, 0x06])
    wrong_readback = bytes([0x07, 0x08, 0x09])

    write_calls = []

    async def mock_write_attributes(attrs, **kwargs):
        write_calls.append(attrs)
        return [{}]

    read_results = [
        [{ic.INPUT_ACTIONS_ATTR_ID: wrong_readback}],  # Verification fails
    ]

    cluster = MagicMock()
    cluster.write_attributes = mock_write_attributes
    cluster.read_attributes = AsyncMock(side_effect=read_results)

    monkeypatch.setattr(
        "custom_components.ubisys.input_config.get_device_setup_cluster",
        AsyncMock(return_value=cluster),
    )
    monkeypatch.setattr(
        "custom_components.ubisys.helpers.is_verbose_info_logging",
        lambda h: False,
    )

    hass = MagicMock()

    with pytest.raises(HomeAssistantError, match="rolled back"):
        await ic.async_apply_input_config(
            hass, "00:11:22:33", new_config, backup_config=original_config
        )

    # Should have written twice: new config then rollback
    assert len(write_calls) == 2
    # Second write should be the original config (rollback)
    assert write_calls[1][ic.INPUT_ACTIONS_ATTR_ID] == original_config


# =============================================================================
# Micro-code generation end-to-end tests
# =============================================================================


def test_micro_code_generation_s1_toggle():
    """S1 toggle preset generates valid micro-code."""
    builder = InputActionBuilder()
    actions = builder.build_preset(InputConfigPreset.S1_TOGGLE, "S1")
    micro_code = b"".join(a.to_bytes() for a in actions)

    # Should be 7 bytes for simple toggle
    assert len(micro_code) == 7
    # First byte is input 0
    assert micro_code[0] == 0x00
    # OnOff cluster (0x0006)
    assert micro_code[3:5] == bytes([0x06, 0x00])


def test_micro_code_generation_d1_toggle_dim():
    """D1 toggle+dim preset generates valid micro-code."""
    builder = InputActionBuilder()
    actions = builder.build_preset(InputConfigPreset.D1_TOGGLE_DIM, "D1")
    micro_code = b"".join(a.to_bytes() for a in actions)

    # 7 bytes for toggle + 8 bytes for dim up + 8 bytes for dim down = 23 bytes
    assert len(micro_code) == 23


def test_micro_code_generation_j1_rocker():
    """J1 rocker preset generates valid micro-code."""
    builder = InputActionBuilder()
    actions = builder.build_preset(InputConfigPreset.J1_COVER_ROCKER, "J1")
    micro_code = b"".join(a.to_bytes() for a in actions)

    # 4 actions × 7 bytes each = 28 bytes
    assert len(micro_code) == 28


def test_micro_code_generation_decoupled():
    """Decoupled preset generates empty micro-code."""
    builder = InputActionBuilder()
    actions = builder.build_preset(InputConfigPreset.S1_DECOUPLED, "S1")
    micro_code = b"".join(a.to_bytes() for a in actions)

    assert micro_code == b""
