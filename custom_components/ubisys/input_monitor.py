"""Monitor Ubisys physical input activity and fire Home Assistant events.

This module monitors ZigBee commands sent from Ubisys controller endpoints
(which represent physical inputs) and correlates them with InputActions
configuration to determine which input and press type triggered the command.

Events are fired to Home Assistant for consumption by automations, device triggers,
and event entities.
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any

from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import async_track_state_change_event

from .const import (
    ATTR_COMMAND,
    ATTR_DEVICE_IEEE,
    ATTR_INPUT_NUMBER,
    ATTR_PRESS_TYPE,
    CONF_DEVICE_IEEE,
    DEVICE_SETUP_CLUSTER_ID,
    DOMAIN,
    EVENT_UBISYS_INPUT,
    INPUT_ACTIONS_ATTR_ID,
    SIGNAL_INPUT_EVENT,
    UBISYS_MANUFACTURER_CODE,
)
from .helpers import (
    extract_ieee_from_device,
    extract_model_from_device,
    get_cluster,
    get_device_setup_cluster,
    get_entity_device_info,
    validate_ubisys_entity,
)
from .input_parser import InputActionRegistry, InputActionsParser, PressType

if TYPE_CHECKING:
    from zigpy.zcl import Cluster

_LOGGER = logging.getLogger(__name__)

# Device model-specific controller endpoint configuration
CONTROLLER_ENDPOINTS = {
    "J1": [2],  # Window covering controller
    "J1-R": [2],
    "D1": [2, 3],  # Primary and secondary dimmer switches
    "D1-R": [2, 3],
    "S1": [2],  # Level control switch
    "S1-R": [2, 3],  # Primary and secondary switches
}

# Device model-specific expected clusters on controller endpoints
CONTROLLER_CLUSTERS = {
    "J1": [0x0102],  # WindowCovering
    "J1-R": [0x0102],
    "D1": [0x0006, 0x0008],  # OnOff, LevelControl
    "D1-R": [0x0006, 0x0008],
    "S1": [0x0006],  # OnOff
    "S1-R": [0x0006],
}


class UbisysInputMonitor:
    """Monitors physical inputs on a Ubisys device.

    This class:
    1. Reads InputActions configuration from the device
    2. Monitors ZHA events for commands from controller endpoints
    3. Correlates observed commands with InputActions to identify input/press
    4. Fires Home Assistant events for automation integration

    Design Pattern:
    - One monitor instance per Ubisys device
    - Monitors all inputs on that device
    - Lifecycle managed by integration __init__.py
    """

    def __init__(
        self,
        hass: HomeAssistant,
        device_ieee: str,
        model: str,
        device_id: str,
    ) -> None:
        """Initialize input monitor for a device.

        Args:
            hass: Home Assistant instance
            device_ieee: IEEE address of the device (e.g., "00:1f:ee:00:00:00:00:01")
            model: Device model (e.g., "J1", "D1", "S1-R")
            device_id: Home Assistant device ID for event context
        """
        self.hass = hass
        self.device_ieee = device_ieee
        self.model = model
        self.device_id = device_id

        self._registry = InputActionRegistry()
        self._controller_endpoints = CONTROLLER_ENDPOINTS.get(model, [])
        self._expected_clusters = CONTROLLER_CLUSTERS.get(model, [])
        self._unsubscribe_listeners: list[Any] = []
        self._started = False

        _LOGGER.debug(
            "Created input monitor for %s (%s) with controller endpoints %s",
            model,
            device_ieee,
            self._controller_endpoints,
        )

    async def async_start(self) -> None:
        """Start monitoring input events.

        This reads the InputActions configuration from the device and sets up
        event listeners for commands from controller endpoints.
        """
        if self._started:
            _LOGGER.warning("Input monitor already started for %s", self.device_ieee)
            return

        try:
            # Read InputActions configuration
            await self._async_read_input_actions()

            # Subscribe to ZHA command events
            self._subscribe_to_zha_events()

            self._started = True
            _LOGGER.info("Started input monitoring for %s (%s)", self.model, self.device_ieee)

        except Exception as err:
            _LOGGER.error(
                "Failed to start input monitoring for %s: %s",
                self.device_ieee,
                err,
                exc_info=True,
            )

    async def async_stop(self) -> None:
        """Stop monitoring input events."""
        if not self._started:
            return

        # Unsubscribe from all listeners
        for unsubscribe in self._unsubscribe_listeners:
            unsubscribe()
        self._unsubscribe_listeners.clear()

        self._started = False
        _LOGGER.info("Stopped input monitoring for %s", self.device_ieee)

    async def _async_read_input_actions(self) -> None:
        """Read InputActions configuration from the device.

        This reads the raw micro-code from cluster 0xFC00 (DeviceSetup),
        attribute 0x0001 (InputActions), parses it, and registers the actions
        in the correlation registry.
        """
        _LOGGER.debug("Reading InputActions from %s (%s)", self.device_ieee, self.model)

        try:
            # Get the DeviceSetup cluster from endpoint 232
            cluster = await get_device_setup_cluster(self.hass, self.device_ieee)

            if not cluster:
                _LOGGER.warning(
                    "DeviceSetup cluster not found for %s - input correlation disabled",
                    self.device_ieee,
                )
                return

            # Read InputActions attribute (manufacturer-specific, requires mfg code)
            _LOGGER.debug(
                "Reading InputActions attribute (0x%04X) from %s",
                INPUT_ACTIONS_ATTR_ID,
                self.device_ieee,
            )

            result = await cluster.read_attributes(
                [INPUT_ACTIONS_ATTR_ID],
                manufacturer=UBISYS_MANUFACTURER_CODE,
            )

            # Check if read was successful
            if not result or not isinstance(result, list) or len(result) == 0:
                _LOGGER.warning(
                    "Failed to read InputActions from %s: empty result",
                    self.device_ieee,
                )
                return

            # Extract attribute value from result
            # Result format: [({attr_id: value, ...}, {attr_id: status, ...})]
            attributes_dict = result[0]
            if INPUT_ACTIONS_ATTR_ID not in attributes_dict:
                _LOGGER.warning(
                    "InputActions attribute (0x%04X) not in read result for %s",
                    INPUT_ACTIONS_ATTR_ID,
                    self.device_ieee,
                )
                return

            input_actions_data = attributes_dict[INPUT_ACTIONS_ATTR_ID]

            # Convert to bytes if needed
            if isinstance(input_actions_data, list):
                input_actions_data = bytes(input_actions_data)
            elif not isinstance(input_actions_data, bytes):
                _LOGGER.warning(
                    "InputActions data has unexpected type: %s",
                    type(input_actions_data).__name__,
                )
                return

            _LOGGER.debug(
                "Read %d bytes of InputActions data from %s",
                len(input_actions_data),
                self.device_ieee,
            )

            # Parse and register actions
            actions = InputActionsParser.parse(input_actions_data)
            self._registry.register(actions)

            _LOGGER.info(
                "Registered %d InputActions for %s (%s)",
                len(actions),
                self.model,
                self.device_ieee,
            )

            # Log registered actions for debugging
            if _LOGGER.isEnabledFor(logging.DEBUG):
                for action in actions:
                    _LOGGER.debug(
                        "  Input %d (%s) → ep%d cluster=0x%04X cmd=0x%02X",
                        action.input_number,
                        action.press_type.value,
                        action.source_endpoint,
                        action.cluster_id,
                        action.command_id,
                    )

        except Exception as err:
            _LOGGER.error(
                "Failed to read InputActions from %s: %s",
                self.device_ieee,
                err,
                exc_info=True,
            )
            # Don't fail startup - we can still fire events without correlation
            # (they just won't have accurate input_number/press_type info)

    def _subscribe_to_zha_events(self) -> None:
        """Subscribe to ZHA events for command observation.

        ZHA fires 'zha_event' when devices send commands. We filter for:
        - Events from this device (IEEE match)
        - Events from controller endpoints
        - Command types we expect based on device model

        ZHA Event Monitoring vs. Cluster Interception:

        There are three approaches to monitoring input events:

        1. ZHA Event Bus (Current Implementation):
           - Subscribe to 'zha_event' on Home Assistant event bus
           - Pros: Simple, no ZHA modifications needed, works across HA restarts
           - Cons: Dependent on ZHA firing events, less direct
           - Use case: General purpose, reliable for most scenarios

        2. ZHA Command Listener API (Alternative):
           - Register listener via ZHA's command listener system
           - Pros: More direct, less overhead than event bus
           - Cons: Requires ZHA support, may not work with all ZHA versions
           - Use case: If ZHA events prove unreliable

        3. Quirk-Level Cluster Interception (Most Direct):
           - Override cluster command handler in custom quirk
           - Pros: Lowest latency, most reliable, sees all commands
           - Cons: Requires quirk modifications, harder to maintain
           - Use case: If ZHA events miss commands or have high latency

        Current Choice:
           We use approach #1 (ZHA event bus) because:
           - It's the simplest and most maintainable
           - ZHA reliably fires events for Ubisys controller endpoint commands
           - No quirk modifications needed (quirks only define attributes)
           - Works consistently across Home Assistant versions

        Future Consideration:
           If users report missed button presses, we can implement approach #3
           by adding command interception to the custom quirks.
        """
        @callback
        def handle_zha_event(event: Event) -> None:
            """Handle ZHA event and check if it's from a controller endpoint."""
            try:
                event_data = event.data

                # Check if event is from this device
                device_ieee = event_data.get("device_ieee")
                if device_ieee != self.device_ieee:
                    return

                # Check if event is from a controller endpoint
                endpoint_id = event_data.get("endpoint_id")
                if endpoint_id not in self._controller_endpoints:
                    return

                # Extract command information
                cluster_id = event_data.get("cluster_id")
                command_id = event_data.get("command")
                args = event_data.get("args", [])

                _LOGGER.debug(
                    "ZHA event from %s ep%d: cluster=0x%04X, cmd=0x%02X, args=%s",
                    self.model,
                    endpoint_id,
                    cluster_id or 0,
                    command_id or 0,
                    args,
                )

                # Correlate command with InputActions
                self._handle_controller_command(
                    endpoint_id, cluster_id or 0, command_id or 0, bytes(args)
                )

            except Exception as err:
                _LOGGER.error(
                    "Error handling ZHA event for %s: %s",
                    self.device_ieee,
                    err,
                    exc_info=True,
                )

        # Subscribe to zha_event
        unsub = self.hass.bus.async_listen("zha_event", handle_zha_event)
        self._unsubscribe_listeners.append(unsub)

        _LOGGER.debug(
            "Subscribed to zha_event for %s (endpoints %s)",
            self.device_ieee,
            self._controller_endpoints,
        )

    def _handle_controller_command(
        self, endpoint: int, cluster: int, command: int, payload: bytes
    ) -> None:
        """Handle a command observed from a controller endpoint.

        This is where the magic happens - we correlate raw Zigbee commands
        with the device's InputActions configuration to determine which
        physical input was pressed and how.

        How InputActions Correlation Works:

        1. Device stores InputActions micro-code in cluster 0xFC00 attribute 0x0001
        2. We read this micro-code during monitor startup (_async_read_input_actions)
        3. Micro-code maps: (input, press_type) → (endpoint, cluster, command, payload)
        4. We parse and store these mappings in self._registry
        5. When a command is observed, we reverse-lookup: command → (input, press_type)

        Example:
           InputActions says: "Input 0 short press → EP2 OnOff Toggle"
           We observe: EP2 sends OnOff Toggle command
           We correlate: This was input 0, short press
           We fire event: ubisys_input_event(input_number=0, press_type="short_press")

        Why This is Necessary:
           Without correlation, we only know "EP2 sent Toggle" but not whether it was:
           - Input 0 short press vs. long press
           - Input 0 vs. Input 1 (if both are configured to send Toggle)
           The InputActions correlation tells us the precise input and press type.

        Fallback Behavior:
           If InputActions couldn't be read or correlation fails, we fire a generic
           event using the endpoint as a hint for which input (not always accurate).

        Args:
            endpoint: Source endpoint ID
            cluster: Cluster ID
            command: Command ID
            payload: Command payload bytes
        """
        # Try to correlate with InputActions
        # This looks up the (endpoint, cluster, command, payload) combination
        # in our registry to find the matching (input_number, press_type)
        action = self._registry.lookup(endpoint, cluster, command, payload)

        if action:
            input_number = action.input_number
            press_type = action.press_type.value
            _LOGGER.debug(
                "Correlated command to input %d (%s)", input_number, press_type
            )
        else:
            # No correlation available - fire generic event
            # Input number is unknown, use endpoint as hint
            input_number = endpoint - self._controller_endpoints[0]
            press_type = PressType.PRESSED.value
            _LOGGER.debug(
                "No InputActions correlation - using generic event "
                "(input=%d, press=%s)",
                input_number,
                press_type,
            )

        # Fire Home Assistant event
        self._fire_input_event(
            input_number=input_number,
            press_type=press_type,
            command_info={
                "endpoint": endpoint,
                "cluster": cluster,
                "command": command,
            },
        )

    def _fire_input_event(
        self, input_number: int, press_type: str, command_info: dict[str, Any]
    ) -> None:
        """Fire Home Assistant event for input activity.

        This fires both:
        1. A bus event (ubisys_input_event) for advanced users
        2. A dispatcher signal for internal consumption (device triggers, event entities)

        Args:
            input_number: Physical input number (0-based)
            press_type: Type of press (pressed, released, short_press, long_press)
            command_info: Raw command details for debugging
        """
        event_data = {
            ATTR_DEVICE_IEEE: self.device_ieee,
            "device_id": self.device_id,
            "model": self.model,
            ATTR_INPUT_NUMBER: input_number,
            ATTR_PRESS_TYPE: press_type,
            ATTR_COMMAND: command_info,
        }

        # Fire bus event
        self.hass.bus.async_fire(EVENT_UBISYS_INPUT, event_data)

        # Fire dispatcher signal
        signal = f"{SIGNAL_INPUT_EVENT}_{self.device_id}"
        async_dispatcher_send(self.hass, signal, event_data)

        _LOGGER.info(
            "%s input %d: %s",
            self.model,
            input_number + 1,  # Display as 1-based for user readability
            press_type,
        )


