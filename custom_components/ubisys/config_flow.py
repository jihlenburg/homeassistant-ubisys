"""Config flow for Ubisys integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.components.cover import DOMAIN as COVER_DOMAIN
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import selector

from .const import (
    CONF_SHADE_TYPE,
    CONF_ZHA_ENTITY_ID,
    DOMAIN,
    SHADE_TYPES,
    ShadeType,
)

_LOGGER = logging.getLogger(__name__)


def _get_zha_cover_entities(hass: HomeAssistant) -> dict[str, str]:
    """Get all ZHA cover entities.

    Returns a dict mapping entity_id to friendly name.
    """
    entity_registry = er.async_get(hass)
    entities = {}

    for entity in entity_registry.entities.values():
        # Filter for cover entities from ZHA integration
        if (
            entity.domain == COVER_DOMAIN
            and entity.platform == "zha"
            and not entity.disabled
        ):
            state = hass.states.get(entity.entity_id)
            friendly_name = (
                state.attributes.get("friendly_name", entity.entity_id)
                if state
                else entity.entity_id
            )
            entities[entity.entity_id] = friendly_name

    return entities


class UbisysConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Ubisys."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        # Get available ZHA cover entities
        zha_entities = await self.hass.async_add_executor_job(
            _get_zha_cover_entities, self.hass
        )

        if not zha_entities:
            return self.async_abort(reason="no_zha_covers")

        if user_input is not None:
            zha_entity_id = user_input[CONF_ZHA_ENTITY_ID]
            shade_type = user_input[CONF_SHADE_TYPE]

            # Validate the selected entity exists
            if zha_entity_id not in zha_entities:
                errors[CONF_ZHA_ENTITY_ID] = "entity_not_found"
            else:
                # Check if this ZHA entity is already configured
                await self.async_set_unique_id(zha_entity_id)
                self._abort_if_unique_id_configured()

                # Create the entry
                title = f"Ubisys {zha_entities[zha_entity_id]}"
                return self.async_create_entry(
                    title=title,
                    data={
                        CONF_ZHA_ENTITY_ID: zha_entity_id,
                        CONF_SHADE_TYPE: shade_type,
                    },
                )

        # Build schema with entity selector
        data_schema = vol.Schema(
            {
                vol.Required(CONF_ZHA_ENTITY_ID): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            selector.SelectOptionDict(value=entity_id, label=name)
                            for entity_id, name in sorted(
                                zha_entities.items(), key=lambda x: x[1]
                            )
                        ],
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Required(CONF_SHADE_TYPE, default=ShadeType.ROLLER): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            selector.SelectOptionDict(value=ShadeType.ROLLER, label="Roller Shade"),
                            selector.SelectOptionDict(value=ShadeType.CELLULAR, label="Cellular Shade"),
                            selector.SelectOptionDict(value=ShadeType.VERTICAL, label="Vertical Blind"),
                            selector.SelectOptionDict(value=ShadeType.VENETIAN, label="Venetian Blind"),
                            selector.SelectOptionDict(
                                value=ShadeType.EXTERIOR_VENETIAN, label="Exterior Venetian Blind"
                            ),
                        ],
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> UbisysOptionsFlow:
        """Get the options flow for this handler."""
        return UbisysOptionsFlow(config_entry)


class UbisysOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for Ubisys."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            # Update the shade type
            new_data = {**self.config_entry.data, CONF_SHADE_TYPE: user_input[CONF_SHADE_TYPE]}
            self.hass.config_entries.async_update_entry(
                self.config_entry, data=new_data
            )
            return self.async_create_entry(title="", data={})

        current_shade_type = self.config_entry.data.get(CONF_SHADE_TYPE, ShadeType.ROLLER)

        data_schema = vol.Schema(
            {
                vol.Required(CONF_SHADE_TYPE, default=current_shade_type): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            selector.SelectOptionDict(value=ShadeType.ROLLER, label="Roller Shade"),
                            selector.SelectOptionDict(value=ShadeType.CELLULAR, label="Cellular Shade"),
                            selector.SelectOptionDict(value=ShadeType.VERTICAL, label="Vertical Blind"),
                            selector.SelectOptionDict(value=ShadeType.VENETIAN, label="Venetian Blind"),
                            selector.SelectOptionDict(
                                value=ShadeType.EXTERIOR_VENETIAN, label="Exterior Venetian Blind"
                            ),
                        ],
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
            }
        )

        return self.async_show_form(
            step_id="init",
            data_schema=data_schema,
        )
