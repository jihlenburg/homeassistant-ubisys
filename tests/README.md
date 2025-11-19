# Ubisys Integration Test Guide

This directory contains tests for the Ubisys Home Assistant integration.

## Quick Start

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=custom_components/ubisys --cov-report=term-missing

# Run specific test file
pytest tests/test_input_parser.py -v

# Run specific test function
pytest tests/test_input_parser.py::test_input_actions_parse_single_entry -v

# Run full CI (lint + type + tests)
# Creates .venv, installs dependencies from pyproject.toml [dependency-groups]
make ci
```

## Test Infrastructure

### Current Status

- ✅ **All tests passing** (6 tests)
- ✅ **Coverage: 23%** (baseline established)
- ✅ **CI working** (lint, type check, tests with coverage)
- ✅ **Comprehensive fixtures** available in `conftest.py`

### Available Fixtures

The `conftest.py` provides extensive fixtures organized by category:

#### 1. Simple Fixtures (Fast)

```python
def test_simple_function(hass):
    """Use for tests that don't need full HA."""
    hass.data = {"test": "value"}  # SimpleNamespace
    assert hass.data["test"] == "value"
```

#### 2. Home Assistant Fixtures (Slower)

```python
async def test_config_flow(hass_full):
    """Use for integration tests needing real HA."""
    result = await hass_full.config_entries.flow.async_init(...)
    assert result["type"] == "form"
```

#### 3. Mock Cluster Fixtures

Available clusters:
- `mock_window_covering_cluster` - For J1 calibration tests
- `mock_level_control_cluster` - For D1 dimmer tests
- `mock_on_off_cluster` - For S1 switch tests
- `mock_device_setup_cluster` - For input configuration tests

```python
async def test_calibration_phase_1(mock_window_covering_cluster):
    """Test entering calibration mode."""
    cluster = mock_window_covering_cluster

    # Simulate writing calibration mode
    await cluster.write_attributes({0x0017: 0x02})

    # Verify call was made
    cluster.write_attributes.assert_called_once_with({0x0017: 0x02})
```

#### 4. Mock Config Entry Fixtures

Available entries:
- `mock_j1_config_entry` - J1 with roller shade
- `mock_d1_config_entry` - D1 dimmer
- `mock_s1_config_entry` - S1 switch

```python
def test_entity_setup(mock_j1_config_entry):
    """Test entity created from config entry."""
    assert mock_j1_config_entry.data["model"] == "J1"
    assert mock_j1_config_entry.options["shade_type"] == "roller"
```

#### 5. Helper Fixtures

Patch common functions to avoid Zigbee calls:
- `mock_async_zcl_command` - Mock ZCL command execution
- `mock_async_write_and_verify_attrs` - Mock attribute write/verify
- `mock_hass_states` - Mock state monitoring

```python
async def test_with_mocked_zcl(mock_async_zcl_command):
    """ZCL commands are automatically mocked."""
    await some_function_that_calls_zcl()
    mock_async_zcl_command.assert_called()
```

#### 6. Parametrize Helpers

Use predefined lists for parametrized tests:

```python
from tests.conftest import SHADE_TYPES

@pytest.mark.parametrize("shade_type", SHADE_TYPES)
def test_all_shade_types(shade_type):
    """Test runs for roller, venetian, vertical, cellular."""
    features = get_features_for_shade_type(shade_type)
    assert features is not None
```

Available lists:
- `SHADE_TYPES` = ["roller", "venetian", "vertical", "cellular"]
- `DEVICE_MODELS` = ["J1", "J1-R", "D1", "D1-R", "S1", "S1-R"]
- `PRESS_TYPES` = ["pressed", "released", "short_press", "long_press", "double_press"]

## Writing New Tests

### Example: Testing Calibration Phase

```python
# tests/test_j1_calibration.py
import pytest
from unittest.mock import patch
from custom_components.ubisys.j1_calibration import _calibration_phase_1_preparation

