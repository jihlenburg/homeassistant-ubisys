"""Service registration for Ubisys integration.

This module registers all device-specific services:
- J1: Calibration, advanced tuning
- D1: Phase mode, ballast configuration
- System: Orphan cleanup
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import Any

import voluptuous as vol
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv

from .cleanup import async_cleanup_orphans
from .const import (
    DOMAIN,
    SERVICE_CALIBRATE_J1,
    SERVICE_CONFIGURE_D1_BALLAST,
    SERVICE_CONFIGURE_D1_ON_LEVEL,
    SERVICE_CONFIGURE_D1_PHASE_MODE,
    SERVICE_CONFIGURE_D1_STARTUP,
    SERVICE_CONFIGURE_D1_TRANSITION,
    SERVICE_GET_D1_STATUS,
    SERVICE_TUNE_J1_ADVANCED,
)
from .d1_config import (
    async_configure_ballast,
    async_configure_on_level,
    async_configure_phase_mode,
    async_configure_startup,
    async_configure_transition_time,
    async_get_status,
)
from .helpers import is_verbose_info_logging
from .j1_calibration import async_calibrate_j1, async_tune_j1

_LOGGER = logging.getLogger(__name__)


def async_setup_services(hass: HomeAssistant) -> None:
    """Register all Ubisys services."""

    # -------------------------------------------------------------------------
    # J1 Calibration Service
    # -------------------------------------------------------------------------
    _LOGGER.debug("Registering J1 calibration service: %s", SERVICE_CALIBRATE_J1)

    async def _calibrate_j1_handler(call: ServiceCall) -> None:
        """Wrapper to inject hass into calibration handler."""
        await async_calibrate_j1(hass, call)

    hass.services.async_register(
        DOMAIN,
        SERVICE_CALIBRATE_J1,
        _calibrate_j1_handler,
        schema=vol.Schema(
            {
                vol.Required("entity_id"): cv.entity_ids,
                vol.Optional("test_mode", default=False): cv.boolean,
            }
        ),
    )

    # -------------------------------------------------------------------------
    # J1 Advanced Tuning Service
    # -------------------------------------------------------------------------
    _LOGGER.debug(
        "Registering J1 advanced tuning service: %s", SERVICE_TUNE_J1_ADVANCED
    )

    async def _tune_j1_handler(call: ServiceCall) -> None:
        """Wrapper to inject hass into tuning handler."""
        await async_tune_j1(hass, call)

    hass.services.async_register(
        DOMAIN,
        SERVICE_TUNE_J1_ADVANCED,
        _tune_j1_handler,
        schema=vol.Schema(
            {
                vol.Required("entity_id"): cv.entity_ids,
                vol.Optional("turnaround_guard_time"): cv.positive_int,
                vol.Optional("inactive_power_threshold"): cv.positive_int,
                vol.Optional("startup_steps"): cv.positive_int,
                vol.Optional("additional_steps"): vol.All(
                    vol.Coerce(int), vol.Range(min=0, max=100)
                ),
                vol.Optional("input_actions"): cv.string,
            }
        ),
    )

    # -------------------------------------------------------------------------
    # D1 Configuration Services
    # -------------------------------------------------------------------------
    _LOGGER.debug(
        "Registering D1 phase mode service: %s", SERVICE_CONFIGURE_D1_PHASE_MODE
    )

    async def _configure_phase_mode_handler(call: ServiceCall) -> None:
        """Wrapper to inject hass and extract parameters from call."""
        entity_ids = _normalize_entity_ids(call.data.get("entity_id"))
        phase_mode = call.data.get("phase_mode")
        if phase_mode is None:
            raise HomeAssistantError("Missing required parameter: phase_mode")

        async def runner(entity_id: str) -> None:
            await async_configure_phase_mode(hass, entity_id, phase_mode)

        await _run_multi_entity_service(entity_ids, runner)

    hass.services.async_register(
        DOMAIN,
        SERVICE_CONFIGURE_D1_PHASE_MODE,
        _configure_phase_mode_handler,
        schema=vol.Schema(
            {
                vol.Required("entity_id"): cv.entity_ids,
                vol.Required("phase_mode"): vol.In(["automatic", "forward", "reverse"]),
            }
        ),
    )

    _LOGGER.debug("Registering D1 ballast service: %s", SERVICE_CONFIGURE_D1_BALLAST)

    async def _configure_ballast_handler(call: ServiceCall) -> None:
        """Wrapper to inject hass and extract parameters from call."""
        entity_ids = _normalize_entity_ids(call.data.get("entity_id"))
        min_level = call.data.get("min_level")
        max_level = call.data.get("max_level")

        async def runner(entity_id: str) -> None:
            await async_configure_ballast(hass, entity_id, min_level, max_level)

        await _run_multi_entity_service(entity_ids, runner)

    hass.services.async_register(
        DOMAIN,
        SERVICE_CONFIGURE_D1_BALLAST,
        _configure_ballast_handler,
        schema=vol.Schema(
            {
                vol.Required("entity_id"): cv.entity_ids,
                vol.Optional("min_level"): vol.All(
                    vol.Coerce(int), vol.Range(min=1, max=254)
                ),
                vol.Optional("max_level"): vol.All(
                    vol.Coerce(int), vol.Range(min=1, max=254)
                ),
            }
        ),
    )

    # D1 Transition Time Service
    _LOGGER.debug(
        "Registering D1 transition time service: %s", SERVICE_CONFIGURE_D1_TRANSITION
    )

    async def _configure_transition_handler(call: ServiceCall) -> None:
        """Wrapper to inject hass and extract parameters from call."""
        entity_ids = _normalize_entity_ids(call.data.get("entity_id"))
        transition_time = call.data.get("transition_time")
        if transition_time is None:
            raise HomeAssistantError("Missing required parameter: transition_time")

        async def runner(entity_id: str) -> None:
            await async_configure_transition_time(hass, entity_id, transition_time)

        await _run_multi_entity_service(entity_ids, runner)

    hass.services.async_register(
        DOMAIN,
        SERVICE_CONFIGURE_D1_TRANSITION,
        _configure_transition_handler,
        schema=vol.Schema(
            {
                vol.Required("entity_id"): cv.entity_ids,
                vol.Required("transition_time"): vol.All(
                    vol.Coerce(int), vol.Range(min=0, max=65535)
                ),
            }
        ),
    )

    # D1 On Level Service
    _LOGGER.debug("Registering D1 on level service: %s", SERVICE_CONFIGURE_D1_ON_LEVEL)

    async def _configure_on_level_handler(call: ServiceCall) -> None:
        """Wrapper to inject hass and extract parameters from call."""
        entity_ids = _normalize_entity_ids(call.data.get("entity_id"))
        on_level = call.data.get("on_level")
        startup_level = call.data.get("startup_level")

        async def runner(entity_id: str) -> None:
            await async_configure_on_level(hass, entity_id, on_level, startup_level)

        await _run_multi_entity_service(entity_ids, runner)

    hass.services.async_register(
        DOMAIN,
        SERVICE_CONFIGURE_D1_ON_LEVEL,
        _configure_on_level_handler,
        schema=vol.Schema(
            {
                vol.Required("entity_id"): cv.entity_ids,
                vol.Optional("on_level"): vol.All(
                    vol.Coerce(int), vol.Range(min=1, max=255)
                ),
                vol.Optional("startup_level"): vol.All(
                    vol.Coerce(int), vol.Range(min=1, max=255)
                ),
            }
        ),
    )

    # D1 Startup Behavior Service
    _LOGGER.debug("Registering D1 startup service: %s", SERVICE_CONFIGURE_D1_STARTUP)

    async def _configure_startup_handler(call: ServiceCall) -> None:
        """Wrapper to inject hass and extract parameters from call."""
        entity_ids = _normalize_entity_ids(call.data.get("entity_id"))
        startup_on_off = call.data.get("startup_on_off")
        if startup_on_off is None:
            raise HomeAssistantError("Missing required parameter: startup_on_off")

        async def runner(entity_id: str) -> None:
            await async_configure_startup(hass, entity_id, startup_on_off)

        await _run_multi_entity_service(entity_ids, runner)

    hass.services.async_register(
        DOMAIN,
        SERVICE_CONFIGURE_D1_STARTUP,
        _configure_startup_handler,
        schema=vol.Schema(
            {
                vol.Required("entity_id"): cv.entity_ids,
                vol.Required("startup_on_off"): vol.In(
                    ["off", "on", "toggle", "previous"]
                ),
            }
        ),
    )

    # D1 Status Read Service
    _LOGGER.debug("Registering D1 status service: %s", SERVICE_GET_D1_STATUS)

    async def _get_status_handler(call: ServiceCall) -> dict[str, int | str | bool]:
        """Wrapper to inject hass and return status."""
        entity_id = call.data.get("entity_id")
        if entity_id is None:
            raise HomeAssistantError("Missing required parameter: entity_id")

        # Handle both single entity and list (take first)
        if isinstance(entity_id, (list, tuple)):
            entity_id = entity_id[0]

        return await async_get_status(hass, entity_id)

    hass.services.async_register(
        DOMAIN,
        SERVICE_GET_D1_STATUS,
        _get_status_handler,
        schema=vol.Schema(
            {
                vol.Required("entity_id"): cv.entity_id,
            }
        ),
        supports_response="optional",
    )

    # -------------------------------------------------------------------------
    # Orphan Cleanup Service
    # -------------------------------------------------------------------------
    _LOGGER.debug("Registering orphan cleanup service: ubisys.cleanup_orphans")

    async def _cleanup_orphans_service(call: ServiceCall) -> None:
        """Clean up orphaned Ubisys devices and entities."""
        result = await async_cleanup_orphans(hass, call)

        dry_run = result.get("dry_run", False)
        devices_count = len(result.get("orphaned_devices", []))
        entities_count = len(result.get("orphaned_entities", []))

        if dry_run:
            # Dry run - show what would be cleaned
            _LOGGER.info(
                "Dry run: Found %d orphaned devices and %d orphaned entities",
                devices_count,
                entities_count,
            )

            try:
                message = f"Found {devices_count} orphaned devices and {entities_count} orphaned entities.\n"
                message += "Run without dry_run=true to remove them."

                await hass.services.async_call(
                    "persistent_notification",
                    "create",
                    {
                        "message": message,
                        "title": "Ubisys Cleanup Preview",
                        "notification_id": "ubisys_cleanup_preview",
                    },
                )
            except Exception:
                _LOGGER.debug("Could not create notification", exc_info=True)
        else:
            # Actual cleanup - show results
            _LOGGER.log(
                logging.INFO if is_verbose_info_logging(hass) else logging.DEBUG,
                "Cleanup completed: removed %d devices and %d entities",
                devices_count,
                entities_count,
            )

            if devices_count > 0 or entities_count > 0:
                try:
                    message = f"Removed {devices_count} orphaned devices and {entities_count} orphaned entities."

                    await hass.services.async_call(
                        "persistent_notification",
                        "create",
                        {
                            "message": message,
                            "title": "Ubisys Cleanup Complete",
                            "notification_id": "ubisys_cleanup_complete",
                        },
                    )
                except Exception:
                    _LOGGER.debug("Could not create notification", exc_info=True)

    hass.services.async_register(
        DOMAIN,
        "cleanup_orphans",
        _cleanup_orphans_service,
        schema=vol.Schema(
            {
                vol.Optional("dry_run", default=False): cv.boolean,
            }
        ),
    )

    _LOGGER.log(
        logging.INFO if is_verbose_info_logging(hass) else logging.DEBUG,
        "Registered Ubisys services",
    )


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------


def _normalize_entity_ids(raw_entity_id: Any) -> list[str]:
    """Normalize service entity_id payload into a list of strings."""
    if raw_entity_id is None:
        raise HomeAssistantError("Missing required parameter: entity_id")
    if isinstance(raw_entity_id, str):
        if not raw_entity_id:
            raise HomeAssistantError("entity_id cannot be empty")
        return [raw_entity_id]
    if isinstance(raw_entity_id, (list, tuple, set)):
        if not raw_entity_id:
            raise HomeAssistantError("entity_id list cannot be empty")
        normalized: list[str] = []
        for idx, entity_id in enumerate(raw_entity_id, start=1):
            if not isinstance(entity_id, str) or not entity_id:
                raise HomeAssistantError(
                    f"entity_id entries must be non-empty strings (entry {idx})"
                )
            normalized.append(entity_id)
        return normalized
    raise HomeAssistantError(
        f"entity_id must be a string or list of strings, got {type(raw_entity_id).__name__}"
    )


async def _run_multi_entity_service(
    entity_ids: list[str],
    runner: Callable[[str], Awaitable[None]],
) -> None:
    """Run a service handler for one or more entities with aggregated errors."""
    successes: list[str] = []
    failures: dict[str, str] = {}
    for idx, entity_id in enumerate(entity_ids, start=1):
        _LOGGER.debug(
            "Processing multi-entity service request %d/%d: %s",
            idx,
            len(entity_ids),
            entity_id,
        )
        try:
            await runner(entity_id)
            successes.append(entity_id)
        except HomeAssistantError as err:
            failures[entity_id] = str(err)
        except Exception as err:  # pragma: no cover - defensive guardrail
            _LOGGER.exception("Service handler raised unexpectedly for %s", entity_id)
            failures[entity_id] = str(err)

    if failures:
        summary = "; ".join(f"{entity}: {error}" for entity, error in failures.items())
        if successes:
            raise HomeAssistantError(
                "Service completed with partial failures. "
                f"Successful: {successes}. Failed: {summary}"
            )
        raise HomeAssistantError(f"Service failed for all entities: {summary}")
