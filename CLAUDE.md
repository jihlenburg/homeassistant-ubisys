# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Home Assistant custom integration for Ubisys Zigbee window covering controllers (J1 model). The integration has three main components:

1. **Custom Integration** (`custom_components/ubisys/`)
   - Cover platform (`cover.py`) - Wrapper entity with feature filtering
   - Button platform (`button.py`) - Calibration button for easy UI access
   - Calibration module (`calibration.py`) - 5-phase automated calibration with stall detection
   - Config flow (`config_flow.py`) - UI-based setup with auto-discovery
   - Constants (`const.py`) - Shade type mappings and feature definitions

2. **ZHA Quirk** (`custom_zha_quirks/ubisys_j1.py`) - Extends ZHA with Ubisys manufacturer-specific attributes

**Key Features:**
- Auto-discovery of J1 devices paired with ZHA (v1.1+)
- Smart feature filtering based on configured shade type
- One-click calibration via button entity or service
- Motor stall detection for reliable limit finding
- Per-device locking prevents concurrent calibrations
- Comprehensive logging with phase-based structure

## Architecture

### Three-Layer Design

```
User → Ubisys Cover Entity → ZHA Cover Entity → Zigbee Device
```

**Critical architectural pattern**: The Ubisys cover entity (`cover.py`) is a **wrapper**, not a replacement. It:
- Listens for state changes from the underlying ZHA entity via event listener
- Filters `supported_features` based on configured shade type
- Delegates all commands to the underlying ZHA entity (never talks to Zigbee directly)
- Must maintain state synchronization through `_async_update_from_zha()`

### Shade Type Feature Filtering

The core value proposition is filtering Home Assistant's cover features based on physical shade capabilities:

- **Position-only shades** (roller/cellular/vertical): OPEN, CLOSE, STOP, SET_POSITION
- **Position+tilt shades** (venetian): All position features + OPEN_TILT, CLOSE_TILT, STOP_TILT, SET_TILT_POSITION

Mapping defined in `const.py` as `SHADE_TYPE_TO_FEATURES` and `SHADE_TYPE_TO_WINDOW_COVERING_TYPE`.

### ZHA Quirk Auto-Injection Pattern

`custom_zha_quirks/ubisys_j1.py` overrides `read_attributes()` and `write_attributes()` to **automatically inject** the Ubisys manufacturer code (0x10F2) when accessing manufacturer-specific attributes:

- `0x1000` - configured_mode
- `0x1001` - lift_to_tilt_transition_steps
- `0x1002` - total_steps

This allows the rest of the integration to access these attributes without specifying the manufacturer code each time.

### Calibration Architecture (v1.1+)

The calibration module (`calibration.py`) implements a **5-phase automated calibration** using **motor stall detection**:

**Phase 1: Preparation**
- Enter calibration mode (mode=0x02)
- Write configured_mode based on shade type

**Phase 2: Find Top Limit**
- Send up_open command (continuous movement)
- Monitor position every 0.5s until stall detected (position unchanged for 3s)
- Send stop command

**Phase 3: Find Bottom Limit + Measure**
- Send down_close command
- Monitor position until stall
- Send stop command
- Read total_steps (device calculated during movement)

**Phase 4: Verification**
- Send up_open command
- Monitor until stall (should reach same top position)
- Send stop command

**Phase 5: Finalization**
- Write lift_to_tilt_transition_steps (0 for rollers, 100 for venetian)
- Exit calibration mode (mode=0x00)

**Key Design Decisions:**

1. **Motor Stall Detection**: J1 doesn't signal when limit reached, so we monitor position attribute. Position unchanged for 3 seconds = motor stalled at limit.

2. **Phase-Based Architecture**: Each phase is a separate function for:
   - Independent testing
   - Clear error messages (know which phase failed)
   - Easier maintenance and modification

3. **Direct Cluster Commands**: Uses cluster.command() for up_open/down_close (not HA services) because we need low-level control and timeout handling.

4. **Concurrency Control**: asyncio.Lock per device prevents race conditions from simultaneous calibrations.

## Code Quality Standards

### Function Complexity Limits

- **Maximum function size**: 100 lines (target: <60 lines)
- **Maximum complexity**: Keep functions focused on single responsibility
- **Nesting limit**: Maximum 2-3 levels of indentation

**Rationale**: The v1.1.1 refactoring reduced _perform_calibration from 274 lines to 81 lines by extracting phases. This improved:
- Testability (each phase can be tested independently)
- Debuggability (know which phase failed)
- Maintainability (change one phase without affecting others)

### Documentation Requirements

**All functions must have docstrings that include:**
1. One-line summary
2. Detailed explanation of WHY (not just WHAT)
3. Args with types, valid values, and constraints
4. Returns with typical values and units
5. Raises with conditions and user actions
6. Examples for complex functions
7. Design decisions and tradeoffs

