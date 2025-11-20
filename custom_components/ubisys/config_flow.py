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
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er

from .const import (
    BALLAST_LEVEL_MAX,
    BALLAST_LEVEL_MIN,
    CONF_DEVICE_ID,
    CONF_DEVICE_IEEE,
    CONF_INPUT_CONFIG_PRESET,
    CONF_SHADE_TYPE,
    CONF_ZHA_CONFIG_ENTRY_ID,
    DOMAIN,
    OPTION_VERBOSE_INFO_LOGGING,
    OPTION_VERBOSE_INPUT_LOGGING,
    PHASE_MODES,
    SERVICE_TUNE_J1_ADVANCED,
    SHADE_TYPES,
    get_device_type,
)
from .d1_config import (
    async_configure_ballast,
    async_configure_phase_mode,
)
from .input_config import (
    InputActionBuilder,
    InputConfigPreset,
    InputConfigPresets,
    async_apply_input_config,
)
from .logtools import info_banner

_LOGGER = logging.getLogger(__name__)


class UbisysConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):  # type: ignore[call-arg]
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
                    vol.Required(CONF_SHADE_TYPE, default="roller"): vol.In(
                        SHADE_TYPES
                    ),
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
            # D1 devices: Create entry, then Options Flow provides advanced config
            zha_config_entry_id = await self._get_zha_config_entry_id()
            if not zha_config_entry_id:
                return self.async_abort(reason="zha_not_found")

            from .helpers import is_verbose_info_logging

            _LOGGER.log(
                logging.INFO if is_verbose_info_logging(self.hass) else logging.DEBUG,
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

        elif device_type == "switch":
            # S1/S1-R devices: Create entry and proceed to input configuration via options
            zha_config_entry_id = await self._get_zha_config_entry_id()
            if not zha_config_entry_id:
                return self.async_abort(reason="zha_not_found")

            from .helpers import is_verbose_info_logging

            _LOGGER.log(
                logging.INFO if is_verbose_info_logging(self.hass) else logging.DEBUG,
                "Creating config entry for S1/S1-R switch: %s",
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
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> UbisysOptionsFlow:
        """Get the options flow for this handler."""
        return UbisysOptionsFlow(config_entry)

    async def _get_zha_config_entry_id(self) -> str | None:
        """Get the ZHA config entry ID."""
        for entry in self.hass.config_entries.async_entries("zha"):
            if entry.state == config_entries.ConfigEntryState.LOADED:
                from typing import cast

                return cast(str, entry.entry_id)
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

            # Extract model (remove any parenthetical suffixes like "(5502)")
            # ZHA may report "J1 (5502)" but we want just "J1"
            model = device_entry.model
            if model and "(" in model:
                model = model.split("(")[0].strip()

            if model not in SUPPORTED_MODELS:
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
                "model": model,  # Use normalized model name
                "name": device_entry.name or f"{device_entry.manufacturer} {model}",
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
        """Top-level options menu: About or Configure."""
        return self.async_show_menu(
            step_id="init",
            menu_options=["about", "configure"],
        )

    async def async_step_about(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """About page with links to docs and issues."""
        if user_input is not None:
            # Exit about
            return self.async_create_entry(title="", data={})

        docs_url = "https://github.com/jihlenburg/homeassistant-ubisys#readme"
        issues_url = "https://github.com/jihlenburg/homeassistant-ubisys/issues"

        data_schema = vol.Schema({})
        return self.async_show_form(
            step_id="about",
            data_schema=data_schema,
            description_placeholders={
                "device_name": self.config_entry.data.get("name", "Ubisys Device"),
                "model": self.config_entry.data.get("model", ""),
                "docs_url": docs_url,
                "issues_url": issues_url,
            },
        )

    async def async_step_configure(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Route to device-specific configuration steps."""
        model = self.config_entry.data.get("model", "")
        device_type = get_device_type(model)

        _LOGGER.debug(
            "Options flow configure: model=%s, device_type=%s",
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

                # Update logging options from form
                new_options = {
                    **self.config_entry.options,
                    OPTION_VERBOSE_INFO_LOGGING: bool(
                        user_input.get(
                            OPTION_VERBOSE_INFO_LOGGING,
                            self.config_entry.options.get(
                                OPTION_VERBOSE_INFO_LOGGING, False
                            ),
                        )
                    ),
                    OPTION_VERBOSE_INPUT_LOGGING: bool(
                        user_input.get(
                            OPTION_VERBOSE_INPUT_LOGGING,
                            self.config_entry.options.get(
                                OPTION_VERBOSE_INPUT_LOGGING, False
                            ),
                        )
                    ),
                }
                self.hass.config_entries.async_update_entry(
                    self.config_entry,
                    options=new_options,
                )

                # Proceed to advanced J1 tuning
                return await self.async_step_j1_advanced()

            # Show current shade type and logging options
            current_shade_type = self.config_entry.data.get(CONF_SHADE_TYPE, "roller")

            data_schema = vol.Schema(
                {
                    vol.Required(CONF_SHADE_TYPE, default=current_shade_type): vol.In(
                        SHADE_TYPES
                    ),
                    vol.Optional(
                        OPTION_VERBOSE_INFO_LOGGING,
                        default=self.config_entry.options.get(
                            OPTION_VERBOSE_INFO_LOGGING, False
                        ),
                    ): bool,
                    vol.Optional(
                        OPTION_VERBOSE_INPUT_LOGGING,
                        default=self.config_entry.options.get(
                            OPTION_VERBOSE_INPUT_LOGGING, False
                        ),
                    ): bool,
                }
            )

            return self.async_show_form(
                step_id="configure",
                data_schema=data_schema,
                description_placeholders={
                    "device_name": self.config_entry.data.get("name", "Ubisys Device"),
                },
            )

        elif device_type == "dimmer":
            return await self.async_step_d1_options()
        elif device_type == "switch":
            return await self.async_step_input_config(user_input)
        else:
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

                from .helpers import is_verbose_info_logging

                _LOGGER.log(
                    (
                        logging.INFO
                        if is_verbose_info_logging(self.hass)
                        else logging.DEBUG
                    ),
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

                _LOGGER.log(
                    (
                        logging.INFO
                        if is_verbose_info_logging(self.hass)
                        else logging.DEBUG
                    ),
                    "✓ Successfully applied input preset '%s' to %s",
                    preset.value,
                    device_name,
                )

                # Update logging options from form (if present)
                new_options = {
                    **self.config_entry.options,
                    OPTION_VERBOSE_INFO_LOGGING: bool(
                        user_input.get(
                            OPTION_VERBOSE_INFO_LOGGING,
                            self.config_entry.options.get(
                                OPTION_VERBOSE_INFO_LOGGING, False
                            ),
                        )
                    ),
                    OPTION_VERBOSE_INPUT_LOGGING: bool(
                        user_input.get(
                            OPTION_VERBOSE_INPUT_LOGGING,
                            self.config_entry.options.get(
                                OPTION_VERBOSE_INPUT_LOGGING, False
                            ),
                        )
                    ),
                }
                self.hass.config_entries.async_update_entry(
                    self.config_entry, options=new_options
                )

                return self.async_create_entry(title="", data={})

            except ValueError:
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

        # Build preset choices (preset_value -> "Name") and info lines for description
        # The dropdown shows short names, while the description shows full explanations
        preset_choices = {}
        preset_info_lines = []
        for preset in available_presets:
            name, description = InputConfigPresets.get_preset_info(preset)
            preset_choices[preset.value] = f"{name}"
            # Build markdown-formatted info line for description
            preset_info_lines.append(f"• **{name}**: {description}")

        # Get current preset (if configured)
        current_preset = self.config_entry.data.get(CONF_INPUT_CONFIG_PRESET)
        if current_preset and current_preset in preset_choices:
            default_preset = current_preset
        else:
            # Default to first preset
            default_preset = available_presets[0].value

        data_schema = vol.Schema(
            {
                vol.Required(CONF_INPUT_CONFIG_PRESET, default=default_preset): vol.In(
                    preset_choices
                ),
                vol.Optional(
                    OPTION_VERBOSE_INFO_LOGGING,
                    default=self.config_entry.options.get(
                        OPTION_VERBOSE_INFO_LOGGING, False
                    ),
                ): bool,
                vol.Optional(
                    OPTION_VERBOSE_INPUT_LOGGING,
                    default=self.config_entry.options.get(
                        OPTION_VERBOSE_INPUT_LOGGING, False
                    ),
                ): bool,
            }
        )

        return self.async_show_form(
            step_id="input_config",
            data_schema=data_schema,
            errors=errors,
            description_placeholders={
                "device_name": device_name,
                "model": model,
                "preset_info": "\n".join(preset_info_lines),
            },
        )

    async def async_step_d1_options(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Advanced D1 options: phase mode and ballast min/max.

        After applying, continues to the input configuration step.
        """
        errors: dict[str, str] = {}

        model = self.config_entry.data.get("model", "")
        # device_ieee = self.config_entry.data.get(CONF_DEVICE_IEEE)
        entity_name = self.config_entry.data.get("name", "Device")

        if model not in ("D1", "D1-R"):
            return self.async_abort(reason="no_options")

        if user_input is not None:
            # Apply phase mode if provided
            phase_mode = user_input.get("phase_mode")
            try:
                applied: dict[str, str | int] = {}
                light_entity = self._find_entity_id(
                    self.config_entry.entry_id, domain="light"
                )
                if phase_mode:
                    await async_configure_phase_mode(
                        self.hass,
                        entity_id=light_entity,
                        phase_mode=phase_mode,
                    )
                    applied["phase_mode"] = phase_mode
                # Apply ballast if provided
                min_level = user_input.get("min_level")
                max_level = user_input.get("max_level")
                if min_level is not None or max_level is not None:
                    await async_configure_ballast(
                        self.hass,
                        entity_id=light_entity,
                        min_level=min_level,
                        max_level=max_level,
                    )
                    if min_level is not None:
                        applied["min_level"] = min_level
                    if max_level is not None:
                        applied["max_level"] = max_level
                if applied:
                    info_banner(_LOGGER, "D1 Options Applied", **applied)
                # Update logging options from form
                new_options = {
                    **self.config_entry.options,
                    OPTION_VERBOSE_INFO_LOGGING: bool(
                        user_input.get(
                            OPTION_VERBOSE_INFO_LOGGING,
                            self.config_entry.options.get(
                                OPTION_VERBOSE_INFO_LOGGING, False
                            ),
                        )
                    ),
                    OPTION_VERBOSE_INPUT_LOGGING: bool(
                        user_input.get(
                            OPTION_VERBOSE_INPUT_LOGGING,
                            self.config_entry.options.get(
                                OPTION_VERBOSE_INPUT_LOGGING, False
                            ),
                        )
                    ),
                }
                self.hass.config_entries.async_update_entry(
                    self.config_entry, options=new_options
                )
                # Proceed to input config step
                return await self.async_step_input_config(None)
            except Exception as err:
                _LOGGER.error("Failed to apply D1 options: %s", err, exc_info=True)
                errors["base"] = "config_write_failed"

        # Build schema (include logging toggles)
        data_schema = vol.Schema(
            {
                vol.Optional("phase_mode", default="automatic"): vol.In(
                    list(PHASE_MODES.keys())
                ),
                vol.Optional("min_level"): vol.All(
                    vol.Coerce(int),
                    vol.Range(min=BALLAST_LEVEL_MIN, max=BALLAST_LEVEL_MAX),
                ),
                vol.Optional("max_level"): vol.All(
                    vol.Coerce(int),
                    vol.Range(min=BALLAST_LEVEL_MIN, max=BALLAST_LEVEL_MAX),
                ),
                vol.Optional(
                    OPTION_VERBOSE_INFO_LOGGING,
                    default=self.config_entry.options.get(
                        OPTION_VERBOSE_INFO_LOGGING, False
                    ),
                ): bool,
                vol.Optional(
                    OPTION_VERBOSE_INPUT_LOGGING,
                    default=self.config_entry.options.get(
                        OPTION_VERBOSE_INPUT_LOGGING, False
                    ),
                ): bool,
            }
        )

        return self.async_show_form(
            step_id="d1_options",
            data_schema=data_schema,
            errors=errors,
            description_placeholders={
                "device_name": entity_name,
                "model": model,
            },
        )

    def _find_entity_id(self, config_entry_id: str, domain: str) -> str:
        """Find entity_id for a given config entry and domain (helper)."""
        entity_registry = er.async_get(self.hass)
        entries = er.async_entries_for_config_entry(entity_registry, config_entry_id)
        for entry in entries:
            if entry.domain == domain:
                from typing import cast

                return cast(str, entry.entity_id)
        raise HomeAssistantError(f"No {domain} entity found for options flow")

    async def async_step_j1_advanced(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Advanced tuning for J1 via options flow (wraps service).

        After completing advanced tuning, continues to input configuration
        step where users can configure physical button behavior presets.

        Flow: configure → j1_advanced → input_config
        """
        errors: dict[str, str] = {}

        model = self.config_entry.data.get("model", "")
        if get_device_type(model) != "window_covering":
            return self.async_abort(reason="no_options")

        entity_id = self._find_entity_id(self.config_entry.entry_id, domain="cover")

        if user_input is not None:
            data: dict[str, Any] = {"entity_id": entity_id}
            for key in (
                "turnaround_guard_time",
                "inactive_power_threshold",
                "startup_steps",
                "additional_steps",
            ):
                if user_input.get(key) is not None:
                    data[key] = user_input[key]
            try:
                # Only call service if any parameters were provided
                if len(data) > 1:  # More than just entity_id
                    await self.hass.services.async_call(
                        DOMAIN, SERVICE_TUNE_J1_ADVANCED, data, blocking=True
                    )
                # Continue to input configuration step
                return await self.async_step_input_config(None)
            except Exception as err:
                _LOGGER.error("Failed to tune J1: %s", err, exc_info=True)
                errors["base"] = "config_write_failed"

        data_schema = vol.Schema(
            {
                vol.Optional("turnaround_guard_time"): vol.All(
                    vol.Coerce(int), vol.Range(min=0, max=65535)
                ),
                vol.Optional("inactive_power_threshold"): vol.All(
                    vol.Coerce(int), vol.Range(min=0, max=65535)
                ),
                vol.Optional("startup_steps"): vol.All(
                    vol.Coerce(int), vol.Range(min=0, max=65535)
                ),
                vol.Optional("additional_steps"): vol.All(
                    vol.Coerce(int), vol.Range(min=0, max=100)
                ),
            }
        )
        return self.async_show_form(
            step_id="j1_advanced",
            data_schema=data_schema,
            errors=errors,
            description_placeholders={
                "device_name": self.config_entry.data.get("name", "Ubisys Device"),
            },
        )
