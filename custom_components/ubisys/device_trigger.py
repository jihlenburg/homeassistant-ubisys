"""Device automation triggers for Ubisys input events.

This module exposes physical input button presses as device automation triggers
in the Home Assistant UI. Users can create automations that respond to button
presses without needing to understand event structures.

Device Trigger Integration:
    Home Assistant's device automation system provides a user-friendly way to
    create automations based on device events. This module bridges between
    the low-level ubisys_input_event and the high-level automation UI.

Supported Triggers:
    For each physical input on a device, we expose these trigger types:
    - button_N_pressed: Button pressed (start of press)
    - button_N_released: Button released
    - button_N_short_press: Complete short press (<1s)
    - button_N_long_press: Button kept pressed (>1s)

    Where N is the button number (1-based for user friendliness).

Example Automation YAML:
    trigger:
      - platform: device
        domain: ubisys
        device_id: abc123def456
        type: button_1_short_press

Example Automation UI:
    Trigger type: Device
    Device: Bedroom J1
    Trigger: Button 1 short press

Architecture:
    User selects trigger in UI
        ↓
    HA calls async_attach_trigger()
        ↓
    We subscribe to dispatcher signal from input_monitor
        ↓
    Physical button press fires input event
        ↓
    input_monitor fires dispatcher signal
        ↓
    We receive event, check if it matches trigger
        ↓
    Call trigger action if match
        ↓
    User's automation runs
"""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.components.device_automation import DEVICE_TRIGGER_BASE_SCHEMA
from homeassistant.const import CONF_DEVICE_ID, CONF_DOMAIN, CONF_PLATFORM, CONF_TYPE
from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.typing import ConfigType

from .const import (
    ATTR_INPUT_NUMBER,
    ATTR_PRESS_TYPE,
    DOMAIN,
    SIGNAL_INPUT_EVENT,
)
from .helpers import extract_model_from_device

_LOGGER = logging.getLogger(__name__)

# Trigger type constants (these appear in the UI)
TRIGGER_BUTTON_1_PRESSED = "button_1_pressed"
TRIGGER_BUTTON_1_RELEASED = "button_1_released"
TRIGGER_BUTTON_1_SHORT_PRESS = "button_1_short_press"
TRIGGER_BUTTON_1_LONG_PRESS = "button_1_long_press"

TRIGGER_BUTTON_2_PRESSED = "button_2_pressed"
TRIGGER_BUTTON_2_RELEASED = "button_2_released"
TRIGGER_BUTTON_2_SHORT_PRESS = "button_2_short_press"
TRIGGER_BUTTON_2_LONG_PRESS = "button_2_long_press"

# Press type to trigger type mapping (input_number → button_number conversion)
# Maps: (input_number, press_type) → trigger_type
#
# Why This Mapping Exists:
#   Ubisys devices use 0-based input numbers internally (input 0, input 1),
#   but we present them as 1-based button numbers (button 1, button 2) in the UI
#   for user-friendliness. This mapping converts between the two.
#
# Input Events Flow:
#   1. Physical button press on device
#   2. Device sends Zigbee command from controller endpoint
#   3. input_monitor correlates command with InputActions → (input_number, press_type)
#   4. input_monitor fires ubisys_input_event with (input_number, press_type)
#   5. This mapping converts to user-facing trigger type (button_1_short_press, etc.)
#   6. Automation action executes if trigger type matches user's automation
#
# Example:
#   User presses physical button 1 briefly
#   → Device: input 0, short_press
#   → Mapping: (0, "short_press") → TRIGGER_BUTTON_1_SHORT_PRESS
#   → UI: "Button 1 short press"
#
PRESS_TYPE_TO_TRIGGER = {
    # Input 0 (Button 1) - First physical input
    (0, "pressed"): TRIGGER_BUTTON_1_PRESSED,        # Press started
    (0, "released"): TRIGGER_BUTTON_1_RELEASED,      # Press ended
    (0, "short_press"): TRIGGER_BUTTON_1_SHORT_PRESS, # Brief press (<1s)
    (0, "long_press"): TRIGGER_BUTTON_1_LONG_PRESS,   # Extended press (>1s)
    # Input 1 (Button 2) - Second physical input (D1, J1, S1-R only)
    (1, "pressed"): TRIGGER_BUTTON_2_PRESSED,
    (1, "released"): TRIGGER_BUTTON_2_RELEASED,
    (1, "short_press"): TRIGGER_BUTTON_2_SHORT_PRESS,
    (1, "long_press"): TRIGGER_BUTTON_2_LONG_PRESS,
}

