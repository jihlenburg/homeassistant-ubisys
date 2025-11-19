from typing import Any

import pytest

from custom_components.ubisys.input_parser import InputActionsParser, TransitionState

syrupy: Any
try:
    import syrupy
except ImportError:
    syrupy = None


def test_input_actions_parse_too_short():
    with pytest.raises(ValueError):
        InputActionsParser.parse(b"\x48\x41\x00")  # 3 bytes only


def test_input_actions_parse_invalid_header():
    # Wrong array type (expect 0x48)
    with pytest.raises(ValueError):
        InputActionsParser.parse(b"\x47\x41\x00\x00")


def test_input_actions_parse_single_entry():
    # Build a minimal valid payload with one entry
    # Header: 0x48 (array), 0x41 (element), count=1 (0x01 0x00)
    header = bytes([0x48, 0x41, 0x01, 0x00])
    # Entry:
    # length=8,
    # input_and_options=0x00 (input=0),
    # transition=0b000111 (0x07) => initial=01 (pressed), final=11 (released) => short_press
    # endpoint=0x02,
    # cluster=0x0006 (OnOff)
    # command_template: command_id=0x02 (Toggle)
    # length=8 implies 3 bytes of command_template after header fields
    # Provide command_id=0x02 and one payload byte 0x00 plus a pad 0x00
    entry = bytes([8, 0x00, 0x07, 0x02, 0x06, 0x00, 0x02, 0x00, 0x00])
    data = header + entry

    actions = InputActionsParser.parse(data)
    assert len(actions) == 1
    a = actions[0]
    assert a.input_number == 0
    assert a.initial_state == TransitionState.PRESSED
    assert a.final_state == TransitionState.RELEASED
    assert a.source_endpoint == 2
    assert a.cluster_id == 0x0006
    assert a.command_id == 0x02


if syrupy:

    def test_input_actions_snapshot(snapshot):
        """Snapshot test for complex input configuration."""
        # Header: Array(0x48), Element(0x41), Count=2
        header = bytes([0x48, 0x41, 0x02, 0x00])

        # Entry 1: Input 0, Short Press (0x07), Toggle (0x0006:0x02)
        # Length=8
        entry1 = bytes([8, 0x00, 0x07, 0x02, 0x06, 0x00, 0x02, 0x00, 0x00])

        # Entry 2: Input 1, Long Press (Initial=KeptPressed=0x02 -> 0x08 in bits), Dim Up (0x0008:0x05)
        # Transition 0x0A (Initial=10, Final=10)
        # Payload: 0x00 (Up), 0x32 (Rate 50)
        # Length=9 (5 header + 1 cmd + 2 payload + 1 pad?) No, length covers all bytes excluding length byte itself.
        # Min 5 bytes: InOpt, Trans, Ep, Clust(2).
        # Cmd(1) + Payload(2) = 3 bytes.
        # Total 5+3 = 8 bytes.
        entry2 = bytes([8, 0x01, 0x0A, 0x02, 0x08, 0x00, 0x05, 0x00, 0x32])

        data = header + entry1 + entry2
        actions = InputActionsParser.parse(data)

        assert actions == snapshot
