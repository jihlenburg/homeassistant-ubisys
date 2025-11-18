"""Unit tests for helper utilities that don't require full HA setup."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import Any, Dict, Tuple
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.exceptions import HomeAssistantError

from custom_components.ubisys import helpers
from custom_components.ubisys.const import DOMAIN


class DummyHass:
    """Very small hass-like container for testing logging flag helpers."""

    def __init__(self, domain_data: Dict[str, Any] | None = None) -> None:
        self.data: Dict[str, Any] | None = domain_data or {}


class FakeCluster:
    """Simple Zigbee cluster double used for async_zcl_command tests."""

    def __init__(self, fail_times: int = 0) -> None:
        self.calls: list[Tuple[str, Tuple[Any, ...], Dict[str, Any]]] = []
        self._fail_times = fail_times

    def __getattr__(self, name: str):  # type: ignore[no-untyped-def]
        """Return a callable that records the command call."""

        async def command_fn(*args: Any, **kwargs: Any) -> None:
            self.calls.append((name, args, kwargs))
            if self._fail_times > 0:
                self._fail_times -= 1
                raise RuntimeError("boom")
            await asyncio.sleep(0)

        return command_fn


def test_extract_model_from_device_handles_suffix():
    device = SimpleNamespace(model="J1-R (5502)")
    assert helpers.extract_model_from_device(device) == "J1-R"


def test_extract_model_from_device_handles_missing_model():
    device = SimpleNamespace(model=None)
    assert helpers.extract_model_from_device(device) is None


def test_extract_ieee_from_device_returns_first_match():
    device = SimpleNamespace(
        identifiers={("other", "abc"), ("zha", "00:11:22:33:44:55:66:77")}
    )
    assert helpers.extract_ieee_from_device(device) == "00:11:22:33:44:55:66:77"


def test_extract_ieee_from_device_returns_none():
    device = SimpleNamespace(identifiers={("other", "abc")})
    assert helpers.extract_ieee_from_device(device) is None


def test_is_verbose_info_logging_prefers_runtime_flags():
    hass = DummyHass({DOMAIN: {"verbose_info_logging": True}})
    assert helpers.is_verbose_info_logging(hass) is True


def test_is_verbose_info_logging_defaults_when_missing_data():
    hass = DummyHass({})
    assert helpers.is_verbose_info_logging(hass) is helpers.VERBOSE_INFO_LOGGING


def test_is_verbose_input_logging_prefers_runtime_flags():
    hass = DummyHass({DOMAIN: {"verbose_input_logging": False}})
    assert helpers.is_verbose_input_logging(hass) is False


def test_is_verbose_input_logging_defaults_on_error():
    hass = DummyHass({})
    hass.data = None  # type: ignore[assignment]
    # Corrupted hass.data should fall back to constant defaults
    assert helpers.is_verbose_input_logging(hass) is helpers.VERBOSE_INPUT_LOGGING


@pytest.mark.asyncio
async def test_validate_ubisys_entity_success():
    states = MagicMock()
    states.get.return_value = SimpleNamespace(state="open")
    hass = SimpleNamespace(states=states)
    entry = SimpleNamespace(platform=DOMAIN, domain="cover")

    registry = MagicMock()
    registry.async_get.return_value = entry

    with patch("custom_components.ubisys.helpers.er.async_get", return_value=registry):
        await helpers.validate_ubisys_entity(
            hass, "cover.test_j1", expected_domain="cover"
        )


@pytest.mark.asyncio
async def test_validate_ubisys_entity_wrong_domain_raises():
    states = MagicMock()
    states.get.return_value = SimpleNamespace(state="open")
    hass = SimpleNamespace(states=states)
    entry = SimpleNamespace(platform=DOMAIN, domain="light")

    registry = MagicMock()
    registry.async_get.return_value = entry

    with patch("custom_components.ubisys.helpers.er.async_get", return_value=registry):
        with pytest.raises(HomeAssistantError, match="wrong domain"):
            await helpers.validate_ubisys_entity(
                hass, "cover.test_j1", expected_domain="cover"
            )


@pytest.mark.asyncio
async def test_validate_ubisys_entity_unavailable_state():
    states = MagicMock()
    states.get.return_value = SimpleNamespace(state="unavailable")
    hass = SimpleNamespace(states=states)
    entry = SimpleNamespace(platform=DOMAIN, domain="cover")

    registry = MagicMock()
    registry.async_get.return_value = entry

    with patch("custom_components.ubisys.helpers.er.async_get", return_value=registry):
        with pytest.raises(HomeAssistantError, match="unavailable"):
            await helpers.validate_ubisys_entity(
                hass, "cover.test_j1", expected_domain="cover"
            )


@pytest.mark.asyncio
async def test_get_entity_device_info_returns_data():
    entry = SimpleNamespace(
        device_id="device-1",
        config_entry_id="entry-1",
    )
    registry = MagicMock()
    registry.async_get.return_value = entry

    config_entry = SimpleNamespace(
        domain=DOMAIN,
        data={"device_ieee": "00:11:22:33:44:55:66:77", "model": "J1"},
    )
    hass = SimpleNamespace(
        config_entries=SimpleNamespace(
            async_get_entry=MagicMock(return_value=config_entry)
        )
    )

    with patch("custom_components.ubisys.helpers.er.async_get", return_value=registry):
        device_id, ieee, model = await helpers.get_entity_device_info(
            hass, "cover.test_j1"
        )
    assert device_id == "device-1"
    assert ieee == "00:11:22:33:44:55:66:77"
    assert model == "J1"


@pytest.mark.asyncio
async def test_get_entity_device_info_validates_config_entry():
    entry = SimpleNamespace(
        device_id="device-1",
        config_entry_id="entry-1",
    )
    registry = MagicMock()
    registry.async_get.return_value = entry

    hass = SimpleNamespace(
        config_entries=SimpleNamespace(async_get_entry=MagicMock(return_value=None))
    )

    with patch("custom_components.ubisys.helpers.er.async_get", return_value=registry):
        with pytest.raises(HomeAssistantError, match="config entry not found"):
            await helpers.get_entity_device_info(hass, "cover.test_j1")


@pytest.mark.asyncio
async def test_get_entity_device_info_requires_model():
    entry = SimpleNamespace(
        device_id="device-1",
        config_entry_id="entry-1",
    )
    registry = MagicMock()
    registry.async_get.return_value = entry

    config_entry = SimpleNamespace(domain=DOMAIN, data={"device_ieee": "00:11"})
    hass = SimpleNamespace(
        config_entries=SimpleNamespace(
            async_get_entry=MagicMock(return_value=config_entry)
        )
    )

    with patch("custom_components.ubisys.helpers.er.async_get", return_value=registry):
        with pytest.raises(HomeAssistantError, match="Device model not found"):
            await helpers.get_entity_device_info(hass, "cover.test_j1")


@pytest.mark.asyncio
async def test_find_zha_entity_for_device_returns_match():
    registry = MagicMock()
    entry = SimpleNamespace(
        platform="zha", domain="cover", entity_id="cover.zha_device"
    )

    with (
        patch("custom_components.ubisys.helpers.er.async_get", return_value=registry),
        patch(
            "custom_components.ubisys.helpers.er.async_entries_for_device",
            return_value=[entry],
        ),
    ):
        entity_id = await helpers.find_zha_entity_for_device(
            SimpleNamespace(), "device-1", "cover"
        )

    assert entity_id == "cover.zha_device"


@pytest.mark.asyncio
async def test_find_zha_entity_for_device_handles_missing():
    registry = MagicMock()
    with (
        patch("custom_components.ubisys.helpers.er.async_get", return_value=registry),
        patch(
            "custom_components.ubisys.helpers.er.async_entries_for_device",
            return_value=[],
        ),
    ):
        entity_id = await helpers.find_zha_entity_for_device(
            SimpleNamespace(), "device-1", "cover"
        )

    assert entity_id is None


@pytest.mark.asyncio
async def test_get_device_setup_cluster_delegates_to_get_cluster():
    mock_cluster = object()
    with patch(
        "custom_components.ubisys.helpers.get_cluster",
        AsyncMock(return_value=mock_cluster),
    ) as mock_get:
        hass = SimpleNamespace()
        result = await helpers.get_device_setup_cluster(hass, "00:11:22:33:44:55:66:77")

    assert result is mock_cluster
    mock_get.assert_awaited_once_with(
        hass,
        "00:11:22:33:44:55:66:77",
        0xFC00,
        232,
        "DeviceSetup",
    )


@pytest.mark.asyncio
async def test_async_zcl_command_success():
    cluster = FakeCluster()
    await helpers.async_zcl_command(cluster, "do_it", 1, 2, retries=0)
    assert cluster.calls == [("do_it", (1, 2), {})]


@pytest.mark.asyncio
async def test_async_zcl_command_eventual_success():
    cluster = FakeCluster(fail_times=1)
    await helpers.async_zcl_command(cluster, "retry", retries=2)
    assert len(cluster.calls) == 2


@pytest.mark.asyncio
async def test_async_zcl_command_retries_and_raises():
    cluster = FakeCluster(fail_times=2)
    with pytest.raises(HomeAssistantError, match="Cluster command failed"):
        await helpers.async_zcl_command(cluster, "fail", retries=1)
    assert len(cluster.calls) == 2
