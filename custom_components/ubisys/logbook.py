"""Logbook integration for Ubisys events."""

from __future__ import annotations

from typing import Any

from homeassistant.components.logbook import (  # type: ignore
    ACTION_CHANGE,
    async_describe_event,
)
from homeassistant.core import HomeAssistant

from .const import EVENT_UBISYS_CALIBRATION_COMPLETE, EVENT_UBISYS_INPUT


def async_describe_events(hass: HomeAssistant, async_describe_event: Any) -> None:
    """Describe Ubisys events for the logbook."""

    async_describe_event(
        "ubisys",
        EVENT_UBISYS_CALIBRATION_COMPLETE,
        "Ubisys calibration completed ({shade_type}) in {duration_s}s",
        ACTION_CHANGE,
    )

    async_describe_event(
        "ubisys",
        EVENT_UBISYS_INPUT,
        "Ubisys input {press_type} on input {input_number}",
        ACTION_CHANGE,
    )