# Device model to available triggers mapping
# Defines which triggers are available for each device model
#
# Why Different Models Have Different Triggers:
#   The number of available triggers depends on the number of physical inputs:
#   - 1 input device (S1): 4 triggers (button 1: pressed/released/short/long)
#   - 2 input devices (J1, D1, S1-R): 8 triggers (buttons 1 & 2, each with 4 types)
#
# Hardware Differences:
#   - J1/J1-R: 2 inputs (same, "-R" is just DIN rail mount)
#   - D1/D1-R: 2 inputs (same, "-R" is just DIN rail mount)
#   - S1: 1 input (flush mount)
#   - S1-R: 2 inputs (DIN rail, different hardware from S1)
#
# Why Expose All Press Types:
#   Different press types enable different automation patterns:
#   - "pressed": Instant response when button is pushed down
#   - "released": Action when button is let go
#   - "short_press": Toggle-style actions (brief press and release)
#   - "long_press": Hold-to-activate actions (press and hold)
#
DEVICE_TRIGGERS = {
    # J1 has 2 inputs
    "J1": [
        TRIGGER_BUTTON_1_PRESSED,
        TRIGGER_BUTTON_1_RELEASED,
        TRIGGER_BUTTON_1_SHORT_PRESS,
        TRIGGER_BUTTON_1_LONG_PRESS,
        TRIGGER_BUTTON_2_PRESSED,
        TRIGGER_BUTTON_2_RELEASED,
        TRIGGER_BUTTON_2_SHORT_PRESS,
        TRIGGER_BUTTON_2_LONG_PRESS,
    ],
    "J1-R": [
        TRIGGER_BUTTON_1_PRESSED,
        TRIGGER_BUTTON_1_RELEASED,
        TRIGGER_BUTTON_1_SHORT_PRESS,
        TRIGGER_BUTTON_1_LONG_PRESS,
        TRIGGER_BUTTON_2_PRESSED,
        TRIGGER_BUTTON_2_RELEASED,
        TRIGGER_BUTTON_2_SHORT_PRESS,
        TRIGGER_BUTTON_2_LONG_PRESS,
    ],
    # D1 has 2 inputs
    "D1": [
        TRIGGER_BUTTON_1_PRESSED,
        TRIGGER_BUTTON_1_RELEASED,
        TRIGGER_BUTTON_1_SHORT_PRESS,
        TRIGGER_BUTTON_1_LONG_PRESS,
        TRIGGER_BUTTON_2_PRESSED,
        TRIGGER_BUTTON_2_RELEASED,
        TRIGGER_BUTTON_2_SHORT_PRESS,
        TRIGGER_BUTTON_2_LONG_PRESS,
    ],
    "D1-R": [
        TRIGGER_BUTTON_1_PRESSED,
        TRIGGER_BUTTON_1_RELEASED,
        TRIGGER_BUTTON_1_SHORT_PRESS,
        TRIGGER_BUTTON_1_LONG_PRESS,
        TRIGGER_BUTTON_2_PRESSED,
        TRIGGER_BUTTON_2_RELEASED,
        TRIGGER_BUTTON_2_SHORT_PRESS,
        TRIGGER_BUTTON_2_LONG_PRESS,
    ],
    # S1 has 1 input
    "S1": [
        TRIGGER_BUTTON_1_PRESSED,
        TRIGGER_BUTTON_1_RELEASED,
        TRIGGER_BUTTON_1_SHORT_PRESS,
        TRIGGER_BUTTON_1_LONG_PRESS,
    ],
    # S1-R has 2 inputs
    "S1-R": [
        TRIGGER_BUTTON_1_PRESSED,
        TRIGGER_BUTTON_1_RELEASED,
        TRIGGER_BUTTON_1_SHORT_PRESS,
        TRIGGER_BUTTON_1_LONG_PRESS,
        TRIGGER_BUTTON_2_PRESSED,
        TRIGGER_BUTTON_2_RELEASED,
        TRIGGER_BUTTON_2_SHORT_PRESS,
        TRIGGER_BUTTON_2_LONG_PRESS,
    ],
}

# User-friendly trigger names for the UI
TRIGGER_NAMES = {
    TRIGGER_BUTTON_1_PRESSED: "Button 1 pressed",
    TRIGGER_BUTTON_1_RELEASED: "Button 1 released",
    TRIGGER_BUTTON_1_SHORT_PRESS: "Button 1 short press",
    TRIGGER_BUTTON_1_LONG_PRESS: "Button 1 long press",
    TRIGGER_BUTTON_2_PRESSED: "Button 2 pressed",
    TRIGGER_BUTTON_2_RELEASED: "Button 2 released",
    TRIGGER_BUTTON_2_SHORT_PRESS: "Button 2 short press",
    TRIGGER_BUTTON_2_LONG_PRESS: "Button 2 long press",
}

# Trigger schema for validation
TRIGGER_SCHEMA = DEVICE_TRIGGER_BASE_SCHEMA.extend(
    {
        vol.Required(CONF_TYPE): vol.In(
            set(TRIGGER_NAMES.keys())
        ),  # Must be a valid trigger type
    }
)


