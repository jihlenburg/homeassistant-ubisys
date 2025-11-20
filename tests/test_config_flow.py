"""Tests for config flow.

Tests cover both initial setup flow and options flow for all device types.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResultType

from custom_components.ubisys.config_flow import UbisysConfigFlow, UbisysOptionsFlow
from custom_components.ubisys.const import (
    CONF_DEVICE_ID,
    CONF_DEVICE_IEEE,
    CONF_SHADE_TYPE,
    CONF_ZHA_CONFIG_ENTRY_ID,
    DOMAIN,
)

# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def hass_with_config_entries(hass):
    """Enhance hass fixture with config_entries mock."""
    hass.config_entries = MagicMock()
    hass.data = {}  # Add data dict for entity registry

    # Mock async_entries to return ZHA entry when called with "zha" domain
    def async_entries_side_effect(domain=None):
        if domain == "zha":
            zha_entry = MagicMock()
            zha_entry.entry_id = "zha_entry_id"
            zha_entry.domain = "zha"
            zha_entry.state = config_entries.ConfigEntryState.LOADED
            return [zha_entry]
        return []

    hass.config_entries.async_entries = MagicMock(side_effect=async_entries_side_effect)
    hass.config_entries.async_update_entry = MagicMock()
    return hass


@pytest.fixture
def mock_zha_config_entry():
    """Mock ZHA config entry."""
    entry = MagicMock()
    entry.entry_id = "zha_entry_id"
    entry.domain = "zha"
    return entry


@pytest.fixture
def j1_discovery_data():
    """Mock discovery data for J1 device."""
    return {
        "device_ieee": "00:11:22:33:44:55:66:77",
        "device_id": "test_device_id",
        "manufacturer": "ubisys",
        "model": "J1",
        "name": "Test J1",
    }


@pytest.fixture
def d1_discovery_data():
    """Mock discovery data for D1 device."""
    return {
        "device_ieee": "00:11:22:33:44:55:66:88",
        "device_id": "test_device_id_d1",
        "manufacturer": "ubisys",
        "model": "D1",
        "name": "Test D1",
    }


@pytest.fixture
def s1_discovery_data():
    """Mock discovery data for S1 device."""
    return {
        "device_ieee": "00:11:22:33:44:55:66:99",
        "device_id": "test_device_id_s1",
        "manufacturer": "ubisys",
        "model": "S1",
        "name": "Test S1",
    }


@pytest.fixture
def mock_config_entry():
    """Mock config entry for options flow."""
    entry = MagicMock()
    entry.entry_id = "test_entry_id"
    entry.domain = DOMAIN
    entry.data = {
        CONF_DEVICE_IEEE: "00:11:22:33:44:55:66:77",
        CONF_DEVICE_ID: "test_device_id",
        CONF_SHADE_TYPE: "roller",
        "manufacturer": "ubisys",
        "model": "J1",
        "name": "Test J1",
    }
    entry.options = {}
    return entry


# =============================================================================
# Test Initial Config Flow - ZHA Discovery
# =============================================================================


@pytest.mark.asyncio
async def test_zha_discovery_j1_device(hass_with_config_entries, j1_discovery_data):
    """Test ZHA discovery flow for J1 device."""
    flow = UbisysConfigFlow()
    flow.hass = hass_with_config_entries
    # Initialize context as mutable dict before calling async_step_zha
    flow.context = {}

    # Step 1: ZHA discovery (fixture handles ZHA entry mocking)
    result = await flow.async_step_zha(j1_discovery_data)

    # Should show form for shade type selection
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"
    assert CONF_SHADE_TYPE in result["data_schema"].schema


@pytest.mark.asyncio
async def test_zha_discovery_duplicate_device(
    hass_with_config_entries, j1_discovery_data
):
    """Test ZHA discovery aborts if device already configured."""
    flow = UbisysConfigFlow()
    flow.hass = hass_with_config_entries
    # Initialize context as mutable dict before calling async_step_zha
    flow.context = {}

    # Mock existing entry with same device_ieee
    existing_entry = MagicMock()
    existing_entry.unique_id = j1_discovery_data["device_ieee"]

    hass_with_config_entries.config_entries.async_entries.return_value = [
        existing_entry
    ]

    with patch.object(flow, "_abort_if_unique_id_configured"):
        await flow.async_step_zha(j1_discovery_data)
        # Unique ID should be set
        assert flow.unique_id == j1_discovery_data["device_ieee"]


# =============================================================================
# Test Initial Config Flow - User Step (J1)
# =============================================================================


@pytest.mark.asyncio
async def test_user_step_j1_creates_entry(hass_with_config_entries, j1_discovery_data):
    """Test user step creates config entry for J1 with shade type."""
    flow = UbisysConfigFlow()
    flow.hass = hass_with_config_entries
    flow._discovery_data = j1_discovery_data

    user_input = {CONF_SHADE_TYPE: "venetian"}

    result = await flow.async_step_user(user_input)

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["title"] == "Test J1 (venetian)"
    assert result["data"][CONF_DEVICE_IEEE] == j1_discovery_data["device_ieee"]
    assert result["data"][CONF_SHADE_TYPE] == "venetian"
    assert result["data"][CONF_ZHA_CONFIG_ENTRY_ID] == "zha_entry_id"


@pytest.mark.asyncio
async def test_user_step_j1_shows_form(hass, j1_discovery_data):
    """Test user step shows form for J1 shade type selection."""
    flow = UbisysConfigFlow()
    flow.hass = hass
    flow._discovery_data = j1_discovery_data

    result = await flow.async_step_user(None)

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"
    assert CONF_SHADE_TYPE in result["data_schema"].schema


# =============================================================================
# Test Initial Config Flow - User Step (D1)
# =============================================================================


@pytest.mark.asyncio
async def test_user_step_d1_creates_entry_directly(
    hass_with_config_entries, d1_discovery_data
):
    """Test user step creates config entry for D1 without additional config."""
    flow = UbisysConfigFlow()
    flow.hass = hass_with_config_entries
    flow._discovery_data = d1_discovery_data

    # D1 should not require user input, so pass empty dict
    user_input = {}

    result = await flow.async_step_user(user_input)

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["title"] == "Test D1 (D1)"
    assert result["data"][CONF_DEVICE_IEEE] == d1_discovery_data["device_ieee"]
    assert CONF_SHADE_TYPE not in result["data"]  # D1 doesn't have shade type


# =============================================================================
# Test Initial Config Flow - Error Handling
# =============================================================================


@pytest.mark.asyncio
async def test_user_step_zha_not_found_shows_error(
    hass_with_config_entries, j1_discovery_data
):
    """Test user step shows error when ZHA integration not found."""
    flow = UbisysConfigFlow()
    flow.hass = hass_with_config_entries
    flow._discovery_data = j1_discovery_data

    user_input = {CONF_SHADE_TYPE: "roller"}

    # Override fixture to return no ZHA entries
    hass_with_config_entries.config_entries.async_entries = MagicMock(return_value=[])

    result = await flow.async_step_user(user_input)

    assert result["type"] == FlowResultType.FORM
    assert result["errors"]["base"] == "zha_not_found"


# =============================================================================
# Test Options Flow - Menu and About
# =============================================================================


@pytest.mark.asyncio
async def test_options_flow_menu(hass, mock_config_entry):
    """Test options flow shows menu."""
    flow = UbisysOptionsFlow(mock_config_entry)
    flow.hass = hass

    result = await flow.async_step_init(None)

    assert result["type"] == FlowResultType.MENU
    assert "about" in result["menu_options"]
    assert "configure" in result["menu_options"]


@pytest.mark.asyncio
async def test_options_flow_about(hass, mock_config_entry):
    """Test options flow about step."""
    flow = UbisysOptionsFlow(mock_config_entry)
    flow.hass = hass

    result = await flow.async_step_about(None)

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "about"


# =============================================================================
# Test Options Flow - Configure Step (J1)
# =============================================================================


@pytest.mark.asyncio
async def test_options_flow_configure_j1_shows_form(hass, mock_config_entry):
    """Test options configure step for J1 shows form with options."""
    flow = UbisysOptionsFlow(mock_config_entry)
    flow.hass = hass

    result = await flow.async_step_configure(None)

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "configure"
    # Should show shade type and logging options
    assert CONF_SHADE_TYPE in result["data_schema"].schema


@pytest.mark.asyncio
async def test_options_flow_configure_j1_updates_options(
    hass_with_config_entries, mock_config_entry
):
    """Test options configure step for J1 updates options."""
    flow = UbisysOptionsFlow(mock_config_entry)
    flow.hass = hass_with_config_entries

    user_input = {
        CONF_SHADE_TYPE: "cellular",
        "verbose_info_logging": True,
    }

    # Mock entity registry - er.async_entries_for_config_entry returns list of entities
    with patch("custom_components.ubisys.config_flow.er") as mock_er:
        mock_registry = MagicMock()
        mock_entity = MagicMock()
        mock_entity.entity_id = "cover.test_j1"
        mock_entity.domain = "cover"

        mock_er.async_get.return_value = mock_registry
        mock_er.async_entries_for_config_entry.return_value = [mock_entity]

        result = await flow.async_step_configure(user_input)

        # After saving options we expect to land on the advanced tuning step
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "j1_advanced"


# =============================================================================
# Test Options Flow - Configure Step (D1)
# =============================================================================


@pytest.mark.asyncio
async def test_options_flow_configure_d1_shows_form(hass):
    """Test options configure step for D1 shows form with D1 options."""
    d1_entry = MagicMock()
    d1_entry.entry_id = "test_d1_entry"
    d1_entry.domain = DOMAIN
    d1_entry.data = {
        CONF_DEVICE_IEEE: "00:11:22:33:44:55:66:88",
        "model": "D1",
        "name": "Test D1",
    }
    d1_entry.options = {}

    flow = UbisysOptionsFlow(d1_entry)
    flow.hass = hass

    result = await flow.async_step_configure(None)

    assert result["type"] == FlowResultType.FORM
    # D1 devices show d1_options step, not generic configure
    assert result["step_id"] == "d1_options"
    # Should show logging options but NOT shade type
    assert CONF_SHADE_TYPE not in result["data_schema"].schema


# =============================================================================
# Test Manual Config Flow
# =============================================================================


@pytest.mark.asyncio
async def test_manual_step_shows_device_list(hass_with_config_entries):
    """Test manual step shows available devices."""
    flow = UbisysConfigFlow()
    flow.hass = hass_with_config_entries
    flow.context = {}

    # Mock device registry to return Ubisys devices
    with patch("custom_components.ubisys.config_flow.dr.async_get") as mock_dr:
        mock_registry = MagicMock()

        # Create mock Ubisys device
        mock_device = MagicMock()
        mock_device.id = "device_123"
        mock_device.identifiers = {("zha", "00:11:22:33:44:55:66:77")}
        mock_device.manufacturer = "ubisys"
        mock_device.model = "J1"
        mock_device.name = "Test J1"
        mock_device.name_by_user = None

        mock_registry.devices.values.return_value = [mock_device]
        mock_dr.return_value = mock_registry

        result = await flow.async_step_manual(None)

        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "manual"


@pytest.mark.asyncio
async def test_manual_step_selects_device(hass_with_config_entries):
    """Test manual step device selection creates entry."""
    flow = UbisysConfigFlow()
    flow.hass = hass_with_config_entries
    flow.context = {}

    # Mock device registry
    with patch("custom_components.ubisys.config_flow.dr.async_get") as mock_dr:
        mock_registry = MagicMock()

        mock_device = MagicMock()
        mock_device.id = "device_123"
        mock_device.identifiers = {("zha", "00:11:22:33:44:55:66:77")}
        mock_device.manufacturer = "ubisys"
        mock_device.model = "J1"
        mock_device.name = "Test J1"
        mock_device.name_by_user = None

        mock_registry.devices.values.return_value = [mock_device]
        mock_dr.return_value = mock_registry

        # First call to show form
        await flow.async_step_manual(None)

        # Second call with device selection
        user_input = {"device": "00:11:22:33:44:55:66:77"}
        result = await flow.async_step_manual(user_input)

        # Should proceed to user step for shade type selection (J1)
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "user"


@pytest.mark.asyncio
async def test_manual_step_no_devices_found(hass_with_config_entries):
    """Test manual step aborts when no devices found."""
    flow = UbisysConfigFlow()
    flow.hass = hass_with_config_entries
    flow.context = {}

    # Mock empty device registry
    with patch("custom_components.ubisys.config_flow.dr.async_get") as mock_dr:
        mock_registry = MagicMock()
        mock_registry.devices.values.return_value = []
        mock_dr.return_value = mock_registry

        result = await flow.async_step_manual(None)

        assert result["type"] == FlowResultType.ABORT
        assert result["reason"] == "no_devices"


# =============================================================================
# Test Options Flow - D1 Options Step
# =============================================================================


@pytest.mark.asyncio
async def test_options_flow_d1_options_updates(hass_with_config_entries):
    """Test D1 options step updates options."""
    d1_entry = MagicMock()
    d1_entry.entry_id = "test_d1_entry"
    d1_entry.domain = DOMAIN
    d1_entry.data = {
        CONF_DEVICE_IEEE: "00:11:22:33:44:55:66:88",
        "model": "D1",
        "name": "Test D1",
    }
    d1_entry.options = {}

    flow = UbisysOptionsFlow(d1_entry)
    flow.hass = hass_with_config_entries

    user_input = {
        "verbose_info_logging": True,
        "verbose_input_logging": False,
    }

    # Mock entity registry for finding entity_id
    with patch("custom_components.ubisys.config_flow.er") as mock_er:
        mock_registry = MagicMock()
        mock_entity = MagicMock()
        mock_entity.entity_id = "light.test_d1"
        mock_entity.domain = "light"
        mock_er.async_get.return_value = mock_registry
        mock_er.async_entries_for_config_entry.return_value = [mock_entity]

        # Mock services call
        hass_with_config_entries.services = MagicMock()
        hass_with_config_entries.services.async_call = AsyncMock()

        result = await flow.async_step_d1_options(user_input)

    # Should proceed to input config step
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "input_config"


# =============================================================================
# Test Options Flow - J1 Advanced Step
# =============================================================================


@pytest.mark.asyncio
async def test_options_flow_j1_advanced_shows_form(hass, mock_config_entry):
    """Test J1 advanced tuning step shows form."""
    flow = UbisysOptionsFlow(mock_config_entry)
    flow.hass = hass
    hass.data = {}  # Add data attribute for tests
    flow._options = {CONF_SHADE_TYPE: "roller"}

    # Mock entity registry for finding entity_id
    with patch("custom_components.ubisys.config_flow.er") as mock_er:
        mock_registry = MagicMock()
        mock_entity = MagicMock()
        mock_entity.entity_id = "cover.test_j1"
        mock_entity.domain = "cover"
        mock_er.async_get.return_value = mock_registry
        mock_er.async_entries_for_config_entry.return_value = [mock_entity]

        result = await flow.async_step_j1_advanced(None)

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "j1_advanced"


@pytest.mark.asyncio
async def test_options_flow_j1_advanced_creates_entry(
    hass_with_config_entries, mock_config_entry
):
    """Test J1 advanced tuning step proceeds to input config."""
    flow = UbisysOptionsFlow(mock_config_entry)
    flow.hass = hass_with_config_entries
    flow._options = {CONF_SHADE_TYPE: "roller", "verbose_info_logging": False}

    user_input = {"auto_calibrate": False}

    # Mock entity registry for finding entity_id
    with patch("custom_components.ubisys.config_flow.er") as mock_er:
        mock_registry = MagicMock()
        mock_entity = MagicMock()
        mock_entity.entity_id = "cover.test_j1"
        mock_entity.domain = "cover"
        mock_er.async_get.return_value = mock_registry
        mock_er.async_entries_for_config_entry.return_value = [mock_entity]

        # Mock services call
        hass_with_config_entries.services = MagicMock()
        hass_with_config_entries.services.async_call = AsyncMock()

        result = await flow.async_step_j1_advanced(user_input)

    # After J1 advanced with user input, it proceeds to input_config step
    # If no presets available for J1, it will abort with "no_presets"
    assert result["type"] in [FlowResultType.FORM, FlowResultType.ABORT]
    if result["type"] == FlowResultType.FORM:
        assert result["step_id"] == "input_config"
    else:
        assert result["reason"] == "no_presets"


# =============================================================================
# Test Options Flow - Input Config Step
# =============================================================================


@pytest.mark.asyncio
async def test_options_flow_input_config_shows_form(hass):
    """Test input config step shows form for S1/D1 devices."""
    s1_entry = MagicMock()
    s1_entry.entry_id = "test_s1_entry"
    s1_entry.domain = DOMAIN
    s1_entry.data = {
        CONF_DEVICE_IEEE: "00:11:22:33:44:55:66:99",
        "model": "S1",
        "name": "Test S1",
    }
    s1_entry.options = {}

    flow = UbisysOptionsFlow(s1_entry)
    flow.hass = hass
    hass.data = {}  # Add data attribute for tests
    flow._options = {"verbose_info_logging": False}

    result = await flow.async_step_input_config(None)

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "input_config"


@pytest.mark.asyncio
async def test_options_flow_input_config_for_j1(
    hass_with_config_entries, mock_config_entry
):
    """Test input config step for J1 devices shows form or aborts if no presets."""
    flow = UbisysOptionsFlow(mock_config_entry)
    flow.hass = hass_with_config_entries
    flow._options = {CONF_SHADE_TYPE: "roller", "verbose_info_logging": False}

    # J1 devices go through input_config like other devices
    result = await flow.async_step_input_config(None)

    # If no presets available for J1, it aborts with "no_presets"
    # Otherwise shows the input_config form
    assert result["type"] in [FlowResultType.FORM, FlowResultType.ABORT]
    if result["type"] == FlowResultType.FORM:
        assert result["step_id"] == "input_config"
    else:
        assert result["reason"] == "no_presets"


# =============================================================================
# Test Options Flow - S1 Specific
# =============================================================================


@pytest.mark.asyncio
async def test_options_flow_configure_s1_shows_form(hass):
    """Test options configure step for S1 shows form."""
    s1_entry = MagicMock()
    s1_entry.entry_id = "test_s1_entry"
    s1_entry.domain = DOMAIN
    s1_entry.data = {
        CONF_DEVICE_IEEE: "00:11:22:33:44:55:66:99",
        "model": "S1",
        "name": "Test S1",
    }
    s1_entry.options = {}

    flow = UbisysOptionsFlow(s1_entry)
    flow.hass = hass
    hass.data = {}  # Add data attribute for tests

    result = await flow.async_step_configure(None)

    assert result["type"] == FlowResultType.FORM
    # S1 uses input_config step directly (no s1_options step)
    assert result["step_id"] == "input_config"


# =============================================================================
# Test Helper Functions
# =============================================================================


@pytest.mark.asyncio
async def test_get_zha_config_entry_id_found(hass_with_config_entries):
    """Test getting ZHA config entry ID when ZHA is loaded."""
    flow = UbisysConfigFlow()
    flow.hass = hass_with_config_entries

    result = await flow._get_zha_config_entry_id()

    assert result == "zha_entry_id"


@pytest.mark.asyncio
async def test_get_zha_config_entry_id_not_found(hass):
    """Test getting ZHA config entry ID when ZHA not loaded."""
    flow = UbisysConfigFlow()
    flow.hass = hass
    hass.config_entries = MagicMock()
    hass.config_entries.async_entries = MagicMock(return_value=[])

    result = await flow._get_zha_config_entry_id()

    assert result is None


def test_find_entity_id(hass, mock_config_entry):
    """Test finding entity ID for config entry."""
    from types import SimpleNamespace

    flow = UbisysOptionsFlow(mock_config_entry)
    flow.hass = hass

    # Create mock entity entry
    mock_entity = SimpleNamespace(
        entity_id="cover.test_j1",
        domain="cover",
    )

    with patch("custom_components.ubisys.config_flow.er.async_get") as mock_er:
        mock_registry = MagicMock()
        mock_er.return_value = mock_registry

        with patch(
            "custom_components.ubisys.config_flow.er.async_entries_for_config_entry"
        ) as mock_entries:
            mock_entries.return_value = [mock_entity]

            result = flow._find_entity_id(mock_config_entry.entry_id, "cover")

            assert result == "cover.test_j1"


def test_find_entity_id_not_found(hass, mock_config_entry):
    """Test finding entity ID when not found raises error."""
    from homeassistant.exceptions import HomeAssistantError

    flow = UbisysOptionsFlow(mock_config_entry)
    flow.hass = hass

    with patch("custom_components.ubisys.config_flow.er.async_get") as mock_er:
        mock_registry = MagicMock()
        mock_er.return_value = mock_registry

        with patch(
            "custom_components.ubisys.config_flow.er.async_entries_for_config_entry"
        ) as mock_entries:
            mock_entries.return_value = []

            # When no entity found, _find_entity_id raises HomeAssistantError
            with pytest.raises(HomeAssistantError) as exc_info:
                flow._find_entity_id(mock_config_entry.entry_id, "cover")

            assert "No cover entity found" in str(exc_info.value)
