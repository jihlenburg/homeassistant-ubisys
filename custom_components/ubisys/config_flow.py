"""Config flow for Ubisys Zigbee integration.

This module handles the configuration flow for setting up Ubisys devices in
Home Assistant. It supports multiple device types with type-specific configuration:

Device Types:
    - J1/J1-R: Window covering controllers (require shade type selection)
    - D1/D1-R: Universal dimmers (no additional configuration needed)
    - S1/S2: Power switches (future, no additional configuration needed)

Flow Types:
    1. Automatic Discovery (async_step_zha):
       - Triggered when ZHA discovers a supported Ubisys device
       - Detects device type and shows appropriate configuration steps

    2. Manual Setup (async_step_manual):
       - User selects from available Ubisys devices
       - Continues to type-specific configuration

Configuration Steps:
    - J1 devices: Require shade type selection (roller, venetian, etc.)
    - D1 devices: No additional configuration (skip to entry creation)
    - Future devices: May have their own configuration steps

Architecture Note:
    This config flow uses device type detection (via get_device_type helper)
    to determine which configuration steps to show. This keeps the flow
    extensible for future device types while maintaining simplicity.

See Also:
    - const.py: Device model categorization (WINDOW_COVERING_MODELS, DIMMER_MODELS)
    - const.py: get_device_type() - Helper to categorize devices
"""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import device_registry as dr, entity_registry as er

from .const import (
    CONF_DEVICE_ID,
    CONF_DEVICE_IEEE,
    CONF_INPUT_CONFIG_PRESET,
    CONF_SHADE_TYPE,
    CONF_ZHA_CONFIG_ENTRY_ID,
    DOMAIN,
    SHADE_TYPES,
    get_device_type,
)
from .input_config import (
    InputActionBuilder,
    InputConfigPreset,
    InputConfigPresets,
    async_apply_input_config,
)

_LOGGER = logging.getLogger(__name__)


class UbisysConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Ubisys Zigbee."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._discovery_data: dict[str, Any] | None = None

    async def async_step_zha(self, discovery_data: dict[str, Any]) -> FlowResult:
        """Handle ZHA discovery of supported device.

        This step is triggered automatically when a supported Ubisys device
        is discovered by ZHA. It receives device information and triggers
        the user step for shade type selection.
        """
        _LOGGER.debug("ZHA discovery triggered with data: %s", discovery_data)

        # Store discovery data for next step
        self._discovery_data = discovery_data

        # Check if already configured
        device_ieee = discovery_data.get("device_ieee")
        await self.async_set_unique_id(device_ieee)
        self._abort_if_unique_id_configured()

        # Show configuration UI to user
        return await self.async_step_user()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle user step for device-specific configuration.

        This step is shown either after ZHA discovery or when manually
        adding the integration. The configuration shown depends on device type:

        - J1 (window covering): Prompts for shade type selection
        - D1 (dimmer): No configuration needed, directly creates entry
        - Future devices: May show device-specific configuration

        Device Type Detection:
            Uses get_device_type() helper to categorize device by model.
            This keeps the logic extensible for future device types.

        Flow Logic:
            1. Check if we have discovery data (if not, show device selection)
            2. Detect device type from model
            3. Route to appropriate configuration step:
               - Window covering → shade type selection
               - Dimmer → direct entry creation
               - Unknown → error

        Why This Design:
            - Single entry point for all device types (simpler for users)
            - Type-specific logic isolated and clear
            - Easy to extend for future device types
        """
        errors: dict[str, str] = {}

        # If we don't have discovery data, show device selection
        if self._discovery_data is None:
            return await self.async_step_manual()

        # Detect device type
        model = self._discovery_data["model"]
        device_type = get_device_type(model)

        _LOGGER.debug(
            "Config flow user step: model=%s, device_type=%s",
            model,
            device_type,
        )

        # Process user input (only for window covering devices that need shade type)
        if user_input is not None:
            if device_type == "window_covering":
                shade_type = user_input[CONF_SHADE_TYPE]
            else:
                shade_type = None  # Not applicable for non-window covering devices

            # Find the ZHA config entry ID
            zha_config_entry_id = await self._get_zha_config_entry_id()
            if not zha_config_entry_id:
                errors["base"] = "zha_not_found"
            else:
                # Build config entry data
                entry_data = {
                    CONF_DEVICE_IEEE: self._discovery_data["device_ieee"],
                    CONF_DEVICE_ID: self._discovery_data["device_id"],
                    CONF_ZHA_CONFIG_ENTRY_ID: zha_config_entry_id,
                    "manufacturer": self._discovery_data["manufacturer"],
                    "model": self._discovery_data["model"],
                    "name": self._discovery_data["name"],
                }

                # Add shade type only for window covering devices
                if device_type == "window_covering":
                    entry_data[CONF_SHADE_TYPE] = shade_type

                # Build title
                if device_type == "window_covering":
                    title = f"{self._discovery_data['name']} ({shade_type})"
                else:
                    title = f"{self._discovery_data['name']} ({model})"

                # Create the config entry
                return self.async_create_entry(
                    title=title,
                    data=entry_data,
                )

        # Route to appropriate configuration step based on device type
        if device_type == "window_covering":
            # J1 devices need shade type selection
            data_schema = vol.Schema(
                {
                    vol.Required(CONF_SHADE_TYPE, default="roller"): vol.In(SHADE_TYPES),
                }
            )

            return self.async_show_form(
                step_id="user",
                data_schema=data_schema,
                errors=errors,
                description_placeholders={
                    "device_name": self._discovery_data.get("name", "Ubisys Device"),
                },
            )

        elif device_type == "dimmer":
            # D1 devices don't need additional configuration
            # Directly create entry without showing form
            zha_config_entry_id = await self._get_zha_config_entry_id()
            if not zha_config_entry_id:
                return self.async_abort(reason="zha_not_found")

            _LOGGER.info(
                "Creating config entry for D1 dimmer: %s",
                self._discovery_data["name"],
            )

            return self.async_create_entry(
                title=f"{self._discovery_data['name']} ({model})",
                data={
                    CONF_DEVICE_IEEE: self._discovery_data["device_ieee"],
                    CONF_DEVICE_ID: self._discovery_data["device_id"],
                    CONF_ZHA_CONFIG_ENTRY_ID: zha_config_entry_id,
                    "manufacturer": self._discovery_data["manufacturer"],
                    "model": self._discovery_data["model"],
                    "name": self._discovery_data["name"],
                },
            )

        else:
            # Unknown device type
            _LOGGER.error(
                "Unknown device type '%s' for model '%s'",
                device_type,
                model,
            )
            return self.async_abort(reason="unsupported_device")

    async def async_step_manual(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle manual device selection.

        This step is shown when the integration is added manually without
        automatic discovery. It shows a list of available Ubisys devices.
        """
        # Get list of available Ubisys devices from ZHA
        available_devices = await self._get_available_devices()

        if not available_devices:
            return self.async_abort(reason="no_devices")

        if user_input is not None:
            # Device selected, store discovery data and continue to shade type
            device_ieee = user_input["device"]
            device_info = available_devices[device_ieee]

            self._discovery_data = {
                "device_ieee": device_ieee,
                "device_id": device_info["device_id"],
                "manufacturer": device_info["manufacturer"],
                "model": device_info["model"],
                "name": device_info["name"],
            }

            await self.async_set_unique_id(device_ieee)
            self._abort_if_unique_id_configured()

            return await self.async_step_user()

        # Show device selection
        device_choices = {
            ieee: f"{info['name']} ({info['model']})"
            for ieee, info in available_devices.items()
        }

        data_schema = vol.Schema(
            {
                vol.Required("device"): vol.In(device_choices),
            }
        )

        return self.async_show_form(
            step_id="manual",
            data_schema=data_schema,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> UbisysOptionsFlow:
        """Get the options flow for this handler."""
        return UbisysOptionsFlow(config_entry)

    async def _get_zha_config_entry_id(self) -> str | None:
        """Get the ZHA config entry ID."""
        for entry in self.hass.config_entries.async_entries("zha"):
            if entry.state == config_entries.ConfigEntryState.LOADED:
                return entry.entry_id
        return None

    async def _get_available_devices(self) -> dict[str, dict[str, Any]]:
        """Get available Ubisys devices from ZHA.

        Returns a dict mapping device IEEE to device info.
        """
        from .const import MANUFACTURER, SUPPORTED_MODELS

        device_registry = dr.async_get(self.hass)
        available: dict[str, dict[str, Any]] = {}

        # Find all Ubisys devices
        for device_entry in device_registry.devices.values():
            # Check manufacturer and model
            if device_entry.manufacturer != MANUFACTURER:
                continue

            if device_entry.model not in SUPPORTED_MODELS:
                continue

            # Extract IEEE from identifiers
            device_ieee = None
            for identifier_set in device_entry.identifiers:
                if identifier_set[0] == "zha":
                    device_ieee = identifier_set[1]
                    break

            if not device_ieee:
                continue

            # Check if already configured
            is_configured = any(
                entry.data.get(CONF_DEVICE_IEEE) == device_ieee
                for entry in self.hass.config_entries.async_entries(DOMAIN)
            )

            if is_configured:
                continue

            available[device_ieee] = {
                "device_id": device_entry.id,
                "manufacturer": device_entry.manufacturer,
                "model": device_entry.model,
                "name": device_entry.name or f"{device_entry.manufacturer} {device_entry.model}",
            }

        return available


class UbisysOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for Ubisys integration.

    Allows changing device-specific options after initial configuration:
    - J1 (window covering): Change shade type
    - D1/D1-R (dimmer): Configure input behavior (toggle+dim, up/down, rocker)
    - S1/S1-R (switch): Configure input behavior (toggle, rocker, etc.)

    Architecture Note:
        The options shown depend on device type. Each device type has
        appropriate configuration options:

        - Window covering: Shade type (affects feature filtering)
        - Dimmer/Switch: Input configuration presets (affects physical button behavior)

        Input configuration changes require writing InputActions micro-code to
        the device, which is done via the input_config module with automatic
        rollback on failure.

        D1 phase mode and ballast configuration remain service-based because
        they are advanced settings that shouldn't be changed as frequently.
    """

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage device-specific options.

        Routes to appropriate options based on device type:
        - Window covering: Show shade type configuration
        - Dimmer: Show message that configuration is done via services
        - Other: No options available
        """
        model = self.config_entry.data.get("model", "")
        device_type = get_device_type(model)

        _LOGGER.debug(
            "Options flow init: model=%s, device_type=%s",
            model,
            device_type,
        )

        if device_type == "window_covering":
            # Window covering devices: Allow changing shade type
            if user_input is not None:
                # Update config entry with new shade type
                new_shade_type = user_input[CONF_SHADE_TYPE]

                # Update entry data (requires updating the entry itself since data is immutable)
                self.hass.config_entries.async_update_entry(
                    self.config_entry,
                    data={**self.config_entry.data, CONF_SHADE_TYPE: new_shade_type},
                )

                # Reload the entry to apply changes
                await self.hass.config_entries.async_reload(self.config_entry.entry_id)

                return self.async_create_entry(title="", data={})

            # Show current shade type
            current_shade_type = self.config_entry.data.get(CONF_SHADE_TYPE, "roller")

            data_schema = vol.Schema(
                {
                    vol.Required(CONF_SHADE_TYPE, default=current_shade_type): vol.In(
                        SHADE_TYPES
                    ),
                }
            )

            return self.async_show_form(
                step_id="init",
                data_schema=data_schema,
                description_placeholders={
                    "device_name": self.config_entry.data.get("name", "Ubisys Device"),
                },
            )

        elif device_type == "dimmer" or device_type == "switch":
            # D1 dimmers and S1 switches: Show input configuration
            return await self.async_step_input_config(user_input)

        else:
            # Unknown or unsupported device type
            return self.async_abort(reason="no_options")

    async def async_step_input_config(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Configure physical input behavior.

        This step allows users to select preset configurations for their
        physical buttons/switches. The preset determines how button presses
        are mapped to ZigBee commands.

        Flow:
            1. Show dropdown with available presets for device model
            2. User selects preset
            3. Generate InputActions micro-code from preset
            4. Write micro-code to device (with automatic rollback on failure)
            5. Save preset name in config entry for future reference

        Error Handling:
            - If device communication fails, show error and retry
            - If verification fails, automatic rollback restores previous config
            - User can cancel at any time (no changes applied)
        """
        errors: dict[str, str] = {}

        model = self.config_entry.data.get("model", "")
        device_ieee = self.config_entry.data.get(CONF_DEVICE_IEEE)
        device_name = self.config_entry.data.get("name", "Device")

        _LOGGER.debug(
            "Input config step: model=%s, device_ieee=%s",
            model,
            device_ieee,
        )

        if user_input is not None:
            # User selected a preset
            preset_value = user_input[CONF_INPUT_CONFIG_PRESET]

            try:
                # Convert string value to enum
                preset = InputConfigPreset(preset_value)

                _LOGGER.info(
                    "Applying input preset '%s' to %s (%s)",
                    preset.value,
                    device_name,
                    model,
                )

                # Generate micro-code from preset
                builder = InputActionBuilder()
                actions = builder.build_preset(preset, model)
                micro_code = b"".join(action.to_bytes() for action in actions)

                _LOGGER.debug(
                    "Generated %d bytes of micro-code from preset %s",
                    len(micro_code),
                    preset.value,
                )

                # Apply to device (with automatic rollback on failure)
                await async_apply_input_config(
                    self.hass,
                    device_ieee,
                    micro_code,
                )

                # Update config entry to remember the preset
                self.hass.config_entries.async_update_entry(
                    self.config_entry,
                    data={
                        **self.config_entry.data,
                        CONF_INPUT_CONFIG_PRESET: preset.value,
                    },
                )

                _LOGGER.info(
                    "✓ Successfully applied input preset '%s' to %s",
                    preset.value,
                    device_name,
                )

                return self.async_create_entry(title="", data={})

            except ValueError as err:
                _LOGGER.error("Invalid preset value: %s", preset_value)
                errors["base"] = "invalid_preset"

            except Exception as err:
                _LOGGER.error(
                    "Failed to apply input configuration: %s",
                    err,
                    exc_info=True,
                )
                errors["base"] = "config_write_failed"

        # Get available presets for this device model
        available_presets = InputConfigPresets.get_presets_for_model(model)

        if not available_presets:
            _LOGGER.warning("No presets available for model %s", model)
            return self.async_abort(reason="no_presets")

        # Build preset choices (preset_value -> "Name - Description")
        preset_choices = {}
        for preset in available_presets:
            name, description = InputConfigPresets.get_preset_info(preset)
            preset_choices[preset.value] = f"{name}"

        # Get current preset (if configured)
        current_preset = self.config_entry.data.get(CONF_INPUT_CONFIG_PRESET)
        if current_preset and current_preset in preset_choices:
            default_preset = current_preset
        else:
            # Default to first preset
            default_preset = available_presets[0].value

        data_schema = vol.Schema(
            {
                vol.Required(
                    CONF_INPUT_CONFIG_PRESET, default=default_preset
                ): vol.In(preset_choices),
            }
        )

        return self.async_show_form(
            step_id="input_config",
            data_schema=data_schema,
            errors=errors,
            description_placeholders={
                "device_name": device_name,
                "model": model,
            },
        )
