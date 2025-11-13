from types import SimpleNamespace

import pytest


@pytest.fixture
def hass():
    """Minimal Home Assistant fixture for tests that don't need full HA."""
    return SimpleNamespace()
