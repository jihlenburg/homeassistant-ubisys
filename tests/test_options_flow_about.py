import pytest
from homeassistant import config_entries

from custom_components.ubisys.config_flow import UbisysOptionsFlow


class DummyEntry:
    def __init__(self, data=None, options=None, entry_id="eid"):
        self.data = data or {
            "name": "Device",
            "model": "J1",
        }
        self.options = options or {}
        self.entry_id = entry_id


@pytest.mark.asyncio
async def test_options_menu_and_about(hass):
    entry = DummyEntry()
    flow = UbisysOptionsFlow(entry)  # type: ignore[arg-type]
    flow.hass = hass

    # Menu
    result = await flow.async_step_init(None)
    assert result["type"] == config_entries.FlowResultType.MENU
    assert "about" in result["menu_options"]
    assert "configure" in result["menu_options"]

    # About page
    result = await flow.async_step_about(None)
    assert result["type"] == config_entries.FlowResultType.FORM
    assert result["step_id"] == "about"

