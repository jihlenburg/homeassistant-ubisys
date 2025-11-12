"""Parse Ubisys InputActions micro-code.

This module parses the manufacturer-specific InputActions attribute (0xFC00:0x0001)
which defines how physical inputs trigger ZigBee commands.

The InputActions format is a binary micro-code that maps:
    (input_number, transition_type) → (endpoint, cluster_id, command_id, payload)

By parsing this, we can correlate observed ZigBee commands back to the physical
input and press type that triggered them.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any

_LOGGER = logging.getLogger(__name__)


class PressType(Enum):
    """Types of physical input press actions."""

    PRESSED = "pressed"  # Button pressed (short press start)
    RELEASED = "released"  # Button released
    SHORT_PRESS = "short_press"  # Complete short press (<1s press→release)
    LONG_PRESS = "long_press"  # Kept pressed >1s
    DOUBLE_PRESS = "double_press"  # Two rapid presses (future)


class TransitionState(Enum):
    """Input transition states from Transition field."""

    IGNORE = 0x00  # Don't care about state
    PRESSED = 0x01  # Pressed (<1s)
    KEPT_PRESSED = 0x02  # Kept pressed (>1s)
    RELEASED = 0x03  # Released


@dataclass
class InputAction:
    """Represents a single InputActions micro-code entry.

    Attributes:
        input_number: Physical input index (0-based)
        input_options: Option flags from upper 4 bits
        transition: Complete transition byte
        initial_state: Starting state of input
        final_state: Ending state of input
        has_alternate: Whether another action alternates with this one
        is_alternate: Whether this is the alternate action
        source_endpoint: Endpoint that sends the command
        cluster_id: Target cluster ID
        command_id: ZCL command ID
        command_payload: Command-specific payload bytes
        press_type: Interpreted press type based on transition
    """

    input_number: int
    input_options: int
    transition: int
    initial_state: TransitionState
    final_state: TransitionState
    has_alternate: bool
    is_alternate: bool
    source_endpoint: int
    cluster_id: int
    command_id: int
    command_payload: bytes
    press_type: PressType

    @property
    def command_signature(self) -> tuple[int, int, int, bytes]:
        """Return a signature tuple that uniquely identifies this command.

        Used for correlating observed commands back to the input action.

        Returns:
            (source_endpoint, cluster_id, command_id, command_payload)
        """
        return (
            self.source_endpoint,
            self.cluster_id,
            self.command_id,
            self.command_payload,
        )

    def __repr__(self) -> str:
        """Return detailed string representation."""
        return (
            f"InputAction(input={self.input_number}, "
            f"press={self.press_type.value}, "
            f"ep={self.source_endpoint}, "
            f"cluster=0x{self.cluster_id:04X}, "
            f"cmd=0x{self.command_id:02X})"
        )


class InputActionsParser:
    """Parser for Ubisys InputActions attribute micro-code.

    The InputActions attribute uses a binary format to encode mappings between
    physical input transitions and ZigBee commands.

    Format:
        - Array type: 0x48 (raw data array)
        - Element type: 0x41 (raw data element)
        - Count: uint16 (little endian)
        - For each entry:
            - Length: uint8 (number of bytes for this entry)
            - InputAndOptions: uint8 (lower 4 bits = input, upper 4 bits = options)
            - Transition: uint8 (state machine definition)
            - Endpoint: uint8 (source endpoint)
            - ClusterID: uint16 (little endian)
            - CommandTemplate: remaining bytes (variable length)
    """

    @staticmethod
    def parse(raw_data: bytes | list[int]) -> list[InputAction]:
        """Parse InputActions raw binary data into structured actions.

        Args:
            raw_data: Raw bytes from InputActions attribute (0xFC00:0x0001)

        Returns:
            List of parsed InputAction objects

        Raises:
            ValueError: If data format is invalid or cannot be parsed

        Example:
            >>> data = bytes([0x41, 0x01, 0x00, 0x06, 0x00, 0x0D, 0x02, 0x06, 0x00, 0x02])
            >>> actions = InputActionsParser.parse(data)
            >>> print(actions[0].input_number)  # 0
            >>> print(actions[0].press_type)  # PressType.SHORT_PRESS
        """
        if isinstance(raw_data, list):
            raw_data = bytes(raw_data)

        if len(raw_data) < 4:
            raise ValueError(
                f"InputActions data too short: {len(raw_data)} bytes "
                "(minimum 4 bytes required)"
            )

        pos = 0

        # Parse array header
        array_type = raw_data[pos]
        if array_type != 0x48:
            raise ValueError(
                f"Invalid array type: 0x{array_type:02X} (expected 0x48)"
            )
        pos += 1

        # Parse element type
        element_type = raw_data[pos]
        if element_type != 0x41:
            raise ValueError(
                f"Invalid element type: 0x{element_type:02X} (expected 0x41)"
            )
        pos += 1

        # Parse count (uint16, little endian)
        if pos + 2 > len(raw_data):
            raise ValueError("Truncated data: cannot read element count")
        count = raw_data[pos] | (raw_data[pos + 1] << 8)
        pos += 2

        _LOGGER.debug("Parsing InputActions: %d entries", count)

        actions = []
        for entry_idx in range(count):
            try:
                action, bytes_read = InputActionsParser._parse_entry(
                    raw_data, pos, entry_idx
                )
                actions.append(action)
                pos += bytes_read
            except Exception as err:
                _LOGGER.warning(
                    "Failed to parse InputAction entry %d: %s", entry_idx, err
                )
                # Try to continue parsing remaining entries
                continue

        _LOGGER.debug("Successfully parsed %d InputActions", len(actions))
        return actions

    @staticmethod
    def _parse_entry(
        raw_data: bytes, pos: int, entry_idx: int
    ) -> tuple[InputAction, int]:
        """Parse a single InputAction entry.

        Args:
            raw_data: Complete raw data bytes
            pos: Current position in raw_data
            entry_idx: Entry index (for logging)

        Returns:
            Tuple of (InputAction, bytes_consumed)

        Raises:
            ValueError: If entry cannot be parsed
        """
        start_pos = pos

        # Read entry length
        if pos >= len(raw_data):
            raise ValueError(f"Entry {entry_idx}: Truncated at length byte")
        entry_length = raw_data[pos]
        pos += 1

        if pos + entry_length > len(raw_data):
            raise ValueError(
                f"Entry {entry_idx}: Length {entry_length} exceeds available data"
            )

        # Parse fields
        if entry_length < 5:  # Minimum: InputAndOptions, Transition, Endpoint, ClusterID
            raise ValueError(
                f"Entry {entry_idx}: Length {entry_length} too short (min 5)"
            )

        # InputAndOptions
        input_and_options = raw_data[pos]
        input_number = input_and_options & 0x0F  # Lower 4 bits
        input_options = (input_and_options >> 4) & 0x0F  # Upper 4 bits
        pos += 1

        # Transition
        transition = raw_data[pos]
        has_alternate = bool(transition & 0x80)
        is_alternate = bool(transition & 0x40)
        initial_state_bits = (transition >> 2) & 0x03
        final_state_bits = transition & 0x03
        pos += 1

        # Convert to enums
        try:
            initial_state = TransitionState(initial_state_bits)
            final_state = TransitionState(final_state_bits)
        except ValueError:
            raise ValueError(
                f"Entry {entry_idx}: Invalid transition states "
                f"(initial={initial_state_bits}, final={final_state_bits})"
            )

        # Determine press type
        press_type = InputActionsParser._determine_press_type(
            initial_state, final_state
        )

        # Endpoint
        source_endpoint = raw_data[pos]
        pos += 1

        # ClusterID (uint16, little endian)
        cluster_id = raw_data[pos] | (raw_data[pos + 1] << 8)
        pos += 2

        # CommandTemplate (remaining bytes)
        command_bytes_length = entry_length - 5
        if command_bytes_length > 0:
            command_template = raw_data[pos : pos + command_bytes_length]
            # First byte is typically the command ID
            command_id = command_template[0]
            command_payload = command_template[1:] if len(command_template) > 1 else b""
        else:
            command_id = 0
            command_payload = b""

        action = InputAction(
            input_number=input_number,
            input_options=input_options,
            transition=transition,
            initial_state=initial_state,
            final_state=final_state,
            has_alternate=has_alternate,
            is_alternate=is_alternate,
            source_endpoint=source_endpoint,
            cluster_id=cluster_id,
            command_id=command_id,
            command_payload=command_payload,
            press_type=press_type,
        )

        bytes_consumed = pos - start_pos
        _LOGGER.debug(
            "Parsed entry %d: %s (consumed %d bytes)", entry_idx, action, bytes_consumed
        )

        return action, bytes_consumed

    @staticmethod
    def _determine_press_type(
        initial_state: TransitionState, final_state: TransitionState
    ) -> PressType:
        """Determine press type from transition states.

        The Ubisys InputActions use state transitions to encode different press types:
        - pressed (01) → released (11): Short press
        - released (11) → pressed (01): Start of press
        - kept pressed (10): Long press
        - ignored (00): Catch-all state

        Args:
            initial_state: Starting state
            final_state: Ending state

        Returns:
            Interpreted press type
        """
        # Short press: pressed → released
        if (
            initial_state == TransitionState.PRESSED
            and final_state == TransitionState.RELEASED
        ):
            return PressType.SHORT_PRESS

        # Long press: kept_pressed state
        if initial_state == TransitionState.KEPT_PRESSED:
            return PressType.LONG_PRESS

        # Press start: released → pressed
        if (
            initial_state == TransitionState.RELEASED
            and final_state == TransitionState.PRESSED
        ):
            return PressType.PRESSED

        # Press release: any → released
        if final_state == TransitionState.RELEASED:
            return PressType.RELEASED

        # Default: treat as generic press
        return PressType.PRESSED


class InputActionRegistry:
    """Registry for correlating observed commands with input actions.

    After parsing InputActions, this registry allows looking up which input
    and press type triggered a given command signature.
    """

    def __init__(self) -> None:
        """Initialize empty registry."""
        self._actions: dict[tuple[int, int, int, bytes], InputAction] = {}

    def register(self, actions: list[InputAction]) -> None:
        """Register parsed InputActions for correlation.

        Args:
            actions: List of parsed InputAction objects
        """
        self._actions.clear()
        for action in actions:
            sig = action.command_signature
            # Handle duplicates by preferring non-alternate actions
            if sig in self._actions and not action.is_alternate:
                continue
            self._actions[sig] = action
            _LOGGER.debug(
                "Registered input %d (%s) → %s",
                action.input_number,
                action.press_type.value,
                sig,
            )

    def lookup(
        self, endpoint: int, cluster: int, command: int, payload: bytes = b""
    ) -> InputAction | None:
        """Look up InputAction by observed command signature.

        Args:
            endpoint: Source endpoint
            cluster: Cluster ID
            command: Command ID
            payload: Command payload bytes

        Returns:
            InputAction if found, None otherwise
        """
        sig = (endpoint, cluster, command, payload)
        action = self._actions.get(sig)

        if action:
            _LOGGER.debug(
                "Matched command (ep=%d, cluster=0x%04X, cmd=0x%02X) → "
                "input %d (%s)",
                endpoint,
                cluster,
                command,
                action.input_number,
                action.press_type.value,
            )
        else:
            _LOGGER.debug(
                "No match for command (ep=%d, cluster=0x%04X, cmd=0x%02X)",
                endpoint,
                cluster,
                command,
            )

        return action

    def get_all_actions(self) -> list[InputAction]:
        """Get all registered actions.

        Returns:
            List of all InputAction objects
        """
        return list(self._actions.values())
