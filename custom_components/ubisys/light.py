"""Light platform for Ubisys Zigbee integration.

This module provides wrapper light entities that delegate to ZHA light entities
while adding Ubisys-specific features and metadata.

Architecture Note:
    Unlike the cover platform which filters features based on shade type, the
    light platform is simpler because all D1 dimmers have identical capabilities.
    The main purposes of this wrapper are:
    1. Consistent device identification (IEEE address-based)
    2. Integration-specific attributes (model, ZHA entity reference)
    3. Future extensibility for D1-specific features

Why a Wrapper Entity:
    We create a wrapper light entity that delegates to ZHA because:
    - ZHA already provides excellent dimming control
    - We want to add Ubisys-specific metadata and configuration
    - We want consistent entity IDs across reboots
    - We want to track which ZHA entity we're wrapping

    The wrapper delegates all light operations (on, off, brightness) to the
    underlying ZHA light entity while adding our custom attributes.

See Also:
    - cover.py: Similar wrapper pattern for J1 covers
    - d1_config.py: D1-specific configuration services
    - custom_zha_quirks/ubisys_d1.py: ZHA quirk for D1 devices
"""

from __future__ import annotations

import logging
from typing import Any, cast

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_TRANSITION,
    ColorMode,
    LightEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_state_change_event

