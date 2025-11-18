"""Diagnostics support for the Ubisys integration.

Exposes redacted configuration and runtime info to help users and developers
troubleshoot issues via Home Assistant's Diagnostics feature.
"""

from __future__ import annotations

import logging
from typing import Any, cast

from homeassistant.components import diagnostics
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .helpers import resolve_zha_gateway

REDACT_KEYS = {"device_ieee"}
_LOGGER = logging.getLogger(__name__)


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry (redacted)."""
    data: dict[str, Any] = {
        "entry": {
            "title": entry.title,
            "version": entry.version,
            "domain": entry.domain,
            "data": dict(entry.data),
            "options": dict(entry.options),
        }
    }

    # Attach basic device info from registry
    try:
        from homeassistant.helpers import device_registry as dr

        dev_reg = dr.async_get(hass)
        device = dev_reg.async_get(entry.data.get("device_id"))
        if device:
            data["device"] = {
                "id": device.id,
                "name": device.name,
                "manufacturer": device.manufacturer,
                "model": device.model,
                "sw_version": device.sw_version,
            }
    except Exception:
        # best effort
        pass

    # Try to include endpoint/cluster snapshot from ZHA and last calibration info
    try:
        zha_data = hass.data.get("zha")
        if zha_data:
            from zigpy.types import EUI64

            gateway = resolve_zha_gateway(zha_data)
            ieee = entry.data.get("device_ieee")
            if ieee and gateway:
                eui = EUI64.convert(ieee)

                # Handle both old API (gateway.application_controller.devices) and new API (gateway.gateway.devices)
                if hasattr(gateway, "application_controller"):
                    # Old API: direct gateway object
                    devices = gateway.application_controller.devices
                elif hasattr(gateway, "gateway"):
                    # New API: ZHAGatewayProxy wrapping gateway
                    devices = gateway.gateway.devices
                else:
                    _LOGGER.debug(
                        "Diagnostics: Gateway has no known device access pattern. Type: %s",
                        type(gateway).__name__,
                    )
                    devices = None

                device = devices.get(eui) if devices else None
                if device:
                    eps: dict[int, Any] = {}
                    for ep_id, ep in device.endpoints.items():
                        eps[int(ep_id)] = {
                            "in_clusters": [hex(cid) for cid in ep.in_clusters.keys()],
                            "out_clusters": [
                                hex(cid) for cid in ep.out_clusters.keys()
                            ],
                        }
                    data["zha_endpoints"] = eps
            elif ieee:
                _LOGGER.debug(
                    "Diagnostics: ZHA gateway unavailable; skipping endpoint dump for %s",
                    ieee,
                )
        # Add last calibration info (if recorded)
        last = (
            hass.data.get(DOMAIN, {})
            .get("calibration_history", {})
            .get(entry.data.get("device_ieee"))
        )
        if last:
            data["last_calibration"] = last
    except Exception:
        # best effort
        pass

    return cast(dict[str, Any], diagnostics.async_redact_data(data, REDACT_KEYS))


async def async_get_device_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry, device: Any
) -> dict[str, Any]:
    """Return diagnostics for a device (redacted)."""
    payload = await async_get_config_entry_diagnostics(hass, entry)
    payload["device_context"] = {
        "ha_device_id": getattr(device, "id", None),
        "identifiers": list(getattr(device, "identifiers", [])),
    }
    return payload