async def async_setup_input_monitoring(
    hass: HomeAssistant, config_entry_id: str
) -> None:
    """Set up input monitoring for all Ubisys devices in a config entry.

    This is called during integration startup to initialize monitoring for
    all devices that support physical inputs.

    Args:
        hass: Home Assistant instance
        config_entry_id: Config entry ID for this integration instance
    """
    # Get all Ubisys devices from device registry
    device_registry = dr.async_get(hass)
    devices = dr.async_entries_for_config_entry(device_registry, config_entry_id)

    monitors = []

    for device in devices:
        # Check if device model supports inputs
        model = extract_model_from_device(device)
        if not model or model not in CONTROLLER_ENDPOINTS:
            _LOGGER.debug(
                "Device %s (model=%s) does not support input monitoring",
                device.name,
                model,
            )
            continue

        # Get device IEEE address
        ieee = extract_ieee_from_device(device)
        if not ieee:
            _LOGGER.warning(
                "Could not extract IEEE address from device %s", device.name
            )
            continue

        # Create and start monitor
        monitor = UbisysInputMonitor(hass, ieee, model, device.id)
        await monitor.async_start()
        monitors.append(monitor)

    # Store monitors in hass.data for cleanup
    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = {}
    hass.data[DOMAIN].setdefault("input_monitors", []).extend(monitors)

    _LOGGER.info("Set up input monitoring for %d devices", len(monitors))


async def async_unload_input_monitoring(hass: HomeAssistant) -> None:
    """Unload all input monitors.

    Called during integration unload to clean up resources.

    Args:
        hass: Home Assistant instance
    """
    monitors = hass.data.get(DOMAIN, {}).get("input_monitors", [])

    for monitor in monitors:
        await monitor.async_stop()

    if DOMAIN in hass.data and "input_monitors" in hass.data[DOMAIN]:
        del hass.data[DOMAIN]["input_monitors"]

    _LOGGER.info("Unloaded input monitoring")