from .const import (
    CONF_DEVICE_ID,
    CONF_DEVICE_IEEE,
    DOMAIN,
)
from .ha_typing import callback as _typed_callback
from .helpers import is_verbose_info_logging

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Ubisys light from config entry.

    This function is called by Home Assistant when setting up the integration
    from a config entry. It finds the underlying ZHA light entity and creates
    a wrapper entity that delegates to it.

    How It Works:
        1. Extract device info from config entry (IEEE address, device ID)
        2. Find the ZHA light entity for this device
        3. Create wrapper UbisysLight entity
        4. Add wrapper entity to Home Assistant

    Why We Need This:
        The ZHA integration already creates a light entity for the D1, but we
        want to:
        - Add Ubisys-specific metadata
        - Provide consistent entity naming
        - Track the relationship between our wrapper and ZHA entity
        - Enable future D1-specific features

    Args:
        hass: Home Assistant instance
        config_entry: Config entry for this device
        async_add_entities: Callback to add entities

    Logging:
        INFO: When wrapper is created
        WARNING: If ZHA entity not found
        DEBUG: Entity creation details
    """
    device_ieee = config_entry.data[CONF_DEVICE_IEEE]
    device_id = config_entry.data[CONF_DEVICE_ID]
    model = config_entry.data.get("model", "D1")

    # Only create light entities for D1/D1-R dimmer models
    # J1 devices are covers, S1 devices are switches
    from .const import DIMMER_MODELS

    if model not in DIMMER_MODELS:
        _LOGGER.debug(
            "Skipping light entity for non-dimmer device: model=%s (ieee=%s)",
            model,
            device_ieee,
        )
        return

    _LOGGER.debug(
        "Setting up Ubisys light for device: ieee=%s, id=%s, model=%s",
        device_ieee,
        device_id,
        model,
    )

    # Find the ZHA light entity (or predict entity ID if not found yet)
    zha_entity_id = await _find_zha_light_entity(hass, device_id, device_ieee)

    # Note: ZHA entity auto-enable is handled centrally in __init__.py

    _LOGGER.log(
        logging.INFO if is_verbose_info_logging(hass) else logging.DEBUG,
        "Creating Ubisys light wrapper for %s (ZHA entity: %s, model: %s)",
        device_ieee,
        zha_entity_id,
        model,
    )

    # Create wrapper entity
    light = UbisysLight(
        hass=hass,
        config_entry=config_entry,
        zha_entity_id=zha_entity_id,
        device_ieee=device_ieee,
        model=model,
    )

    async_add_entities([light])


async def _find_zha_light_entity(
    hass: HomeAssistant, device_id: str, device_ieee: str
) -> str:
    """Find the ZHA light entity for a device.

    If the ZHA entity doesn't exist yet (e.g., during startup race condition),
    this function predicts the entity ID. The wrapper entity will mark itself
    as unavailable and automatically recover when ZHA creates its entity.

    Args:
        hass: Home Assistant instance
        device_id: Device registry ID
        device_ieee: Device IEEE address for logging and prediction

    Returns:
        ZHA light entity ID (either found or predicted)

    Why This Is Needed:
        ZHA creates entities with its own naming scheme and entity IDs. We need
        to find that entity so our wrapper can delegate to it. The entity ID
        may change across HA restarts, so we look it up dynamically.

    See Also:
        - helpers.py: find_zha_entity_for_device() - similar shared utility
        - cover.py: _find_zha_cover_entity() - same pattern for covers
    """
    entity_registry = er.async_get(hass)

    # Find all entities for this device
    entities = er.async_entries_for_device(entity_registry, device_id)

    _LOGGER.debug(
        "Searching for ZHA light entity in %d entities for device %s",
        len(entities),
        device_id,
    )

    for entity_entry in entities:
        if entity_entry.platform == "zha" and entity_entry.domain == "light":
            _LOGGER.debug(
                "Found ZHA light entity: %s (platform=%s, domain=%s)",
                entity_entry.entity_id,
                entity_entry.platform,
                entity_entry.domain,
            )
            return cast(str, entity_entry.entity_id)

    # ZHA entity not found - predict entity ID
    # This handles startup race condition where Ubisys loads before ZHA
    from homeassistant.helpers import device_registry as dr

    device_registry = dr.async_get(hass)
    device = device_registry.async_get(device_id)

    if device and device.name_by_user:
        predicted_name = device.name_by_user.lower().replace(" ", "_")
    elif device and device.name:
        predicted_name = device.name.lower().replace(" ", "_")
    else:
        # Fallback: use IEEE address
        predicted_name = f"ubisys_{device_ieee.replace(':', '_')}"

    predicted_entity_id = f"light.{predicted_name}"

    _LOGGER.warning(
        "ZHA light entity not found for device %s (%s). "
        "Predicting entity ID as %s. "
        "Wrapper entity will be unavailable until ZHA entity appears.",
        device_id,
        device_ieee,
        predicted_entity_id,
    )

    return predicted_entity_id


class UbisysLight(LightEntity):
    """Wrapper light entity that delegates to ZHA.

    This wrapper entity delegates all light operations to the underlying ZHA
    light entity while adding Ubisys-specific metadata and attributes.

    Delegation Pattern:
        All light operations (turn_on, turn_off, brightness changes) are
        forwarded to the ZHA light entity via service calls. State is synced
        from the ZHA entity via event tracking.

    Why Delegate Instead of Control Directly:
        ZHA already has excellent Zigbee communication handling, retry logic,
        and state management. Rather than duplicate that complexity, we delegate
        to ZHA and add our value on top.

    Attributes:
        _zha_entity_id: The ZHA light entity we're wrapping
        _device_ieee: Device IEEE address (for identification)
        _model: Device model (D1, D1-R)
        _attr_supported_color_modes: Color modes (brightness only for D1)
        _attr_color_mode: Current color mode
        _attr_is_on: Whether light is on
        _attr_brightness: Current brightness (0-255)

    See Also:
        - cover.py: UbisysCover - similar wrapper pattern for J1 covers
        - d1_config.py: Configuration services for phase mode and ballast
    """

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        zha_entity_id: str,
        device_ieee: str,
        model: str,
    ) -> None:
        """Initialize the Ubisys light.

        Args:
            hass: Home Assistant instance
            config_entry: Config entry for this device
            zha_entity_id: ZHA light entity to delegate to
            device_ieee: Device IEEE address
            model: Device model (D1, D1-R)
        """
        self.hass = hass
        self._config_entry = config_entry
        self._zha_entity_id = zha_entity_id
        self._device_ieee = device_ieee
        self._model = model

        # Set unique ID based on IEEE address (stable across restarts)
        self._attr_unique_id = f"{device_ieee}_light"

        # Set device info (links this entity to the device)
        self._attr_device_info = {
            "identifiers": {(DOMAIN, device_ieee)},
        }

        # D1 supports brightness control only (not color)
        self._attr_supported_color_modes = {ColorMode.BRIGHTNESS}
        self._attr_color_mode = ColorMode.BRIGHTNESS

        # State tracking (synced from ZHA entity)
        self._attr_is_on: bool | None = None
        self._attr_brightness: int | None = None

        # ZHA entity availability tracking (for graceful degradation)
        # This allows wrapper entity to handle startup race conditions
        # where ZHA hasn't created its entity yet
        self._zha_entity_available = False

        _LOGGER.debug(
            "Initialized UbisysLight: ieee=%s, zha_entity=%s, model=%s",
            device_ieee,
            zha_entity_id,
            model,
        )

    async def async_added_to_hass(self) -> None:
        """Run when entity is added to Home Assistant.

        This method is called after the entity is registered with Home Assistant.
        We use it to:
        1. Sync initial state from ZHA entity
        2. Set up state change tracking

        Why Track State Changes:
            The ZHA entity state can change from:
            - User actions via HA UI
            - Physical switch presses
            - Zigbee commands from other devices
            - Automations

            We need to track all these changes to keep our wrapper in sync.
        """
        # Initial state sync
        await self._sync_state_from_zha()

        # Track ZHA entity state changes
        # async_on_remove ensures tracking is cleaned up when entity is removed
        self.async_on_remove(
            async_track_state_change_event(
                self.hass, [self._zha_entity_id], self._handle_zha_state_change
            )
        )

        _LOGGER.debug(
            "UbisysLight added to hass: %s (tracking %s)",
            self._attr_unique_id,
            self._zha_entity_id,
        )

    @_typed_callback
    def _handle_zha_state_change(self, event: object) -> None:
        """Handle ZHA entity state change event.

        This callback is triggered whenever the ZHA entity state changes.
        We create an async task to sync our state from the new ZHA state.

        Args:
            event: State change event from Home Assistant

        Why Use async_create_task:
            This callback must be synchronous (@callback decorator), but state
            syncing is async. We create a task to handle the async operation.
        """
        _LOGGER.debug(
            "ZHA state change detected for %s, syncing state",
            self._zha_entity_id,
        )
        self.hass.async_create_task(self._sync_state_from_zha())

    async def _sync_state_from_zha(self) -> None:
        """Sync state from ZHA entity.

        Handles graceful degradation when ZHA entity doesn't exist yet
        (startup race condition) or becomes unavailable.

        State Attributes Synced:
            - is_on: Whether light is on or off
            - brightness: Current brightness level (0-255)
        """
        zha_state = self.hass.states.get(self._zha_entity_id)

        if zha_state is None:
            # ZHA entity not found - handle gracefully
            if self._zha_entity_available:
                # Entity was available before, now it's gone
                _LOGGER.warning(
                    "ZHA entity %s disappeared for device %s",
                    self._zha_entity_id,
                    self._device_ieee,
                )
            else:
                # Entity never existed (likely startup race condition)
                _LOGGER.debug(
                    "ZHA entity %s not found for sync (device: %s). "
                    "Wrapper will be unavailable until ZHA entity appears.",
                    self._zha_entity_id,
                    self._device_ieee,
                )

            self._zha_entity_available = False
            self.async_write_ha_state()
            return

        # ZHA entity exists - check if it just appeared
        if not self._zha_entity_available:
            _LOGGER.info(
                "ZHA entity %s became available for device %s. "
                "Wrapper entity is now operational.",
                self._zha_entity_id,
                self._device_ieee,
            )
            self._zha_entity_available = True

        # Update state attributes from ZHA entity
        self._attr_is_on = zha_state.state == "on"
        self._attr_brightness = zha_state.attributes.get("brightness")

        # Write updated state to Home Assistant
        self.async_write_ha_state()

        _LOGGER.debug(
            "Synced state from ZHA: %s -> is_on=%s, brightness=%s",
            self._zha_entity_id,
            self._attr_is_on,
            self._attr_brightness,
        )

    @property
    def available(self) -> bool:
        """Return if entity is available.

        Wrapper entity is only available when the underlying ZHA entity exists
        and is available. This handles startup race conditions where Ubisys loads
        before ZHA has created its light entity.

        Returns:
            True if ZHA entity exists and is available, False otherwise
        """
        zha_state = self.hass.states.get(self._zha_entity_id)

        if zha_state is None:
            # ZHA entity doesn't exist yet (startup race condition)
            return False

        # Check if ZHA entity is available (not unavailable/unknown)
        from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN

        if zha_state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            return False

        return True

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return entity-specific state attributes.

        These attributes appear in the entity's state and are useful for:
        - Debugging (seeing which ZHA entity we're wrapping)
        - Automations (filtering by model)
        - User information

        Returns:
            Dictionary of additional attributes
        """
        attrs = {
            "model": self._model,
            "zha_entity_id": self._zha_entity_id,
            "integration": "ubisys",
        }

        # Add availability info for debugging
        if not self._zha_entity_available:
            attrs["unavailable_reason"] = "ZHA entity not found or unavailable"

        return attrs

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the light on.

        Delegates to the ZHA light entity via service call. Supports brightness
        and transition parameters.

        Args:
            **kwargs: Service call parameters
                brightness: Target brightness (0-255)
                transition: Transition time in seconds

        Why Use Service Calls:
            Service calls go through HA's standard light control logic, which
            handles:
            - Parameter validation
            - Zigbee command formatting
            - Retry logic
            - State updates

        Logging:
            DEBUG: Logs all turn_on calls with parameters
        """
        _LOGGER.debug(
            "Turning on light %s via ZHA entity %s (kwargs=%s)",
            self._attr_unique_id,
            self._zha_entity_id,
            kwargs,
        )

        service_data = {"entity_id": self._zha_entity_id}

        # Pass through brightness if specified
        if ATTR_BRIGHTNESS in kwargs:
            service_data[ATTR_BRIGHTNESS] = kwargs[ATTR_BRIGHTNESS]

        # Pass through transition if specified
        if ATTR_TRANSITION in kwargs:
            service_data[ATTR_TRANSITION] = kwargs[ATTR_TRANSITION]

        await self.hass.services.async_call(
            "light",
            "turn_on",
            service_data,
            blocking=True,
        )

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the light off.

        Delegates to the ZHA light entity via service call. Supports transition
        parameter for gradual dimming to off.

        Args:
            **kwargs: Service call parameters
                transition: Transition time in seconds

        Logging:
            DEBUG: Logs all turn_off calls with parameters
        """
        _LOGGER.debug(
            "Turning off light %s via ZHA entity %s (kwargs=%s)",
            self._attr_unique_id,
            self._zha_entity_id,
            kwargs,
        )

        service_data = {"entity_id": self._zha_entity_id}

        # Pass through transition if specified
        if ATTR_TRANSITION in kwargs:
            service_data[ATTR_TRANSITION] = kwargs[ATTR_TRANSITION]

        await self.hass.services.async_call(
            "light",
            "turn_off",
            service_data,
            blocking=True,
        )