**Example of good docstring:**
```python
async def _wait_for_stall(
    hass: HomeAssistant,
    entity_id: str,
    phase_description: str,
    timeout: int = PER_MOVE_TIMEOUT,
) -> int:
    \"\"\"Wait for motor stall via position monitoring.

    The J1 motor doesn't signal when it reaches a limit. We detect
    stall by monitoring the position attribute - if unchanged for
    STALL_DETECTION_TIME seconds, the motor has stalled.

    Why 3 seconds?
    - <2s: False positives (motor may pause briefly)
    - >5s: Poor UX (user perceives lag)
    - 3s: Balanced (proven by deCONZ implementation)

    Args:
        hass: Home Assistant instance for state access
        entity_id: ZHA cover entity to monitor
        phase_description: Description for logging (e.g., "finding top")
        timeout: Max seconds to wait before raising timeout error

    Returns:
        Final position when motor stalled (e.g., 100 for fully open)

    Raises:
        HomeAssistantError: If motor doesn't stall within timeout.
            Usually indicates jammed motor or disconnected device.
    \"\"\"
```

### Security Patterns

**Service Parameter Validation** (Added in v1.1.1):
```python
# ALWAYS validate service parameters
entity_id = call.data.get("entity_id")

# Check type
if not isinstance(entity_id, str):
    raise HomeAssistantError(f"entity_id must be string, got {type(entity_id).__name__}")

# Verify entity exists
entity_entry = entity_registry.async_get(entity_id)
if not entity_entry:
    raise HomeAssistantError(f"Entity {entity_id} not found")

# Verify platform ownership
if entity_entry.platform != DOMAIN:
    raise HomeAssistantError(
        f"Entity {entity_id} is not a Ubisys entity (platform: {entity_entry.platform})"
    )
```

**Concurrency Control** (Added in v1.1.1):
```python
# Use asyncio.Lock, NOT set-based tracking
# Set-based has TOCTOU race condition

# Get or create lock for device
if "calibration_locks" not in hass.data.setdefault(DOMAIN, {}):
    hass.data[DOMAIN]["calibration_locks"] = {}

locks = hass.data[DOMAIN]["calibration_locks"]
if device_ieee not in locks:
    locks[device_ieee] = asyncio.Lock()

device_lock = locks[device_ieee]

# Non-blocking check
if device_lock.locked():
    raise HomeAssistantError("Calibration already in progress")

# Atomic acquire
async with device_lock:
    await perform_operation()
    # Lock automatically released
```

### Testing Strategy

**Unit Tests**: Test individual functions with mocked dependencies
- Mock cluster for calibration phase functions
- Mock hass.states for stall detection
- Test error conditions

**Integration Tests**: Test with real ZHA integration
- Requires ZHA test setup
- Use test fixtures for device pairing

**Manual Testing**: Test with real hardware
- Required for calibration validation
- Document test scenarios in `docs/testing.md`

## Development Commands

### Testing in Home Assistant

```bash
# Create symlinks for development (run from repo root)
ln -s $(pwd)/custom_components/ubisys ~/.homeassistant/custom_components/ubisys
ln -s $(pwd)/custom_zha_quirks/ubisys_j1.py ~/.homeassistant/custom_zha_quirks/ubisys_j1.py
ln -s $(pwd)/python_scripts/ubisys_j1_calibrate.py ~/.homeassistant/python_scripts/ubisys_j1_calibrate.py

# After code changes, reload the integration
# Via Home Assistant UI: Configuration → Integrations → Ubisys → ⋮ → Reload

# Or restart Home Assistant
ha core restart
```

### Required Home Assistant Configuration

```yaml
# configuration.yaml
zha:
  custom_quirks_path: custom_zha_quirks

python_script:

logger:
  logs:
    custom_components.ubisys: debug  # For development
```

### Checking Integration Status

```bash
# View integration logs
grep -i ubisys ~/.homeassistant/home-assistant.log | tail -50

# Check if quirk loaded (should show custom cluster)
# Navigate to: Configuration → Integrations → ZHA → Devices → J1 device → Signature

# Test calibration script exists
# Navigate to: Developer Tools → Services → Filter for "python_script.ubisys_j1_calibrate"

# Verify entity created
# Navigate to: Developer Tools → States → Filter for "ubisys"
```

## Code Modification Guidelines

### Changing Shade Types or Features

1. Update `const.py`:
   - Add to `SHADE_TYPES` list
   - Add to `ShadeType` enum
   - Add mapping in `SHADE_TYPE_TO_WINDOW_COVERING_TYPE`
   - Add mapping in `SHADE_TYPE_TO_FEATURES`

2. Update `config_flow.py`:
   - Add option to both `async_step_user` and `UbisysOptionsFlow.async_step_init`