async def async_get_triggers(
    hass: HomeAssistant, device_id: str
) -> list[dict[str, Any]]:
    """Return a list of triggers for a Ubisys device.

    This is called by Home Assistant when building the automation UI.
    It returns all available triggers for the specified device.

    Args:
        hass: Home Assistant instance
        device_id: Device registry ID

    Returns:
        List of trigger configurations, each containing:
        - platform: "device"
        - domain: "ubisys"
        - device_id: The device ID
        - type: Trigger type (e.g., "button_1_short_press")
        - metadata: User-friendly name and suggested area

    Example Return Value:
        [
            {
                "platform": "device",
                "domain": "ubisys",
                "device_id": "abc123",
                "type": "button_1_short_press",
                "metadata": {
                    "name": "Button 1 short press",
                    "suggested_area": "living_room"
                }
            },
            ...
        ]
    """
    device_registry = dr.async_get(hass)
    device = device_registry.async_get(device_id)

    if not device:
        _LOGGER.warning("Device %s not found in registry", device_id)
        return []

    # Extract model from device
    model = extract_model_from_device(device)
    if not model:
        _LOGGER.warning("Could not determine model for device %s", device_id)
        return []

    # Get available triggers for this device model
    available_triggers = DEVICE_TRIGGERS.get(model, [])
    if not available_triggers:
        _LOGGER.debug("No triggers available for model %s", model)
        return []

    # Build trigger configurations
    triggers = []
    for trigger_type in available_triggers:
        trigger_name = TRIGGER_NAMES.get(trigger_type, trigger_type)

        triggers.append(
            {
                CONF_PLATFORM: "device",
                CONF_DOMAIN: DOMAIN,
                CONF_DEVICE_ID: device_id,
                CONF_TYPE: trigger_type,
                "metadata": {
                    "name": trigger_name,
                    "suggested_area": device.area_id,
                },
            }
        )

    _LOGGER.debug(
        "Returning %d triggers for %s (device_id=%s)",
        len(triggers),
        model,
        device_id,
    )

    return triggers


async def async_attach_trigger(
    hass: HomeAssistant,
    config: ConfigType,
    action: Any,
    trigger_info: dict[str, Any],
) -> CALLBACK_TYPE:
    """Attach a trigger for a Ubisys input event.

    This is called when an automation is activated. It sets up a listener
    that will call the action when the specified trigger fires.

    How It Works:
        1. Extract trigger configuration (device_id, trigger_type)
        2. Subscribe to dispatcher signal from input_monitor
        3. When signal received, check if event matches trigger config
        4. If match, call the automation action
        5. Return unsubscribe function for cleanup

    Args:
        hass: Home Assistant instance
        config: Trigger configuration from automation
        action: Action to call when trigger fires
        trigger_info: Additional trigger context

    Returns:
        Unsubscribe function to remove the listener

    Example Config:
        {
            "platform": "device",
            "domain": "ubisys",
            "device_id": "abc123",
            "type": "button_1_short_press"
        }
    """
    device_id = config[CONF_DEVICE_ID]
    trigger_type = config[CONF_TYPE]

    _LOGGER.debug(
        "Attaching trigger: device_id=%s, type=%s",
        device_id,
        trigger_type,
    )

    # Create dispatcher signal for this device
    signal = f"{SIGNAL_INPUT_EVENT}_{device_id}"

    @callback
    def handle_event(event_data: dict[str, Any]) -> None:
        """Handle input event and check if it matches trigger."""
        # Extract input number and press type from event
        input_number = event_data.get(ATTR_INPUT_NUMBER)
        press_type = event_data.get(ATTR_PRESS_TYPE)

        if input_number is None or press_type is None:
            _LOGGER.debug(
                "Event missing input_number or press_type: %s", event_data
            )
            return

        # Map (input_number, press_type) to trigger_type
        event_trigger_type = PRESS_TYPE_TO_TRIGGER.get((input_number, press_type))

        if event_trigger_type is None:
            _LOGGER.debug(
                "No trigger mapping for input=%d, press=%s",
                input_number,
                press_type,
            )
            return

        # Check if this event matches the trigger we're waiting for
        if event_trigger_type == trigger_type:
            _LOGGER.debug(
                "Trigger matched: %s (input=%d, press=%s)",
                trigger_type,
                input_number,
                press_type,
            )

            # Call the automation action
            hass.async_run_job(
                action,
                {
                    "trigger": {
                        "platform": "device",
                        "domain": DOMAIN,
                        "device_id": device_id,
                        "type": trigger_type,
                        "input_number": input_number,
                        "press_type": press_type,
                        "description": TRIGGER_NAMES.get(trigger_type, trigger_type),
                    },
                    **trigger_info,
                },
            )

    # Subscribe to dispatcher signal
    unsub = async_dispatcher_connect(hass, signal, handle_event)

    _LOGGER.debug(
        "Trigger attached: device_id=%s, type=%s, signal=%s",
        device_id,
        trigger_type,
        signal,
    )

    # Return unsubscribe function
    return unsub


async def async_get_trigger_capabilities(
    hass: HomeAssistant, config: ConfigType
) -> dict[str, vol.Schema]:
    """Return trigger capabilities.

    This is optional and provides additional configuration options for
    triggers. For Ubisys input triggers, we don't need additional
    configuration, so we return an empty schema.

    Args:
        hass: Home Assistant instance
        config: Trigger configuration

    Returns:
        Dictionary with 'extra_fields' key containing voluptuous schema
    """
    return {
        "extra_fields": vol.Schema({})  # No additional fields needed
    }