async def test_phase_1_enter_calibration_mode(hass, mock_window_covering_cluster):
    """Test Phase 1: Enter calibration mode."""
    # Setup
    cluster = mock_window_covering_cluster
    window_covering_type = 0  # Roller shade

    # Execute
    await _calibration_phase_1_preparation(
        hass,
        cluster,
        window_covering_type
    )

    # Verify calibration mode was set
    cluster.write_attributes.assert_called()
    call_args = cluster.write_attributes.call_args
    assert 0x0017 in call_args[0][0]  # Calibration mode attribute
    assert call_args[0][0][0x0017] == 0x02  # Enter calibration
```

### Example: Testing Config Flow

```python
# tests/test_config_flow.py
import pytest
from homeassistant import config_entries
from custom_components.ubisys.const import DOMAIN

async def test_config_flow_j1_discovery(hass_full):
    """Test J1 device auto-discovery."""
    result = await hass_full.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER}
    )

    assert result["type"] == "form"
    assert result["step_id"] == "user"
```

### Example: Testing Input Parsing

```python
# tests/test_input_parser.py (existing)
from custom_components.ubisys.input_parser import InputActionsParser

def test_parse_valid_input_actions():
    """Test parsing valid InputActions micro-code."""
    # Valid micro-code from device
    data = b"\x48\x41\x01\x00\x01\x02\x00\x01\x06\x00\x02\x00"

    parser = InputActionsParser()
    actions = parser.parse(data)

    assert len(actions) == 1
    assert actions[0].input_number == 0
    assert actions[0].transition_state == "pressed"
```

## Test Organization

```
tests/
├── conftest.py                    # Shared fixtures (enhanced!)
├── README.md                      # This file
├── test_input_parser.py          # ✅ Input parsing (existing)
├── test_helpers_write_verify.py  # ✅ Helper functions (existing)
├── test_options_flow_about.py    # ✅ Options flow (existing)
│
└── (Future tests to add)
    ├── test_j1_calibration.py    # J1 calibration phases
    ├── test_config_flow.py       # Config flow steps
    ├── test_cover_platform.py    # Cover entity lifecycle
    ├── test_light_platform.py    # Light entity lifecycle
    ├── test_switch_platform.py   # Switch entity lifecycle
    ├── test_button_platform.py   # Button entities
    ├── test_device_trigger.py    # Device triggers
    └── test_input_monitor.py     # Input event monitoring
```

## Coverage Goals

**Current Coverage: 23%**

### Well-Tested Modules (✅):
- `const.py`: 94%
- `input_parser.py`: 74%
- `ha_typing.py`: 75%

### Priority for Testing:
1. **j1_calibration.py** - 7% → 80% (most critical, complex)
2. **config_flow.py** - 17% → 70% (user's first experience)
3. **Platform files** - 0% → 70% (cover, light, switch, button, sensor)
4. **input_monitor.py** - 16% → 70% (event correlation)
5. **device_trigger.py** - 0% → 70% (automation triggers)

### Target: 80%+ overall coverage

## Best Practices

### 1. Use Appropriate Fixtures

```python
# Fast unit test - use simple hass
def test_pure_function(hass):
    result = calculate_something(hass, input)
    assert result == expected

# Integration test - use hass_full
async def test_config_flow(hass_full):
    result = await hass_full.config_entries.flow.async_init(...)
```

### 2. Mock External Dependencies

```python
# Mock ZCL commands
async def test_calibration(mock_async_zcl_command, mock_window_covering_cluster):
    await calibrate(cluster)
    mock_async_zcl_command.assert_called()
```

### 3. Test Both Success and Failure

```python
async def test_write_verify_success(mock_cluster):
    """Test successful write and verify."""
    await async_write_and_verify_attrs(mock_cluster, {0x1234: 7})
    # No exception = success

async def test_write_verify_mismatch_raises(mock_cluster):
    """Test mismatch raises error."""
    mock_cluster.read_attributes.return_value = [{0x1234: 999}]  # Wrong value

    with pytest.raises(HomeAssistantError, match="mismatch"):
        await async_write_and_verify_attrs(mock_cluster, {0x1234: 7})
```

### 4. Use Parametrize for Multiple Cases

```python
from tests.conftest import SHADE_TYPES

