# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Home Assistant custom integration for Ubisys Zigbee devices supporting J1 (window covering), D1 (universal dimmer), and S1 (power switch) devices. The integration follows a multi-device architecture with shared components.

1. **Custom Integration** (`custom_components/ubisys/`)
   - **Platforms**:
     - Cover platform (`cover.py`) - Wrapper entity with feature filtering for J1
     - Light platform (`light.py`) - Wrapper entity for D1
     - Button platform (`button.py`) - Calibration button for J1
   - **Device-Specific Modules**:
     - J1 calibration (`j1_calibration.py`) - 5-phase automated calibration with stall detection
     - D1 configuration (`d1_config.py`) - Phase mode, ballast, and input configuration
   - **Shared Modules**:
     - Helpers (`helpers.py`) - Shared utility functions (device info extraction, cluster access)
     - Input configuration (`input_config.py`) - Shared D1/S1 input configuration micro-code generation
     - Input monitoring (`input_monitor.py`) - Physical input event monitoring for all devices
     - Device triggers (`device_trigger.py`) - Button press automation triggers
   - **Core**:
     - Config flow (`config_flow.py`) - UI-based setup with auto-discovery
     - Constants (`const.py`) - Device categorization, endpoint maps, and constants

2. **ZHA Quirks** (`custom_zha_quirks/`)
   - `ubisys_j1.py` - J1 WindowCovering cluster with manufacturer attributes
   - `ubisys_d1.py` - D1 Ballast, DimmerSetup, and DeviceSetup clusters
   - `ubisys_s1.py` - S1/S1-R DeviceSetup cluster
   - `ubisys_common.py` - Shared DeviceSetup cluster and constants (DRY principle)

**Key Features:**
- Auto-discovery of all Ubisys devices paired with ZHA
- J1: Smart feature filtering based on configured shade type
- J1: One-click calibration via button entity or service
- D1: Phase control mode, ballast configuration via services
- S1/S1-R: UI-based input configuration with automatic rollback
- Physical input monitoring and device triggers for automations
- Diagnostics (redacted), Logbook entries, Repairs issues when clusters missing
- Quiet-by-default logging with structured `kv(...)` and user toggles (verbose info/input)

