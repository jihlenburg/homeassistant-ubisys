import pytest

from custom_components.ubisys.input_parser import InputActionsParser, TransitionState


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
    entry = bytes([8, 0x00, 0x07, 0x02, 0x06, 0x00, 0x02, 0x00])
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