@pytest.mark.parametrize("shade_type", SHADE_TYPES)
def test_feature_filtering(shade_type):
    """Test feature filtering for all shade types."""
    features = get_features_for_shade_type(shade_type)

    if shade_type in ["roller", "cellular", "vertical"]:
        assert not (features & TILT_FEATURES)
    elif shade_type == "venetian":
        assert features & TILT_FEATURES
```

### 5. Document Test Purpose

```python
async def test_stall_detection_timeout():
    """Test that stall detection times out if motor never stops.

    The J1 motor should signal a stall by position not changing for 3 seconds.
    If position keeps changing, the function should timeout after 60 seconds.
    """
    # Test implementation...
```

## Running Tests

### Locally

```bash
# Quick test run
pytest

# With verbose output
pytest -v

# With coverage
pytest --cov=custom_components/ubisys --cov-report=term-missing

# Specific test
pytest tests/test_input_parser.py::test_parse_valid_input -v

# Stop on first failure
pytest -x

# Drop into debugger on failure
pytest --pdb

# Show print statements
pytest -s
```

### CI

```bash
# Run full CI suite
make ci

# Just tests
make test

# Just lint
make lint

# Just type check
make typecheck
```

## Next Steps for Test Coverage

### Phase 1: Calibration Tests (Priority 1)

Create `tests/test_j1_calibration.py` with tests for:
- [ ] Phase 1: Enter calibration mode
- [ ] Phase 2: Find top limit with stall detection
- [ ] Phase 3: Find bottom limit + measure
- [ ] Phase 4: Verification
- [ ] Phase 5: Finalization
- [ ] Stall detection logic
- [ ] Timeout handling
- [ ] Concurrent calibration prevention
- [ ] Error recovery

**Expected coverage increase**: +15% (j1_calibration.py: 7% → 80%)

### Phase 2: Platform Tests (Priority 2)

Create tests for each platform:
- [ ] `test_cover_platform.py` - Entity lifecycle, feature filtering, state sync
- [ ] `test_light_platform.py` - Entity lifecycle, state sync
- [ ] `test_switch_platform.py` - Entity lifecycle, state sync
- [ ] `test_button_platform.py` - Button press handling
- [ ] `test_sensor_platform.py` - Input event sensor

**Expected coverage increase**: +20%

### Phase 3: Config Flow Tests (Priority 3)

Create `tests/test_config_flow.py` with tests for:
- [ ] User flow initialization
- [ ] Discovery flow
- [ ] Options flow for each device type
- [ ] Shade type changes
- [ ] Input configuration
- [ ] Validation errors

**Expected coverage increase**: +10% (config_flow.py: 17% → 70%)

### Phase 4: Input System Tests (Priority 4)

Create tests for:
- [ ] `test_input_monitor.py` - Event correlation, button press detection
- [ ] `test_device_trigger.py` - Trigger registration and firing

**Expected coverage increase**: +10%

**Target after all phases**: 75-85% coverage

## Troubleshooting

### Tests fail with import errors
```bash
# Make sure PYTHONPATH is set (pytest.ini handles this)
pytest  # Should work

# If not, explicitly set it
PYTHONPATH=. pytest
```

### Tests fail with "fixture not found"
```bash
# Check fixture is defined in conftest.py
grep "def your_fixture" tests/conftest.py

# Check fixture spelling in test
# Note: hass vs hass_full (different fixtures!)
```

### Async tests fail
```bash
# Make sure test is marked async and uses asyncio
@pytest.mark.asyncio  # Can be omitted if asyncio_mode=auto
async def test_something():
    await async_function()
```

### Coverage doesn't increase
```bash
# Make sure you're testing the right module
pytest --cov=custom_components/ubisys.j1_calibration

# Make sure tests actually execute the code
pytest -v  # See which tests run
```

## Resources

- pytest documentation: https://docs.pytest.org/
- pytest-asyncio: https://pytest-asyncio.readthedocs.io/
- Home Assistant testing: https://developers.home-assistant.io/docs/development_testing/
- Coverage.py: https://coverage.readthedocs.io/