**Architecture Principles (v2.1.0+):**
- **DRY (Don't Repeat Yourself)**: Shared components extracted to common modules
- **Separation of Concerns**: Device-specific logic in dedicated modules
- **Shared-First**: Helper functions and quirk clusters shared across devices
- **Well-Documented**: Comprehensive inline comments explaining WHY, not just WHAT

## Technical Reference Documentation

The `docs/ubisys/` directory contains official Ubisys technical reference manuals for current and upcoming devices:

- **J1/J1-R** - ZigBee Window Covering/Shutter Control (currently implemented)
- **S1/S1-R** - ZigBee Power Switch with smart meter (planned)
- **D1/D1-R** - ZigBee Universal Dimmer with smart meter (planned)

These manuals provide detailed specifications including:
- ZigBee cluster definitions and manufacturer-specific attributes
- Calibration procedures and device configuration
- Endpoint structures and supported commands
- Hardware specifications and compliance information

**Manufacturer ID:** 0x10F2 (all Ubisys devices)

Refer to these documents when implementing support for new devices or working with device-specific features.

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

The J1 calibration module (`j1_calibration.py`) implements a **5-phase automated calibration** using **motor stall detection**:

UI presents “Steps”; developer logs/docs continue to reference “Phases”.

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

3. **Direct Cluster Commands**: Uses `async_zcl_command()` helper (timeouts + retries) for up_open/down_close/stop.

4. **Concurrency Control**: asyncio.Lock per device prevents race conditions from simultaneous calibrations.

### Input Monitoring Architecture (v2.0+)

The input monitoring system detects physical button presses on Ubisys devices and exposes them to Home Assistant for automation triggers.

**Architecture Overview:**

```
Physical Input Press → ZigBee Command → ZHA Event → Input Monitor → Correlation → Home Assistant Event/Trigger
```

**Key Components:**

1. **input_parser.py** - Parses InputActions micro-code
   - `InputActionsParser`: Parses binary InputActions attribute (0xFC00:0x0001)
   - `InputActionRegistry`: Correlates observed commands with inputs/press types
   - `PressType` enum: pressed, released, short_press, long_press, double_press

2. **input_monitor.py** - Monitors ZHA events and fires HA events
   - `UbisysInputMonitor`: One monitor instance per device
   - Subscribes to `zha_event` bus for commands from controller endpoints
   - Correlates observed commands using InputActionRegistry
   - Fires `ubisys_input_event` and dispatcher signals

3. **Integration Lifecycle** (__init__.py)
   - `async_setup_input_monitoring()` called after HA starts
   - Monitors initialized for all Ubisys devices
   - `async_unload_input_monitoring()` during integration unload

**Controller Endpoints:**
- **J1**: Endpoint 2 (Window Covering Controller)
- **D1**: Endpoints 2, 3 (Primary/Secondary Dimmer Switch)
- **S1**: Endpoint 2 (Level Control Switch)
- **S1-R**: Endpoints 2, 3 (Primary/Secondary Level Control Switch)

**Command Correlation Algorithm:**

1. Read InputActions from DeviceSetup cluster (0xFC00:0x0001)
2. Parse micro-code to build mapping: `{(endpoint, cluster, command, payload) → (input_num, press_type)}`
3. Subscribe to ZHA events from controller endpoints
4. When command observed, look up in mapping to determine which input and press type
5. Fire Home Assistant events with context: `device_id, input_number, press_type, command_info`

**Event Flow:**

```
Physical Button Press
    ↓
Device executes InputActions micro-code
    ↓
Device sends ZigBee command from controller endpoint (ep2/ep3)
    ↓
ZHA receives command and fires zha_event
    ↓
UbisysInputMonitor handles zha_event
    ↓
Correlates command signature with InputActions mapping
    ↓
Fires ubisys_input_event (bus event)
    ↓
Fires dispatcher signal (for device triggers and event entities)
    ↓
User automations triggered
```

**Design Decisions:**

1. **Observation, Not Replacement**: We observe commands sent from controller endpoints rather than replacing the device behavior. Local control (physical button → device action) continues to work normally.

2. **ZHA Event Bus**: We use ZHA's existing event infrastructure rather than low-level ZigBee monitoring. This is non-invasive and leverages ZHA's reliable command handling.

3. **Command Correlation**: InputActions parsing allows us to determine which physical input and press type triggered a command, enabling precise automation triggers (e.g., "input 1 long press" vs "input 2 short press").

4. **Shared Architecture**: All three device types (J1, D1, S1) use the same InputActions format and monitoring infrastructure, maximizing code reuse.

### Logging Policy (v2.1+)

- Quiet by default; promote to INFO via options toggles:
  - `verbose_info_logging` for lifecycle/setup/status
  - `verbose_input_logging` for per-input events
- `kv(logger, level, msg, **kvs)`: structured, sorted key=value context; skips formatting if level disabled.
- `info_banner(logger, title, **kvs)`: 3-line banners for major milestones (gated by verbose toggle).
- See docs/logging.md for user guidance.

### Diagnostics, Logbook, Repairs

- Diagnostics: redacted config/options, device info, endpoint/cluster snapshot, last calibration results.
- Logbook: entries for `ubisys_input_event` and calibration completion.
- Repairs: issues raised when expected clusters are missing.

### Options Flow “About”

- Options starts with a menu: `about` (docs/issues links) or `configure` (device-specific options + logging toggles).

## CI & Tests

- GitHub Actions: hassfest, HACS, black/isort/flake8/mypy, pytest with HA 2024.1.*.
- Local CI: `scripts/run_ci_local.sh` and Makefile (`ci`, `fmt`, `lint`, `typecheck`, `test`).
- Tests use `pytest-homeassistant-custom-component`; ZHA/zigpy mocked.

### Current Tests

- InputActions parsing (valid/invalid)
- Attribute write+verify (timeouts/retry, mismatch)
- Options Flow About/menu

### Future Tests

- Input monitor (zha_event → ubisys_input_event correlation)
- Diagnostics payload content and redaction
- Calibration flow happy-path and failure-path (mocked clusters)

## Work Log Expectations (for Claude Code)

Always keep an up‑to‑date, human‑readable log of work performed:

- Append entries to `docs/work_log.md` for every meaningful change set.
  - Use a date heading (YYYY‑MM‑DD) and concise bullets.
  - Summarize what changed (code, docs, CI), why, and any follow‑ups.
- Update `CHANGELOG.md` under the "Unreleased" section to reflect added/changed/fixed/reliability items.
- Use clear, Conventional Commit‑style messages (e.g., `feat:`, `fix:`, `docs:`, `chore(ci):`).

This logbook is separate from HA’s Logbook feature and is intended for developers to quickly understand recent work.

### Device Trigger Architecture (v2.0+ Phase 3)

Device triggers expose physical button presses as automation triggers in the Home Assistant UI, making them user-friendly and discoverable.

**Architecture Overview:**

```
User selects trigger in UI
    ↓
HA calls async_attach_trigger()
    ↓
Subscribe to dispatcher signal from input_monitor
    ↓
Physical button press fires input event
    ↓
input_monitor fires dispatcher signal
    ↓
Receive event, check if matches trigger
    ↓
Call trigger action if match
    ↓
User's automation runs
```

**Key Components:**

1. **device_trigger.py** - Home Assistant device automation integration
   - `async_get_triggers()`: Returns available triggers for a device
   - `async_attach_trigger()`: Attaches listener for trigger events
   - `PRESS_TYPE_TO_TRIGGER`: Maps (input_num, press_type) to trigger type
   - `DEVICE_TRIGGERS`: Defines available triggers per device model

2. **Trigger Types Per Device:**
   - **J1**: 8 triggers (2 inputs × 4 press types)
   - **D1**: 8 triggers (2 inputs × 4 press types)
   - **S1**: 4 triggers (1 input × 4 press types)
   - **S1-R**: 8 triggers (2 inputs × 4 press types)

3. **Press Types:**
   - `button_N_pressed`: Button pressed (start of press)
   - `button_N_released`: Button released
   - `button_N_short_press`: Complete short press (<1s)
   - `button_N_long_press`: Button kept pressed (>1s)

**Integration with Home Assistant:**

Device triggers are automatically discovered by Home Assistant when `device_trigger.py` exists in the integration. No registration needed in `__init__.py` or `PLATFORMS` list.

**User Experience:**

Users create automations via UI:
1. Trigger type: Device
2. Device: [Select Ubisys device]
3. Trigger: [Select "Button 1 short press"]

No YAML or event knowledge required!

**Trigger Context:**

When trigger fires, automation receives context:
```python
{
    "trigger": {
        "platform": "device",
        "domain": "ubisys",
        "device_id": "abc123",
        "type": "button_1_short_press",
        "input_number": 0,  # 0-based
        "press_type": "short_press",
        "description": "Button 1 short press"
    }
}
```

**Design Decisions:**

1. **User-Friendly Names**: Button numbers are 1-based in UI (button_1, button_2) but 0-based internally (input_number=0,1) to match user expectations.

2. **Dispatcher Integration**: Uses dispatcher signals from input_monitor rather than bus events for better performance and type safety.

3. **Model-Specific Triggers**: Each device model has different number of inputs, so triggers are defined per model in `DEVICE_TRIGGERS` dictionary.

4. **Complete Context**: Trigger context includes both user-friendly names and technical details for advanced templating.

**Future Enhancements:**
- Event entities (Phase 4): Show last button press in dashboard with history
- Binary sensors (Phase 5): For stationary rocker switches with persistent state
- Configuration UI (Phase 6): Reconfigure InputActions via UI instead of service calls

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

Calibration is implemented in `custom_components/ubisys/j1_calibration.py` as a service with phase-based architecture.

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
