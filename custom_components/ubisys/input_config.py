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
    - Not implemented in v2.0
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

# Device-specific endpoint constants
# S1 endpoints
S1_PRIMARY_ENDPOINT = 2  # S1 input 0 source endpoint (Level Control Switch - client)
S1R_PRIMARY_ENDPOINT = 2  # S1-R input 0 source endpoint
S1R_SECONDARY_ENDPOINT = 3  # S1-R input 1 source endpoint


class InputConfigPreset(str, Enum):
    """Available preset configurations for Ubisys devices.

    Each preset represents a common use case with pre-configured
    InputActions micro-code that's ready to write to the device.
    """

    # S1/S1-R presets (power switch)
    S1_TOGGLE = "s1_toggle"  # Toggle on press (default)
    S1_ON_ONLY = "s1_on_only"  # Turn on when pressed, turn off when released
    S1_OFF_ONLY = "s1_off_only"  # Turn off when pressed, turn on when released
    S1_ROCKER = "s1_rocker"  # S1-R: Button 1=on, Button 2=off

    # D1/D1-R presets (dimmer)
    D1_TOGGLE_DIM = "d1_toggle_dim"  # Short=toggle, Long=dim (default)
    D1_UP_DOWN = "d1_up_down"  # Button 1=brighter, Button 2=dimmer
    D1_ROCKER = "d1_rocker"  # Rocker switch: up=brighter, down=dimmer

    # J1 doesn't need presets - default configuration is optimal
    # (Up/Down buttons with stop on release)

    # TODO v2.1: Add scene-only mode presets (buttons trigger automations only,
    # no direct device control). Requires design work on how to handle events
    # without affecting physical outputs.


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

        else:
            raise ValueError(f"Unknown preset: {preset}")


class InputConfigPresets:
    """Manages available presets for each device model.

    This class provides the preset options shown in the UI, along with
    human-readable names and descriptions.
    """

    # Preset metadata (name, description)
    PRESET_INFO = {
        # S1/S1-R presets
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
        # D1/D1-R presets
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
    }

    # Device model to available presets
    MODEL_PRESETS = {
        "S1": [
            InputConfigPreset.S1_TOGGLE,
            InputConfigPreset.S1_ON_ONLY,
            InputConfigPreset.S1_OFF_ONLY,
        ],
        "S1-R": [
            InputConfigPreset.S1_TOGGLE,
            InputConfigPreset.S1_ON_ONLY,
            InputConfigPreset.S1_OFF_ONLY,
            InputConfigPreset.S1_ROCKER,
        ],
        "D1": [
            InputConfigPreset.D1_TOGGLE_DIM,
            InputConfigPreset.D1_UP_DOWN,  # Both D1 and D1-R have 2 inputs
            InputConfigPreset.D1_ROCKER,
        ],
        "D1-R": [
            InputConfigPreset.D1_TOGGLE_DIM,
            InputConfigPreset.D1_UP_DOWN,  # Both D1 and D1-R have 2 inputs
            InputConfigPreset.D1_ROCKER,
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