3. Update `strings.json` and `translations/en.json` with new shade type label

4. Update calibration script if new WindowCoveringType requires different sequence

### Adding New Manufacturer Attributes

1. In `custom_zha_quirks/ubisys_j1.py`:
   - Define attribute constant (e.g., `UBISYS_ATTR_NEW = 0x1003`)
   - Add to `manufacturer_attributes` dict with `ZCLAttributeDef`
   - The auto-injection in `read_attributes`/`write_attributes` will handle it

2. Use anywhere in integration via ZHA cluster access (manufacturer code injected automatically)

### Modifying Calibration Sequence

Calibration is implemented in `custom_components/ubisys/calibration.py` as a service with phase-based architecture.

**To add a new calibration phase:**

1. Create phase function following the naming pattern:
```python
async def _calibration_phase_N_description(
    hass: HomeAssistant,
    cluster: Cluster,
    entity_id: str,
) -> Optional[ReturnType]:
    """PHASE N: [Description].

    [Detailed explanation of what this phase does and why]

    Args:
        hass: Home Assistant instance
        cluster: WindowCovering cluster
        entity_id: ZHA cover entity for monitoring

    Returns:
        [What this phase returns, if anything]

    Raises:
        HomeAssistantError: [Conditions that cause failure]
    """
    _LOGGER.info("═══ PHASE N: [Description] ═══")

    # Step implementation
    _LOGGER.debug("Step X: [What we're doing]")
    # ... code ...

    _LOGGER.info("✓ PHASE N Complete: [Result]")
    return result
```

2. Add phase call to `_perform_calibration()` orchestrator:
```python
async def _perform_calibration(...) -> None:
    # ... existing phases ...
    result = await _calibration_phase_N_description(hass, cluster, entity_id)
    # ... remaining phases ...
```

3. Update module docstring to include new phase
4. Add tests for new phase function
5. Update `docs/calibration.md` if user-visible

**To modify stall detection:**
- Edit `_wait_for_stall()` function
- Constants are at module level: `STALL_DETECTION_TIME`, `STALL_DETECTION_INTERVAL`
- Be careful: changes affect all phases that use stall detection

### State Synchronization Pattern

The wrapper entity must stay synchronized with ZHA entity. Critical implementation:

```python
# In UbisysCover.__init__():
self._zha_entity_id = zha_entity_id

# In UbisysCover.async_added_to_hass():
self._unsubscribe_state_listener = async_track_state_change_event(
    self.hass, [self._zha_entity_id], self._async_state_changed_listener
)

# Callback triggers update:
@callback
def _async_state_changed_listener(self, event) -> None:
    self.hass.async_create_task(self._async_update_from_zha())

# Update pulls all state from ZHA entity:
async def _async_update_from_zha(self) -> None:
    zha_state = self.hass.states.get(self._zha_entity_id)
    # Copy all attributes...
    self.async_write_ha_state()
```

**Do not** poll or directly access the Zigbee device from the wrapper entity.

## Version Updates

To release a new version:

1. Update version in `custom_components/ubisys/manifest.json`
2. Update badges in `README.md` if needed
3. Commit with message: `chore: bump version to X.Y.Z`
4. Tag: `git tag -a vX.Y.Z -m "Release version X.Y.Z"`
5. Push tag: `git push origin vX.Y.Z`
6. HACS will auto-detect the new release

## Home Assistant Integration Requirements

This integration follows Home Assistant's integration quality checklist:

- Config flow (UI-based setup) - no YAML configuration required
- Type hints on all functions
- Uses `from __future__ import annotations`
- Logger per module: `_LOGGER = logging.getLogger(__name__)`
- No polling (`_attr_should_poll = False`)
- Proper unload/reload support in `__init__.py`
- Unique IDs for entities based on underlying device
- Device linkage via `device_info`
- Service definitions in `services.yaml`
- Translations in `strings.json` and `translations/en.json`

## Testing Without Hardware

To test without a physical J1 device:

1. Create a mock ZHA cover entity (requires ZHA integration with any Zigbee cover device)
2. Configure the Ubisys integration pointing to the mock entity
3. Test feature filtering (should only show features for selected shade type)
4. Calibration will fail without real device, but you can test service registration

Note: Full calibration testing requires actual Ubisys J1 hardware.

## Zigbee Technical Details

- **Manufacturer Code**: 0x10F2
- **Cluster**: 0x0102 (Window Covering)
- **Endpoint**: 2 (J1 uses endpoint 2 for window covering control)
- **Device Type**: 0x0202 (Window covering device)
- **Profile**: 0x0104 (Zigbee Home Automation)

The quirk matches device signature `("ubisys", "J1")` and replaces endpoint 2's WindowCovering cluster with the extended `UbisysWindowCovering` cluster.
