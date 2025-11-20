"""Input configuration management for Ubisys devices.

This module provides tools for generating, reading, and writing InputActions
micro-code to configure physical input behavior on Ubisys devices (J1, D1, S1).

Why This Exists:
    InputActions micro-code is powerful but complex. Users shouldn't need to
    understand binary formats, cluster IDs, or command sequences. This module
    provides:

    1. **Preset-Based Configuration**: Simple choices like "Toggle switch" or
       "Up/Down buttons" that generate correct micro-code automatically.

    2. **Device-Specific Templates**: Each device type (S1, D1, J1) has presets
       tailored to common use cases.

    3. **Micro-Code Generation**: `InputActionBuilder` encapsulates the complex
       binary format, making it impossible to generate invalid configurations.

    4. **Safe Device Writing**: Atomic write operations with automatic rollback
       on failure prevent bricking devices.

Architecture:

    User selects preset in UI
        ↓
    InputConfigPresets.get_preset_config()
        ↓
    InputActionBuilder.build_preset()
        ↓
    Generated micro-code bytes
        ↓
    async_apply_input_config() with rollback
        ↓
    Device configured

Design Philosophy - Progressive Disclosure:

    **Level 1 (Most Users)**: Select preset from dropdown
    - "Toggle switch"
    - "Dimmer with up/down buttons"
    - etc.

    **Level 2 (Advanced Users)**: Customize preset parameters
    - Invert inputs
    - Disable inputs
    - Swap button functions

    **Level 3 (Expert Users)**: Direct micro-code editing
    - Not yet implemented
    - Would require separate advanced mode

InputActions Micro-Code Format:

    Each action is a variable-length entry:

    Byte 0: InputAndOptions
        Bits 0-3: Input number (0-15)
        Bit 4: Invert input (0=normal, 1=inverted)
        Bit 5-7: Reserved

    Byte 1: Transition
        0x00: Pressed (start of press)
        0x01: Released (end of press)
        0x02: Short press (complete short press <1s)
        0x03: Long press (press held >1s)
        0x04: Double press (two rapid presses)
        0x80+: Alternating (e.g., 0x80|0x02 = alternate on each short press)

    Byte 2: SourceEndpoint
        Endpoint to send command from (usually 2 or 3)

    Bytes 3-4: ClusterID (little-endian)
        0x0006: OnOff cluster
        0x0008: LevelControl cluster
        0x0102: WindowCovering cluster

    Byte 5: CommandID
        OnOff: 0x00=off, 0x01=on, 0x02=toggle
        LevelControl: 0x00=move_to_level, 0x01=move, 0x02=step
        WindowCovering: 0x00=up_open, 0x01=down_close, 0x02=stop

    Byte 6: PayloadLength
        Number of payload bytes following (0-255)

    Bytes 7+: Payload (if PayloadLength > 0)
        Command-specific parameters

Example - S1 Toggle Switch:

    Input 0 short press → Toggle:
    [0x00, 0x02, 0x02, 0x06, 0x00, 0x02, 0x00]
     │     │     │     │           │     └─ PayloadLength=0
     │     │     │     │           └─ CommandID=0x02 (toggle)
     │     │     │     └─ ClusterID=0x0006 (OnOff), little-endian
     │     │     └─ SourceEndpoint=2
     │     └─ Transition=0x02 (short press)
     └─ Input=0, not inverted

Example - D1 Dimmer Toggle+Dim:

    Input 0 short press → Toggle:
    [0x00, 0x02, 0x02, 0x06, 0x00, 0x02, 0x00]

    Input 0 long press → Dim up/down (alternating):
    [0x00, 0x83, 0x02, 0x08, 0x00, 0x01, 0x01, 0x00]
     │     │     │     │           │     │     └─ Payload: direction=up
     │     │     │     │           │     └─ PayloadLength=1
     │     │     │     │           └─ CommandID=0x01 (move)
     │     │     │     └─ ClusterID=0x0008 (LevelControl)
     │     │     └─ SourceEndpoint=2
     │     └─ Transition=0x83 (0x80|0x03 = alternating long press)
     └─ Input=0

    [0x00, 0x03, 0x02, 0x08, 0x00, 0x01, 0x01, 0x01]
     Same as above but direction=down (alternates with previous)

See Also:
    - input_parser.py: Parses micro-code (reverse of this module)
    - config_flow.py: UI that uses this module to configure devices
    - docs/ubisys/: Technical reference for each device type
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from .const import UBISYS_MANUFACTURER_CODE
from .helpers import get_device_setup_cluster

_LOGGER = logging.getLogger(__name__)

# InputActions attribute constants
INPUT_ACTIONS_ATTR_ID = 0x0001
INPUT_CONFIGURATIONS_ATTR_ID = 0x0000

# ZigBee cluster IDs
CLUSTER_ON_OFF = 0x0006
CLUSTER_LEVEL_CONTROL = 0x0008
CLUSTER_WINDOW_COVERING = 0x0102

# Common command IDs
# OnOff cluster
CMD_OFF = 0x00
CMD_ON = 0x01
CMD_TOGGLE = 0x02

# LevelControl cluster
CMD_MOVE_TO_LEVEL = 0x00
CMD_MOVE = 0x01
CMD_STEP = 0x02
CMD_STOP = 0x03

# WindowCovering cluster
CMD_UP_OPEN = 0x00
CMD_DOWN_CLOSE = 0x01
CMD_WC_STOP = 0x02

# Transition types
TRANSITION_PRESSED = 0x00
TRANSITION_RELEASED = 0x01
TRANSITION_SHORT_PRESS = 0x02
TRANSITION_LONG_PRESS = 0x03
TRANSITION_DOUBLE_PRESS = 0x04
TRANSITION_ALTERNATING_FLAG = 0x80  # OR with transition type

# =============================================================================
# DEVICE-SPECIFIC ENDPOINT CONSTANTS
# =============================================================================
# Each Ubisys device has controller endpoints (EP2, EP3) that send commands
# when physical inputs are pressed. These are the source endpoints in InputActions.

# S1 endpoints (power switch)
S1_PRIMARY_ENDPOINT = 2  # S1 input 0 source endpoint (Level Control Switch - client)
S1R_PRIMARY_ENDPOINT = 2  # S1-R input 0 source endpoint
S1R_SECONDARY_ENDPOINT = 3  # S1-R input 1 source endpoint

# D1 endpoints (universal dimmer)
# D1 and D1-R both have 2 inputs
D1_PRIMARY_ENDPOINT = 2  # D1 input 0 source endpoint
D1_SECONDARY_ENDPOINT = 3  # D1 input 1 source endpoint

# J1 endpoints (window covering)
# J1 and J1-R both have 2 inputs for up/down control
J1_PRIMARY_ENDPOINT = 2  # J1 input 0 source endpoint (typically "up")
J1_SECONDARY_ENDPOINT = 3  # J1 input 1 source endpoint (typically "down")


class InputConfigPreset(str, Enum):
    """Available preset configurations for Ubisys devices.

    Each preset represents a common use case with pre-configured
    InputActions micro-code that's ready to write to the device.

    Preset Design Philosophy:
        - Cover 90% of use cases with simple, tested configurations
        - Provide DECOUPLED option for full Home Assistant control
        - Use descriptive names that match physical switch behavior

    Adding New Presets:
        1. Add enum value here
        2. Add to build_preset() in InputActionBuilder
        3. Add to PRESET_INFO with name and description
        4. Add to MODEL_PRESETS for appropriate device models
        5. Add translation in strings.json
    """

    # -------------------------------------------------------------------------
    # S1/S1-R presets (power switch)
    # -------------------------------------------------------------------------
    S1_TOGGLE = "s1_toggle"  # Toggle on press (default)
    S1_ON_ONLY = "s1_on_only"  # Turn on when pressed, turn off when released
    S1_OFF_ONLY = "s1_off_only"  # Turn off when pressed, turn on when released
    S1_ROCKER = "s1_rocker"  # S1-R: Button 1=on, Button 2=off
    S1_TOGGLE_DIM = "s1_toggle_dim"  # Short=toggle, Long=dim (dimmer control)
    S1_UP_DOWN = "s1_up_down"  # S1-R: Button 1=brighter, Button 2=dimmer
    S1_DECOUPLED = "s1_decoupled"  # No local control, events only

    # -------------------------------------------------------------------------
    # D1/D1-R presets (universal dimmer)
    # -------------------------------------------------------------------------
    D1_TOGGLE_DIM = "d1_toggle_dim"  # Short=toggle, Long=dim (default)
    D1_UP_DOWN = "d1_up_down"  # Button 1=brighter, Button 2=dimmer
    D1_ROCKER = "d1_rocker"  # Rocker switch: up=brighter, down=dimmer
    D1_STEP = "d1_step"  # Step dimming for latching switches
    D1_DECOUPLED = "d1_decoupled"  # No local control, events only

    # -------------------------------------------------------------------------
    # J1/J1-R presets (window covering)
    # -------------------------------------------------------------------------
    # J1 has 2 inputs controlling a window covering (blinds/shades)
    # Uses WindowCovering cluster (0x0102) with Up/Down/Stop commands
    J1_COVER_ROCKER = "j1_cover_rocker"  # Button 1=up, Button 2=down (default)
    J1_TOGGLE = "j1_toggle"  # Single button cycles: open→stop→close→stop
    J1_ALTERNATING = "j1_alternating"  # Alternating up/down for latching switches
    J1_DECOUPLED = "j1_decoupled"  # No local control, events only


@dataclass
class InputAction:
    """Represents a single InputActions micro-code entry.

    This is the building block for generating micro-code. Multiple actions
    are concatenated to form the complete InputActions attribute value.

    Attributes:
        input_number: Physical input number (0-15)
        inverted: Whether input logic is inverted
        transition: Transition type (pressed, released, short_press, etc.)
        alternating: Whether this alternates with next action
        source_endpoint: Endpoint to send command from
        cluster_id: ZigBee cluster ID
        command_id: Command ID within cluster
        payload: Command payload bytes (empty for most commands)
    """

    input_number: int
    inverted: bool
    transition: int
    alternating: bool
    source_endpoint: int
    cluster_id: int
    command_id: int
    payload: bytes = b""

    def to_bytes(self) -> bytes:
        """Convert this action to micro-code bytes.

        Returns:
            Micro-code bytes for this action

        Example:
            >>> action = InputAction(
            ...     input_number=0, inverted=False,
            ...     transition=TRANSITION_SHORT_PRESS, alternating=False,
            ...     source_endpoint=2, cluster_id=CLUSTER_ON_OFF,
            ...     command_id=CMD_TOGGLE, payload=b""
            ... )
            >>> action.to_bytes()
            b'\\x00\\x02\\x02\\x06\\x00\\x02\\x00'
        """
        # Byte 0: InputAndOptions
        input_and_options = self.input_number & 0x0F
        if self.inverted:
            input_and_options |= 0x10

        # Byte 1: Transition
        transition = self.transition
        if self.alternating:
            transition |= TRANSITION_ALTERNATING_FLAG

        # Bytes 2: SourceEndpoint
        source_endpoint = self.source_endpoint

        # Bytes 3-4: ClusterID (little-endian)
        cluster_lo = self.cluster_id & 0xFF
        cluster_hi = (self.cluster_id >> 8) & 0xFF

        # Byte 5: CommandID
        command_id = self.command_id

        # Byte 6: PayloadLength
        payload_length = len(self.payload)

        # Build bytes
        result = bytes(
            [
                input_and_options,
                transition,
                source_endpoint,
                cluster_lo,
                cluster_hi,
                command_id,
                payload_length,
            ]
        )

        # Append payload if present
        if self.payload:
            result += self.payload

        return result


class InputActionBuilder:
    """Builder for generating InputActions micro-code.

    This class provides methods for generating common action patterns
    without needing to understand the micro-code format details.

    Example Usage:
        >>> builder = InputActionBuilder()
        >>>
        >>> # Generate S1 toggle switch configuration
        >>> actions = builder.build_simple_toggle(input_number=0, endpoint=2)
        >>> micro_code = b"".join(a.to_bytes() for a in actions)
        >>>
        >>> # Generate D1 dimmer with toggle+dim
        >>> actions = builder.build_dimmer_toggle_dim(
        ...     input_number=0, endpoint=2
        ... )
        >>> micro_code = b"".join(a.to_bytes() for a in actions)
    """

    def build_simple_toggle(
        self,
        input_number: int,
        endpoint: int,
        inverted: bool = False,
    ) -> list[InputAction]:
        """Build simple toggle action (short press = toggle).

        This is the most common configuration for switches. Each short
        press toggles the output on/off.

        Args:
            input_number: Input number (0-15)
            endpoint: Source endpoint (usually 2)
            inverted: Whether to invert input logic

        Returns:
            List with single toggle action

        Example:
            Use for S1 toggle switch, or D1 button 2 as simple toggle.
        """
        return [
            InputAction(
                input_number=input_number,
                inverted=inverted,
                transition=TRANSITION_SHORT_PRESS,
                alternating=False,
                source_endpoint=endpoint,
                cluster_id=CLUSTER_ON_OFF,
                command_id=CMD_TOGGLE,
                payload=b"",
            )
        ]

    def build_on_off_rocker(
        self,
        input_number: int,
        endpoint: int,
        press_for_on: bool = True,
        inverted: bool = False,
    ) -> list[InputAction]:
        """Build rocker switch (press=on, release=off or vice versa).

        This configuration turns the output on when pressed and off when
        released (or the reverse).

        Args:
            input_number: Input number (0-15)
            endpoint: Source endpoint
            press_for_on: True = press turns on, False = press turns off
            inverted: Whether to invert input logic

        Returns:
            List with two actions (pressed + released)

        Example:
            S1 configured as rocker (press=on, release=off).
        """
        if press_for_on:
            press_cmd = CMD_ON
            release_cmd = CMD_OFF
        else:
            press_cmd = CMD_OFF
            release_cmd = CMD_ON

        return [
            InputAction(
                input_number=input_number,
                inverted=inverted,
                transition=TRANSITION_PRESSED,
                alternating=False,
                source_endpoint=endpoint,
                cluster_id=CLUSTER_ON_OFF,
                command_id=press_cmd,
                payload=b"",
            ),
            InputAction(
                input_number=input_number,
                inverted=inverted,
                transition=TRANSITION_RELEASED,
                alternating=False,
                source_endpoint=endpoint,
                cluster_id=CLUSTER_ON_OFF,
                command_id=release_cmd,
                payload=b"",
            ),
        ]

    def build_dimmer_toggle_dim(
        self,
        input_number: int,
        endpoint: int,
        inverted: bool = False,
    ) -> list[InputAction]:
        """Build dimmer with toggle+dim (default D1 configuration).

        This is the most common dimmer configuration:
        - Short press: Toggle on/off
        - Long press: Dim up/down (alternating)

        Args:
            input_number: Input number (0-15)
            endpoint: Source endpoint (usually 2 or 3)
            inverted: Whether to invert input logic

        Returns:
            List with three actions (short press + alternating long presses)

        Example:
            D1 default configuration - single button controls everything.
        """
        return [
            # Short press = toggle
            InputAction(
                input_number=input_number,
                inverted=inverted,
                transition=TRANSITION_SHORT_PRESS,
                alternating=False,
                source_endpoint=endpoint,
                cluster_id=CLUSTER_ON_OFF,
                command_id=CMD_TOGGLE,
                payload=b"",
            ),
            # Long press = dim up (alternating)
            InputAction(
                input_number=input_number,
                inverted=inverted,
                transition=TRANSITION_LONG_PRESS,
                alternating=True,
                source_endpoint=endpoint,
                cluster_id=CLUSTER_LEVEL_CONTROL,
                command_id=CMD_MOVE,
                payload=b"\x00",  # Direction: up
            ),
            # Long press = dim down (alternates with previous)
            InputAction(
                input_number=input_number,
                inverted=inverted,
                transition=TRANSITION_LONG_PRESS,
                alternating=False,
                source_endpoint=endpoint,
                cluster_id=CLUSTER_LEVEL_CONTROL,
                command_id=CMD_MOVE,
                payload=b"\x01",  # Direction: down
            ),
        ]

    def build_dimmer_up_down(
        self,
        input_up: int,
        input_down: int,
        endpoint_up: int,
        endpoint_down: int,
        inverted: bool = False,
    ) -> list[InputAction]:
        """Build dimmer with separate up/down buttons (D1-R configuration).

        This configuration uses two buttons:
        - Button 1: Short=on, Long=dim up
        - Button 2: Short=off, Long=dim down

        Args:
            input_up: Input number for "up" button (usually 0)
            input_down: Input number for "down" button (usually 1)
            endpoint_up: Endpoint for up button (usually 2)
            endpoint_down: Endpoint for down button (usually 3)
            inverted: Whether to invert input logic

        Returns:
            List with four actions (2 per button)

        Example:
            D1-R with two push buttons for precise dimming control.
        """
        return [
            # Button 1 short press = on
            InputAction(
                input_number=input_up,
                inverted=inverted,
                transition=TRANSITION_SHORT_PRESS,
                alternating=False,
                source_endpoint=endpoint_up,
                cluster_id=CLUSTER_ON_OFF,
                command_id=CMD_ON,
                payload=b"",
            ),
            # Button 1 long press = dim up
            InputAction(
                input_number=input_up,
                inverted=inverted,
                transition=TRANSITION_LONG_PRESS,
                alternating=False,
                source_endpoint=endpoint_up,
                cluster_id=CLUSTER_LEVEL_CONTROL,
                command_id=CMD_MOVE,
                payload=b"\x00",  # Direction: up
            ),
            # Button 2 short press = off
            InputAction(
                input_number=input_down,
                inverted=inverted,
                transition=TRANSITION_SHORT_PRESS,
                alternating=False,
                source_endpoint=endpoint_down,
                cluster_id=CLUSTER_ON_OFF,
                command_id=CMD_OFF,
                payload=b"",
            ),
            # Button 2 long press = dim down
            InputAction(
                input_number=input_down,
                inverted=inverted,
                transition=TRANSITION_LONG_PRESS,
                alternating=False,
                source_endpoint=endpoint_down,
                cluster_id=CLUSTER_LEVEL_CONTROL,
                command_id=CMD_MOVE,
                payload=b"\x01",  # Direction: down
            ),
        ]

    def build_dimmer_step(
        self,
        input_number: int,
        endpoint: int,
        step_size: int = 32,
        inverted: bool = False,
    ) -> list[InputAction]:
        """Build step dimming for latching switches (single button dimmer control).

        This preset is specifically designed for latching switches (push-on/push-off
        switches that stay in position after pressing). Unlike momentary switches
        where you can "hold to dim", latching switches require a different approach
        using discrete brightness steps.

        How it works:
        - Press 1: Step brightness UP by step_size
        - Press 2: Step brightness DOWN by step_size
        - (cycle repeats)

        Each press alternates between stepping up and stepping down. This provides
        fine-grained control over brightness without needing to hold a button.

        Why step_size=32?
        - ZigBee brightness range is 0-254 (8-bit)
        - step_size=32 gives ~8 steps from min to max (254/32 ≈ 8)
        - This balances precision with speed of adjustment
        - Users can reach any brightness in 4 presses maximum

        Technical details:
        - Uses LevelControl cluster (0x0008) step command (0x02)
        - Step command payload: [mode, step_size, transition_time_low, transition_time_high]
        - mode=0x00 for up, mode=0x01 for down
        - transition_time=0 for immediate change

        Args:
            input_number: Input number (0-15)
            endpoint: Source endpoint (usually 2)
            step_size: Brightness step amount (1-254, default 32 = ~12.5% per step)
            inverted: Whether to invert input logic

        Returns:
            List with two alternating actions (step up, step down)

        Example:
            A user with a latching wall switch controlling a D1 dimmer:
            - Current brightness: 50%
            - Press switch: brightness increases to ~62.5%
            - Press switch again: brightness decreases to ~50%
            - Continue pressing to fine-tune brightness

        Use case:
            Install a latching push switch (push-on/push-off) to control a D1
            dimmer. Each press adjusts brightness without needing to hold.
        """
        return [
            # Step UP (first press in cycle, alternating)
            # Increases brightness by step_size
            InputAction(
                input_number=input_number,
                inverted=inverted,
                transition=TRANSITION_SHORT_PRESS,
                alternating=True,
                source_endpoint=endpoint,
                cluster_id=CLUSTER_LEVEL_CONTROL,
                command_id=CMD_STEP,
                # Payload: [mode=up, step_size, transition_time_low, transition_time_high]
                payload=bytes([0x00, step_size, 0x00, 0x00]),
            ),
            # Step DOWN (second press in cycle, ends alternation)
            # Decreases brightness by step_size
            InputAction(
                input_number=input_number,
                inverted=inverted,
                transition=TRANSITION_SHORT_PRESS,
                alternating=False,  # End of cycle
                source_endpoint=endpoint,
                cluster_id=CLUSTER_LEVEL_CONTROL,
                command_id=CMD_STEP,
                # Payload: [mode=down, step_size, transition_time_low, transition_time_high]
                payload=bytes([0x01, step_size, 0x00, 0x00]),
            ),
        ]

    # -------------------------------------------------------------------------
    # J1 Window Covering Builder Functions
    # -------------------------------------------------------------------------
    # These functions generate InputActions for window covering control using
    # the WindowCovering cluster (0x0102) with Up/Down/Stop commands.

    def build_cover_rocker(
        self,
        input_up: int,
        input_down: int,
        endpoint_up: int,
        endpoint_down: int,
        inverted: bool = False,
    ) -> list[InputAction]:
        """Build window covering with separate up/down buttons (default J1 configuration).

        This is the most common window covering configuration:
        - Button 1 (input_up): Press=up/open, Release=stop
        - Button 2 (input_down): Press=down/close, Release=stop

        This allows precise control - the covering moves while the button is held
        and stops when released.

        Args:
            input_up: Input number for "up" button (usually 0)
            input_down: Input number for "down" button (usually 1)
            endpoint_up: Endpoint for up button (usually 2)
            endpoint_down: Endpoint for down button (usually 3)
            inverted: Whether to invert input logic

        Returns:
            List with four actions (pressed + released for each button)

        Example:
            J1 with two momentary push buttons for blind control:
            - Top button: opens blind while pressed
            - Bottom button: closes blind while pressed
        """
        return [
            # Button 1 pressed = up/open
            InputAction(
                input_number=input_up,
                inverted=inverted,
                transition=TRANSITION_PRESSED,
                alternating=False,
                source_endpoint=endpoint_up,
                cluster_id=CLUSTER_WINDOW_COVERING,
                command_id=CMD_UP_OPEN,
                payload=b"",
            ),
            # Button 1 released = stop
            InputAction(
                input_number=input_up,
                inverted=inverted,
                transition=TRANSITION_RELEASED,
                alternating=False,
                source_endpoint=endpoint_up,
                cluster_id=CLUSTER_WINDOW_COVERING,
                command_id=CMD_WC_STOP,
                payload=b"",
            ),
            # Button 2 pressed = down/close
            InputAction(
                input_number=input_down,
                inverted=inverted,
                transition=TRANSITION_PRESSED,
                alternating=False,
                source_endpoint=endpoint_down,
                cluster_id=CLUSTER_WINDOW_COVERING,
                command_id=CMD_DOWN_CLOSE,
                payload=b"",
            ),
            # Button 2 released = stop
            InputAction(
                input_number=input_down,
                inverted=inverted,
                transition=TRANSITION_RELEASED,
                alternating=False,
                source_endpoint=endpoint_down,
                cluster_id=CLUSTER_WINDOW_COVERING,
                command_id=CMD_WC_STOP,
                payload=b"",
            ),
        ]

    def build_cover_toggle(
        self,
        input_number: int,
        endpoint: int,
        inverted: bool = False,
    ) -> list[InputAction]:
        """Build window covering with single toggle button (cycle through states).

        This configuration uses one button to cycle through:
        - Press 1: Open (up)
        - Press 2: Stop
        - Press 3: Close (down)
        - Press 4: Stop
        - (repeat)

        This is achieved using alternating actions that cycle through 4 states.

        Args:
            input_number: Input number (0-15)
            endpoint: Source endpoint (usually 2)
            inverted: Whether to invert input logic

        Returns:
            List with four alternating actions for the state cycle

        Example:
            Single-button control for window covering - each press advances
            through the open→stop→close→stop cycle.
        """
        return [
            # Short press 1 = up/open (alternating, starts cycle)
            InputAction(
                input_number=input_number,
                inverted=inverted,
                transition=TRANSITION_SHORT_PRESS,
                alternating=True,
                source_endpoint=endpoint,
                cluster_id=CLUSTER_WINDOW_COVERING,
                command_id=CMD_UP_OPEN,
                payload=b"",
            ),
            # Short press 2 = stop (alternating)
            InputAction(
                input_number=input_number,
                inverted=inverted,
                transition=TRANSITION_SHORT_PRESS,
                alternating=True,
                source_endpoint=endpoint,
                cluster_id=CLUSTER_WINDOW_COVERING,
                command_id=CMD_WC_STOP,
                payload=b"",
            ),
            # Short press 3 = down/close (alternating)
            InputAction(
                input_number=input_number,
                inverted=inverted,
                transition=TRANSITION_SHORT_PRESS,
                alternating=True,
                source_endpoint=endpoint,
                cluster_id=CLUSTER_WINDOW_COVERING,
                command_id=CMD_DOWN_CLOSE,
                payload=b"",
            ),
            # Short press 4 = stop (alternating, completes cycle)
            InputAction(
                input_number=input_number,
                inverted=inverted,
                transition=TRANSITION_SHORT_PRESS,
                alternating=False,  # Last in cycle, no alternating flag
                source_endpoint=endpoint,
                cluster_id=CLUSTER_WINDOW_COVERING,
                command_id=CMD_WC_STOP,
                payload=b"",
            ),
        ]

    def build_cover_alternating(
        self,
        input_number: int,
        endpoint: int,
        inverted: bool = False,
    ) -> list[InputAction]:
        """Build alternating up/down for latching switches (single button cover control).

        This preset is specifically designed for latching switches (push-on/push-off
        switches that stay in position after pressing). Unlike J1_TOGGLE which has
        a 4-state cycle (open→stop→close→stop), this preset uses a simpler 2-state
        alternation between up and down.

        How it works:
        - Press 1: Send up_open command (covering opens)
        - Press 2: Send down_close command (covering closes)
        - (cycle repeats)

        Each press alternates between opening and closing. The covering stops
        automatically when it reaches its limit. To stop mid-movement, press again
        to reverse direction.

        Why this is better than J1_TOGGLE for latching switches:
        - Only 2 presses per cycle (not 4)
        - More intuitive - press to go up, press again to go down
        - Faster to reach desired position
        - Covering stops naturally at limits

        Why no explicit stop command?
        - Latching switches can't easily "tap" for stop (no double-press timing)
        - Reversing direction effectively stops movement momentarily
        - The covering will stop at its calibrated limits
        - Users can fine-tune with alternating presses

        Technical details:
        - Uses WindowCovering cluster (0x0102)
        - up_open command (0x00) moves covering toward open position
        - down_close command (0x01) moves covering toward closed position

        Args:
            input_number: Input number (0-15)
            endpoint: Source endpoint (usually 2)
            inverted: Whether to invert input logic

        Returns:
            List with two alternating actions (up_open, down_close)

        Example:
            A user with a latching wall switch controlling J1 blinds:
            - Blinds are closed
            - Press switch: blinds start opening
            - Press switch while moving: blinds start closing
            - Blinds stop automatically at limit

        Use case:
            Install a latching push switch (push-on/push-off) to control J1
            window covering. Each press reverses direction for simple control.
        """
        return [
            # Open/Up (first press in cycle, alternating)
            # Starts covering movement toward open position
            InputAction(
                input_number=input_number,
                inverted=inverted,
                transition=TRANSITION_SHORT_PRESS,
                alternating=True,
                source_endpoint=endpoint,
                cluster_id=CLUSTER_WINDOW_COVERING,
                command_id=CMD_UP_OPEN,
                payload=b"",
            ),
            # Close/Down (second press in cycle, ends alternation)
            # Starts covering movement toward closed position
            InputAction(
                input_number=input_number,
                inverted=inverted,
                transition=TRANSITION_SHORT_PRESS,
                alternating=False,  # End of cycle
                source_endpoint=endpoint,
                cluster_id=CLUSTER_WINDOW_COVERING,
                command_id=CMD_DOWN_CLOSE,
                payload=b"",
            ),
        ]

    def build_preset(
        self,
        preset: InputConfigPreset,
        model: str,
    ) -> list[InputAction]:
        """Build actions for a preset configuration.

        This is the high-level interface used by the config flow UI.
        User selects a preset, this generates the appropriate micro-code.

        Args:
            preset: Preset to build
            model: Device model (e.g., "S1", "S1-R", "D1", "D1-R")

        Returns:
            List of InputActions for this preset

        Raises:
            ValueError: If preset is not valid for this device model

        Example:
            >>> builder = InputActionBuilder()
            >>> actions = builder.build_preset(
            ...     InputConfigPreset.D1_TOGGLE_DIM, "D1"
            ... )
            >>> micro_code = b"".join(a.to_bytes() for a in actions)
        """
        # S1 presets
        if preset == InputConfigPreset.S1_TOGGLE:
            if model not in ("S1", "S1-R"):
                raise ValueError(f"Preset {preset} not valid for {model}")
            return self.build_simple_toggle(input_number=0, endpoint=2)

        elif preset == InputConfigPreset.S1_ON_ONLY:
            if model not in ("S1", "S1-R"):
                raise ValueError(f"Preset {preset} not valid for {model}")
            return self.build_on_off_rocker(
                input_number=0, endpoint=2, press_for_on=True
            )

        elif preset == InputConfigPreset.S1_OFF_ONLY:
            if model not in ("S1", "S1-R"):
                raise ValueError(f"Preset {preset} not valid for {model}")
            return self.build_on_off_rocker(
                input_number=0, endpoint=2, press_for_on=False
            )

        elif preset == InputConfigPreset.S1_ROCKER:
            if model != "S1-R":
                raise ValueError(f"Preset {preset} requires S1-R (dual input)")
            # Button 1 = on, Button 2 = off
            return [
                InputAction(
                    input_number=0,
                    inverted=False,
                    transition=TRANSITION_SHORT_PRESS,
                    alternating=False,
                    source_endpoint=S1R_PRIMARY_ENDPOINT,  # Use constant (endpoint 2)
                    cluster_id=CLUSTER_ON_OFF,
                    command_id=CMD_ON,
                    payload=b"",
                ),
                InputAction(
                    input_number=1,
                    inverted=False,
                    transition=TRANSITION_SHORT_PRESS,
                    alternating=False,
                    source_endpoint=S1R_SECONDARY_ENDPOINT,  # Use constant (endpoint 3)
                    cluster_id=CLUSTER_ON_OFF,
                    command_id=CMD_OFF,
                    payload=b"",
                ),
            ]

        # D1 presets
        elif preset == InputConfigPreset.D1_TOGGLE_DIM:
            if model not in ("D1", "D1-R"):
                raise ValueError(f"Preset {preset} not valid for {model}")
            return self.build_dimmer_toggle_dim(input_number=0, endpoint=2)

        elif preset == InputConfigPreset.D1_UP_DOWN:
            if model not in ("D1", "D1-R"):
                raise ValueError(f"Preset {preset} not valid for {model}")
            # Both D1 and D1-R have 2 inputs
            return self.build_dimmer_up_down(
                input_up=0, input_down=1, endpoint_up=2, endpoint_down=3
            )

        elif preset == InputConfigPreset.D1_ROCKER:
            if model not in ("D1", "D1-R"):
                raise ValueError(f"Preset {preset} not valid for {model}")
            # Rocker switch: up=pressed (dim up), down=released (dim down)
            return [
                InputAction(
                    input_number=0,
                    inverted=False,
                    transition=TRANSITION_PRESSED,
                    alternating=False,
                    source_endpoint=2,
                    cluster_id=CLUSTER_LEVEL_CONTROL,
                    command_id=CMD_MOVE,
                    payload=b"\x00",  # Up
                ),
                InputAction(
                    input_number=0,
                    inverted=False,
                    transition=TRANSITION_RELEASED,
                    alternating=False,
                    source_endpoint=2,
                    cluster_id=CLUSTER_LEVEL_CONTROL,
                    command_id=CMD_STOP,
                    payload=b"",
                ),
            ]

        elif preset == InputConfigPreset.D1_STEP:
            if model not in ("D1", "D1-R"):
                raise ValueError(f"Preset {preset} not valid for {model}")
            # Step dimming for latching switches (push-on/push-off)
            # Each press alternates between step up and step down
            # Ideal when "hold to dim" isn't possible
            return self.build_dimmer_step(
                input_number=0,
                endpoint=D1_PRIMARY_ENDPOINT,
            )

        # -------------------------------------------------------------------------
        # DECOUPLED presets - No local control, events only for HA automations
        # -------------------------------------------------------------------------
        # These presets generate empty InputActions, meaning physical button presses
        # won't control the device directly. However, press events are still sent
        # to Home Assistant via the input monitoring system, allowing automations
        # to handle all control logic while ensuring devices work when HA is down.

        elif preset == InputConfigPreset.S1_TOGGLE_DIM:
            if model not in ("S1", "S1-R"):
                raise ValueError(f"Preset {preset} not valid for {model}")
            # Same as D1's toggle+dim - makes S1 act as dimmer controller
            # Useful for controlling remote dimmers via group binding
            return self.build_dimmer_toggle_dim(
                input_number=0,
                endpoint=S1_PRIMARY_ENDPOINT,
            )

        elif preset == InputConfigPreset.S1_UP_DOWN:
            if model != "S1-R":
                raise ValueError(f"Preset {preset} requires S1-R (dual input)")
            # S1-R acts as dimmer controller with separate buttons
            # Button 1 = on + dim up, Button 2 = off + dim down
            return self.build_dimmer_up_down(
                input_up=0,
                input_down=1,
                endpoint_up=S1R_PRIMARY_ENDPOINT,
                endpoint_down=S1R_SECONDARY_ENDPOINT,
            )

        elif preset == InputConfigPreset.S1_DECOUPLED:
            if model not in ("S1", "S1-R"):
                raise ValueError(f"Preset {preset} not valid for {model}")
            # Empty actions = no local control, but events still fire to HA
            return []

        elif preset == InputConfigPreset.D1_DECOUPLED:
            if model not in ("D1", "D1-R"):
                raise ValueError(f"Preset {preset} not valid for {model}")
            # Empty actions = no local control, but events still fire to HA
            return []

        # -------------------------------------------------------------------------
        # J1 Window Covering presets
        # -------------------------------------------------------------------------

        elif preset == InputConfigPreset.J1_COVER_ROCKER:
            if model not in ("J1", "J1-R"):
                raise ValueError(f"Preset {preset} not valid for {model}")
            # Two-button control: Button 1=up/open, Button 2=down/close
            # Press and hold = continuous movement, release = stop
            return self.build_cover_rocker(
                input_up=0,
                input_down=1,
                endpoint_up=J1_PRIMARY_ENDPOINT,
                endpoint_down=J1_SECONDARY_ENDPOINT,
            )

        elif preset == InputConfigPreset.J1_TOGGLE:
            if model not in ("J1", "J1-R"):
                raise ValueError(f"Preset {preset} not valid for {model}")
            # Single button cycles: open → stop → close → stop → repeat
            # Uses first input only
            return self.build_cover_toggle(
                input_number=0,
                endpoint=J1_PRIMARY_ENDPOINT,
            )

        elif preset == InputConfigPreset.J1_ALTERNATING:
            if model not in ("J1", "J1-R"):
                raise ValueError(f"Preset {preset} not valid for {model}")
            # Alternating up/down for latching switches (push-on/push-off)
            # Each press alternates between up_open and down_close
            # Simpler than J1_TOGGLE (2 states vs 4 states)
            return self.build_cover_alternating(
                input_number=0,
                endpoint=J1_PRIMARY_ENDPOINT,
            )

        elif preset == InputConfigPreset.J1_DECOUPLED:
            if model not in ("J1", "J1-R"):
                raise ValueError(f"Preset {preset} not valid for {model}")
            # Empty actions = no local control, but events still fire to HA
            return []

        else:
            raise ValueError(f"Unknown preset: {preset}")


class InputConfigPresets:
    """Manages available presets for each device model.

    This class provides the preset options shown in the UI, along with
    human-readable names and descriptions.
    """

    # Preset metadata (name, description)
    # Each preset has a user-friendly name and description shown in the UI.
    # The description should explain what the physical buttons do, not technical details.
    PRESET_INFO = {
        # -------------------------------------------------------------------------
        # S1/S1-R presets (power switch)
        # -------------------------------------------------------------------------
        InputConfigPreset.S1_TOGGLE: (
            "Toggle switch (default)",
            "Each press toggles the output on/off",
        ),
        InputConfigPreset.S1_ON_ONLY: (
            "On when pressed",
            "Turns on when pressed, off when released",
        ),
        InputConfigPreset.S1_OFF_ONLY: (
            "Off when pressed",
            "Turns off when pressed, on when released",
        ),
        InputConfigPreset.S1_ROCKER: (
            "On/Off button pair",
            "Button 1 turns on, Button 2 turns off",
        ),
        InputConfigPreset.S1_TOGGLE_DIM: (
            "Toggle + Dim (dimmer control)",
            "Short press toggles, long press dims up/down",
        ),
        InputConfigPreset.S1_UP_DOWN: (
            "Brightness up/down buttons",
            "Button 1 brightens, Button 2 dims",
        ),
        InputConfigPreset.S1_DECOUPLED: (
            "Decoupled (HA control only)",
            "Buttons send events to HA but don't control output directly",
        ),
        # -------------------------------------------------------------------------
        # D1/D1-R presets (universal dimmer)
        # -------------------------------------------------------------------------
        InputConfigPreset.D1_TOGGLE_DIM: (
            "Toggle + Dim (default)",
            "Short press toggles, long press dims up/down",
        ),
        InputConfigPreset.D1_UP_DOWN: (
            "Separate up/down buttons",
            "Button 1 brightens, Button 2 dims",
        ),
        InputConfigPreset.D1_ROCKER: (
            "Rocker switch (continuous dimming)",
            "Up position dims up, down position dims down",
        ),
        InputConfigPreset.D1_STEP: (
            "Step dimming (latching switch)",
            "Each press steps brightness up or down - ideal for push-on/push-off switches",
        ),
        InputConfigPreset.D1_DECOUPLED: (
            "Decoupled (HA control only)",
            "Buttons send events to HA but don't control output directly",
        ),
        # -------------------------------------------------------------------------
        # J1/J1-R presets (window covering)
        # -------------------------------------------------------------------------
        InputConfigPreset.J1_COVER_ROCKER: (
            "Up/Down buttons (default)",
            "Button 1 opens, Button 2 closes. Release to stop.",
        ),
        InputConfigPreset.J1_TOGGLE: (
            "Single button cycle",
            "Each press cycles: open → stop → close → stop",
        ),
        InputConfigPreset.J1_ALTERNATING: (
            "Alternating up/down (latching switch)",
            "Each press alternates between open and close - ideal for push-on/push-off switches",
        ),
        InputConfigPreset.J1_DECOUPLED: (
            "Decoupled (HA control only)",
            "Buttons send events to HA but don't control covering directly",
        ),
    }

    # Device model to available presets
    # Each device model has a list of available presets in display order.
    # The first preset in each list is the default (marked with "default" in UI).
    MODEL_PRESETS = {
        # -------------------------------------------------------------------------
        # S1/S1-R: Power switch with 1 or 2 inputs
        # -------------------------------------------------------------------------
        "S1": [
            InputConfigPreset.S1_TOGGLE,  # Default: single press toggles
            InputConfigPreset.S1_ON_ONLY,
            InputConfigPreset.S1_OFF_ONLY,
            InputConfigPreset.S1_TOGGLE_DIM,  # Control remote dimmers
            InputConfigPreset.S1_DECOUPLED,  # For advanced HA automations
        ],
        "S1-R": [
            InputConfigPreset.S1_TOGGLE,  # Default: single press toggles
            InputConfigPreset.S1_ON_ONLY,
            InputConfigPreset.S1_OFF_ONLY,
            InputConfigPreset.S1_ROCKER,  # Uses both inputs
            InputConfigPreset.S1_TOGGLE_DIM,  # Control remote dimmers
            InputConfigPreset.S1_UP_DOWN,  # Separate brightness buttons
            InputConfigPreset.S1_DECOUPLED,  # For advanced HA automations
        ],
        # -------------------------------------------------------------------------
        # D1/D1-R: Universal dimmer with 2 inputs
        # -------------------------------------------------------------------------
        "D1": [
            InputConfigPreset.D1_TOGGLE_DIM,  # Default: short=toggle, long=dim
            InputConfigPreset.D1_UP_DOWN,  # Separate brightness buttons
            InputConfigPreset.D1_ROCKER,  # Continuous dimming while held
            InputConfigPreset.D1_STEP,  # Step dimming for latching switches
            InputConfigPreset.D1_DECOUPLED,  # For advanced HA automations
        ],
        "D1-R": [
            InputConfigPreset.D1_TOGGLE_DIM,  # Default: short=toggle, long=dim
            InputConfigPreset.D1_UP_DOWN,  # Separate brightness buttons
            InputConfigPreset.D1_ROCKER,  # Continuous dimming while held
            InputConfigPreset.D1_STEP,  # Step dimming for latching switches
            InputConfigPreset.D1_DECOUPLED,  # For advanced HA automations
        ],
        # -------------------------------------------------------------------------
        # J1/J1-R: Window covering controller with 2 inputs
        # -------------------------------------------------------------------------
        "J1": [
            InputConfigPreset.J1_COVER_ROCKER,  # Default: up/down buttons
            InputConfigPreset.J1_TOGGLE,  # Single button cycle
            InputConfigPreset.J1_ALTERNATING,  # Alternating up/down for latching switches
            InputConfigPreset.J1_DECOUPLED,  # For advanced HA automations
        ],
        "J1-R": [
            InputConfigPreset.J1_COVER_ROCKER,  # Default: up/down buttons
            InputConfigPreset.J1_TOGGLE,  # Single button cycle
            InputConfigPreset.J1_ALTERNATING,  # Alternating up/down for latching switches
            InputConfigPreset.J1_DECOUPLED,  # For advanced HA automations
        ],
    }

    @classmethod
    def get_presets_for_model(cls, model: str) -> list[InputConfigPreset]:
        """Get available presets for a device model.

        Args:
            model: Device model (e.g., "S1", "D1-R")

        Returns:
            List of available presets

        Example:
            >>> InputConfigPresets.get_presets_for_model("S1")
            [
                InputConfigPreset.S1_TOGGLE,
                InputConfigPreset.S1_ON_ONLY,
                InputConfigPreset.S1_OFF_ONLY,
                InputConfigPreset.S1_SCENE,
            ]
        """
        return cls.MODEL_PRESETS.get(model, [])

    @classmethod
    def get_preset_info(cls, preset: InputConfigPreset) -> tuple[str, str]:
        """Get preset name and description.

        Args:
            preset: Preset to get info for

        Returns:
            Tuple of (name, description)

        Example:
            >>> InputConfigPresets.get_preset_info(
            ...     InputConfigPreset.S1_TOGGLE
            ... )
            ("Toggle switch (default)", "Each press toggles the output on/off")
        """
        return cls.PRESET_INFO.get(preset, (str(preset), ""))


async def async_read_input_config(
    hass: HomeAssistant,
    device_ieee: str,
) -> bytes:
    """Read current InputActions configuration from device.

    Args:
        hass: Home Assistant instance
        device_ieee: Device IEEE address

    Returns:
        Raw InputActions micro-code bytes

    Raises:
        HomeAssistantError: If read fails

    Example:
        >>> config = await async_read_input_config(hass, "00:12:4b:...")
        >>> print(f"Current config is {len(config)} bytes")
    """
    _LOGGER.debug("Reading InputActions from %s", device_ieee)

    cluster = await get_device_setup_cluster(hass, device_ieee)
    if not cluster:
        raise HomeAssistantError(f"DeviceSetup cluster not found for {device_ieee}")

    try:
        result = await cluster.read_attributes(
            [INPUT_ACTIONS_ATTR_ID],
            manufacturer=UBISYS_MANUFACTURER_CODE,
        )

        if not result or not isinstance(result, list):
            raise HomeAssistantError("Failed to read InputActions: empty result")

        attributes_dict = result[0]
        if INPUT_ACTIONS_ATTR_ID not in attributes_dict:
            raise HomeAssistantError("InputActions attribute not in read result")

        input_actions_data = attributes_dict[INPUT_ACTIONS_ATTR_ID]

        # Convert to bytes if needed
        if isinstance(input_actions_data, list):
            input_actions_data = bytes(input_actions_data)
        elif not isinstance(input_actions_data, bytes):
            raise HomeAssistantError(
                f"Unexpected InputActions data type: {type(input_actions_data)}"
            )

        _LOGGER.debug(
            "Read %d bytes of InputActions from %s",
            len(input_actions_data),
            device_ieee,
        )

        return input_actions_data

    except Exception as err:
        _LOGGER.error("Failed to read InputActions from %s: %s", device_ieee, err)
        raise HomeAssistantError(
            f"Failed to read InputActions from device: {err}"
        ) from err


async def async_apply_input_config(
    hass: HomeAssistant,
    device_ieee: str,
    input_actions: bytes,
    backup_config: bytes | None = None,
) -> None:
    """Write InputActions configuration to device with rollback support.

    This function implements atomic configuration updates:
    1. Read current configuration (for rollback)
    2. Write new configuration
    3. Read back and verify
    4. If verification fails, restore backup

    Args:
        hass: Home Assistant instance
        device_ieee: Device IEEE address
        input_actions: New InputActions micro-code to write
        backup_config: Optional pre-read backup (saves one read operation)

    Raises:
        HomeAssistantError: If write fails or verification fails

    Example:
        >>> builder = InputActionBuilder()
        >>> actions = builder.build_simple_toggle(0, 2)
        >>> micro_code = b"".join(a.to_bytes() for a in actions)
        >>> await async_apply_input_config(hass, ieee, micro_code)
    """
    from .helpers import is_verbose_info_logging

    _LOGGER.log(
        logging.INFO if is_verbose_info_logging(hass) else logging.DEBUG,
        "Applying InputActions configuration to %s",
        device_ieee,
    )

    cluster = await get_device_setup_cluster(hass, device_ieee)
    if not cluster:
        raise HomeAssistantError(f"DeviceSetup cluster not found for {device_ieee}")

    try:
        # Step 1: Read current config for rollback (if not provided)
        if backup_config is None:
            _LOGGER.debug("Reading current config for backup")
            backup_config = await async_read_input_config(hass, device_ieee)

        _LOGGER.debug(
            "Writing %d bytes of InputActions to %s",
            len(input_actions),
            device_ieee,
        )

        # Step 2: Write new configuration
        result = await cluster.write_attributes(
            {INPUT_ACTIONS_ATTR_ID: input_actions},
            manufacturer=UBISYS_MANUFACTURER_CODE,
        )

        # Check write result
        if not result or not isinstance(result, list):
            raise HomeAssistantError("Write failed: empty result")

        write_status = result[0]
        if INPUT_ACTIONS_ATTR_ID in write_status:
            status_code = write_status[INPUT_ACTIONS_ATTR_ID]
            if status_code != 0:  # 0 = success
                raise HomeAssistantError(f"Write failed with status code {status_code}")

        _LOGGER.debug("Write successful, verifying...")

        # Step 3: Read back and verify
        readback = await async_read_input_config(hass, device_ieee)

        if readback != input_actions:
            _LOGGER.error(
                "Verification failed! Expected %d bytes, read %d bytes",
                len(input_actions),
                len(readback),
            )

            # Step 4: Rollback on verification failure
            _LOGGER.warning("Rolling back to previous configuration")
            await cluster.write_attributes(
                {INPUT_ACTIONS_ATTR_ID: backup_config},
                manufacturer=UBISYS_MANUFACTURER_CODE,
            )

            raise HomeAssistantError(
                "Configuration verification failed - rolled back to previous config"
            )

        _LOGGER.log(
            logging.INFO if is_verbose_info_logging(hass) else logging.DEBUG,
            "✓ InputActions configuration applied successfully",
        )

    except Exception as err:
        _LOGGER.error(
            "Failed to apply InputActions to %s: %s",
            device_ieee,
            err,
            exc_info=True,
        )
        raise HomeAssistantError(f"Failed to apply configuration: {err}") from err
