"""Tests for services helper functions."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.exceptions import HomeAssistantError

from custom_components.ubisys import services as services_mod

# =============================================================================
# _normalize_entity_ids tests
# =============================================================================


def test_normalize_entity_ids_string():
    """Single string entity_id is normalized to list."""
    result = services_mod._normalize_entity_ids("light.test")
    assert result == ["light.test"]


def test_normalize_entity_ids_list():
    """List of entity_ids is passed through."""
    result = services_mod._normalize_entity_ids(["light.one", "light.two"])
    assert result == ["light.one", "light.two"]


def test_normalize_entity_ids_tuple():
    """Tuple of entity_ids is converted to list."""
    result = services_mod._normalize_entity_ids(("light.one", "light.two"))
    assert result == ["light.one", "light.two"]


def test_normalize_entity_ids_set():
    """Set of entity_ids is converted to list."""
    result = services_mod._normalize_entity_ids({"light.one"})
    assert "light.one" in result


def test_normalize_entity_ids_none_raises():
    """None entity_id raises HomeAssistantError."""
    with pytest.raises(HomeAssistantError, match="Missing required parameter"):
        services_mod._normalize_entity_ids(None)


def test_normalize_entity_ids_empty_string_raises():
    """Empty string entity_id raises HomeAssistantError."""
    with pytest.raises(HomeAssistantError, match="entity_id cannot be empty"):
        services_mod._normalize_entity_ids("")


def test_normalize_entity_ids_empty_list_raises():
    """Empty list raises HomeAssistantError."""
    with pytest.raises(HomeAssistantError, match="entity_id list cannot be empty"):
        services_mod._normalize_entity_ids([])


def test_normalize_entity_ids_empty_tuple_raises():
    """Empty tuple raises HomeAssistantError."""
    with pytest.raises(HomeAssistantError, match="entity_id list cannot be empty"):
        services_mod._normalize_entity_ids(())


def test_normalize_entity_ids_invalid_type_raises():
    """Invalid type raises HomeAssistantError."""
    with pytest.raises(HomeAssistantError, match="must be a string or list"):
        services_mod._normalize_entity_ids(123)


def test_normalize_entity_ids_list_with_non_string_raises():
    """List with non-string entry raises HomeAssistantError."""
    with pytest.raises(HomeAssistantError, match="must be non-empty strings"):
        services_mod._normalize_entity_ids(["light.one", 123])


def test_normalize_entity_ids_list_with_empty_string_raises():
    """List with empty string raises HomeAssistantError."""
    with pytest.raises(HomeAssistantError, match="must be non-empty strings"):
        services_mod._normalize_entity_ids(["light.one", ""])


# =============================================================================
# _run_multi_entity_service tests
# =============================================================================


@pytest.mark.asyncio
async def test_run_multi_entity_service_success():
    """Successful service call for all entities."""
    runner = AsyncMock()

    await services_mod._run_multi_entity_service(
        ["light.one", "light.two"],
        runner,
    )

    assert runner.await_count == 2
    runner.assert_any_await("light.one")
    runner.assert_any_await("light.two")


@pytest.mark.asyncio
async def test_run_multi_entity_service_partial_failure():
    """Service call with partial failures raises with summary."""

    async def runner(entity_id):
        if entity_id == "light.one":
            return  # Success
        raise HomeAssistantError(f"Failed for {entity_id}")

    with pytest.raises(HomeAssistantError) as exc_info:
        await services_mod._run_multi_entity_service(
            ["light.one", "light.two"],
            runner,
        )

    error = str(exc_info.value)
    assert "partial failures" in error
    assert "light.one" in error  # Listed as successful
    assert "light.two" in error  # Listed as failed


@pytest.mark.asyncio
async def test_run_multi_entity_service_all_failure():
    """Service call with all failures raises with summary."""

    async def runner(entity_id):
        raise HomeAssistantError(f"Failed for {entity_id}")

    with pytest.raises(HomeAssistantError) as exc_info:
        await services_mod._run_multi_entity_service(
            ["light.one", "light.two"],
            runner,
        )

    error = str(exc_info.value)
    assert "failed for all entities" in error
    assert "light.one" in error
    assert "light.two" in error


@pytest.mark.asyncio
async def test_run_multi_entity_service_single_entity():
    """Service call for single entity."""
    runner = AsyncMock()

    await services_mod._run_multi_entity_service(
        ["light.one"],
        runner,
    )

    runner.assert_awaited_once_with("light.one")


@pytest.mark.asyncio
async def test_run_multi_entity_service_empty_list():
    """Service call with empty list does nothing."""
    runner = AsyncMock()

    await services_mod._run_multi_entity_service([], runner)

    runner.assert_not_awaited()


# =============================================================================
# async_setup_services tests
# =============================================================================


def _make_hass() -> SimpleNamespace:
    """Return a lightweight hass surrogate for service registration tests."""
    hass = SimpleNamespace()
    hass.services = MagicMock()
    hass.services.async_register = MagicMock()
    return hass


def test_async_setup_services_registers_all_services():
    """Test that async_setup_services registers all expected services."""
    hass = _make_hass()

    services_mod.async_setup_services(hass)

    # Get all registered service names
    registered_calls = hass.services.async_register.call_args_list
    registered_services = [call[0][1] for call in registered_calls]

    # Verify all expected services are registered
    assert "calibrate_j1" in registered_services
    assert "tune_j1_advanced" in registered_services
    assert "configure_d1_phase_mode" in registered_services
    assert "configure_d1_ballast" in registered_services
    assert "configure_d1_transition" in registered_services
    assert "configure_d1_on_level" in registered_services
    assert "configure_d1_startup" in registered_services
    assert "get_d1_status" in registered_services
    assert "cleanup_orphans" in registered_services


def test_async_setup_services_uses_correct_domain():
    """Test that all services are registered under the ubisys domain."""
    hass = _make_hass()

    services_mod.async_setup_services(hass)

    # All calls should use DOMAIN as first argument
    for call in hass.services.async_register.call_args_list:
        assert call[0][0] == "ubisys"


@pytest.mark.asyncio
async def test_calibrate_j1_handler_calls_function(monkeypatch):
    """Test J1 calibration service handler calls the right function."""
    hass = _make_hass()
    mock_calibrate = AsyncMock()
    monkeypatch.setattr(
        "custom_components.ubisys.services.async_calibrate_j1",
        mock_calibrate,
    )

    services_mod.async_setup_services(hass)

    # Get the registered handler
    handler = None
    for call in hass.services.async_register.call_args_list:
        if call[0][1] == "calibrate_j1":
            handler = call[0][2]
            break

    assert handler is not None

    # Call the handler
    mock_call = MagicMock()
    await handler(mock_call)

    mock_calibrate.assert_awaited_once_with(hass, mock_call)


@pytest.mark.asyncio
async def test_tune_j1_handler_calls_function(monkeypatch):
    """Test J1 tuning service handler calls the right function."""
    hass = _make_hass()
    mock_tune = AsyncMock()
    monkeypatch.setattr(
        "custom_components.ubisys.services.async_tune_j1",
        mock_tune,
    )

    services_mod.async_setup_services(hass)

    # Get the registered handler
    handler = None
    for call in hass.services.async_register.call_args_list:
        if call[0][1] == "tune_j1_advanced":
            handler = call[0][2]
            break

    assert handler is not None

    # Call the handler
    mock_call = MagicMock()
    await handler(mock_call)

    mock_tune.assert_awaited_once_with(hass, mock_call)


@pytest.mark.asyncio
async def test_configure_phase_mode_handler(monkeypatch):
    """Test phase mode service handler extracts parameters correctly."""
    hass = _make_hass()
    mock_configure = AsyncMock()
    monkeypatch.setattr(
        "custom_components.ubisys.services.async_configure_phase_mode",
        mock_configure,
    )

    services_mod.async_setup_services(hass)

    # Get the registered handler
    handler = None
    for call in hass.services.async_register.call_args_list:
        if call[0][1] == "configure_d1_phase_mode":
            handler = call[0][2]
            break

    assert handler is not None

    # Call the handler with data
    mock_call = MagicMock()
    mock_call.data = {"entity_id": "light.test_d1", "phase_mode": "forward"}
    await handler(mock_call)

    mock_configure.assert_awaited_once_with(hass, "light.test_d1", "forward")


@pytest.mark.asyncio
async def test_configure_phase_mode_handler_missing_param():
    """Test phase mode handler raises on missing phase_mode."""
    hass = _make_hass()

    services_mod.async_setup_services(hass)

    # Get the registered handler
    handler = None
    for call in hass.services.async_register.call_args_list:
        if call[0][1] == "configure_d1_phase_mode":
            handler = call[0][2]
            break

    # Call without phase_mode
    mock_call = MagicMock()
    mock_call.data = {"entity_id": "light.test_d1"}

    with pytest.raises(HomeAssistantError, match="Missing required parameter"):
        await handler(mock_call)


@pytest.mark.asyncio
async def test_configure_ballast_handler(monkeypatch):
    """Test ballast service handler extracts parameters correctly."""
    hass = _make_hass()
    mock_configure = AsyncMock()
    monkeypatch.setattr(
        "custom_components.ubisys.services.async_configure_ballast",
        mock_configure,
    )

    services_mod.async_setup_services(hass)

    # Get the registered handler
    handler = None
    for call in hass.services.async_register.call_args_list:
        if call[0][1] == "configure_d1_ballast":
            handler = call[0][2]
            break

    assert handler is not None

    # Call the handler with data
    mock_call = MagicMock()
    mock_call.data = {"entity_id": "light.test_d1", "min_level": 10, "max_level": 200}
    await handler(mock_call)

    mock_configure.assert_awaited_once_with(hass, "light.test_d1", 10, 200)


@pytest.mark.asyncio
async def test_configure_transition_handler(monkeypatch):
    """Test transition time service handler extracts parameters correctly."""
    hass = _make_hass()
    mock_configure = AsyncMock()
    monkeypatch.setattr(
        "custom_components.ubisys.services.async_configure_transition_time",
        mock_configure,
    )

    services_mod.async_setup_services(hass)

    # Get the registered handler
    handler = None
    for call in hass.services.async_register.call_args_list:
        if call[0][1] == "configure_d1_transition":
            handler = call[0][2]
            break

    assert handler is not None

    # Call the handler with data
    mock_call = MagicMock()
    mock_call.data = {"entity_id": "light.test_d1", "transition_time": 20}
    await handler(mock_call)

    mock_configure.assert_awaited_once_with(hass, "light.test_d1", 20)


@pytest.mark.asyncio
async def test_configure_transition_handler_missing_param():
    """Test transition handler raises on missing transition_time."""
    hass = _make_hass()

    services_mod.async_setup_services(hass)

    # Get the registered handler
    handler = None
    for call in hass.services.async_register.call_args_list:
        if call[0][1] == "configure_d1_transition":
            handler = call[0][2]
            break

    # Call without transition_time
    mock_call = MagicMock()
    mock_call.data = {"entity_id": "light.test_d1"}

    with pytest.raises(HomeAssistantError, match="Missing required parameter"):
        await handler(mock_call)


@pytest.mark.asyncio
async def test_configure_on_level_handler(monkeypatch):
    """Test on level service handler extracts parameters correctly."""
    hass = _make_hass()
    mock_configure = AsyncMock()
    monkeypatch.setattr(
        "custom_components.ubisys.services.async_configure_on_level",
        mock_configure,
    )

    services_mod.async_setup_services(hass)

    # Get the registered handler
    handler = None
    for call in hass.services.async_register.call_args_list:
        if call[0][1] == "configure_d1_on_level":
            handler = call[0][2]
            break

    assert handler is not None

    # Call the handler with data
    mock_call = MagicMock()
    mock_call.data = {
        "entity_id": "light.test_d1",
        "on_level": 128,
        "startup_level": 200,
    }
    await handler(mock_call)

    mock_configure.assert_awaited_once_with(hass, "light.test_d1", 128, 200)


@pytest.mark.asyncio
async def test_configure_startup_handler(monkeypatch):
    """Test startup service handler extracts parameters correctly."""
    hass = _make_hass()
    mock_configure = AsyncMock()
    monkeypatch.setattr(
        "custom_components.ubisys.services.async_configure_startup",
        mock_configure,
    )

    services_mod.async_setup_services(hass)

    # Get the registered handler
    handler = None
    for call in hass.services.async_register.call_args_list:
        if call[0][1] == "configure_d1_startup":
            handler = call[0][2]
            break

    assert handler is not None

    # Call the handler with data
    mock_call = MagicMock()
    mock_call.data = {"entity_id": "light.test_d1", "startup_on_off": "on"}
    await handler(mock_call)

    mock_configure.assert_awaited_once_with(hass, "light.test_d1", "on")


@pytest.mark.asyncio
async def test_configure_startup_handler_missing_param():
    """Test startup handler raises on missing startup_on_off."""
    hass = _make_hass()

    services_mod.async_setup_services(hass)

    # Get the registered handler
    handler = None
    for call in hass.services.async_register.call_args_list:
        if call[0][1] == "configure_d1_startup":
            handler = call[0][2]
            break

    # Call without startup_on_off
    mock_call = MagicMock()
    mock_call.data = {"entity_id": "light.test_d1"}

    with pytest.raises(HomeAssistantError, match="Missing required parameter"):
        await handler(mock_call)


@pytest.mark.asyncio
async def test_get_d1_status_handler(monkeypatch):
    """Test get status service handler calls the right function."""
    hass = _make_hass()
    mock_get_status = AsyncMock(return_value={"status": "ok"})
    monkeypatch.setattr(
        "custom_components.ubisys.services.async_get_status",
        mock_get_status,
    )

    services_mod.async_setup_services(hass)

    # Get the registered handler
    handler = None
    for call in hass.services.async_register.call_args_list:
        if call[0][1] == "get_d1_status":
            handler = call[0][2]
            break

    assert handler is not None

    # Call the handler with data
    mock_call = MagicMock()
    mock_call.data = {"entity_id": "light.test_d1"}
    result = await handler(mock_call)

    mock_get_status.assert_awaited_once_with(hass, "light.test_d1")
    assert result == {"status": "ok"}


@pytest.mark.asyncio
async def test_cleanup_orphans_handler(monkeypatch):
    """Test cleanup orphans service handler calls the right function."""
    hass = _make_hass()
    # Add services.async_call for notification creation
    hass.services.async_call = AsyncMock()

    # Return a properly structured result
    mock_cleanup = AsyncMock(
        return_value={
            "dry_run": False,
            "orphaned_devices": [],
            "orphaned_entities": [],
        }
    )
    monkeypatch.setattr(
        "custom_components.ubisys.services.async_cleanup_orphans",
        mock_cleanup,
    )
    monkeypatch.setattr(
        "custom_components.ubisys.services.is_verbose_info_logging",
        lambda h: False,
    )

    services_mod.async_setup_services(hass)

    # Get the registered handler
    handler = None
    for call in hass.services.async_register.call_args_list:
        if call[0][1] == "cleanup_orphans":
            handler = call[0][2]
            break

    assert handler is not None

    # Call the handler - it returns None, not the result
    mock_call = MagicMock()
    mock_call.data = {}
    await handler(mock_call)

    mock_cleanup.assert_awaited_once_with(hass, mock_call)


@pytest.mark.asyncio
async def test_handler_with_multiple_entities(monkeypatch):
    """Test handler processes multiple entities correctly."""
    hass = _make_hass()
    mock_configure = AsyncMock()
    monkeypatch.setattr(
        "custom_components.ubisys.services.async_configure_phase_mode",
        mock_configure,
    )

    services_mod.async_setup_services(hass)

    # Get the registered handler
    handler = None
    for call in hass.services.async_register.call_args_list:
        if call[0][1] == "configure_d1_phase_mode":
            handler = call[0][2]
            break

    # Call with multiple entities
    mock_call = MagicMock()
    mock_call.data = {
        "entity_id": ["light.d1_one", "light.d1_two"],
        "phase_mode": "forward",
    }
    await handler(mock_call)

    assert mock_configure.await_count == 2
    mock_configure.assert_any_await(hass, "light.d1_one", "forward")
    mock_configure.assert_any_await(hass, "light.d1_two", "forward")
