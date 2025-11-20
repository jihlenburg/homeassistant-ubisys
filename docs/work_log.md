# Development Work Log

Technical notes and implementation details for the Ubisys integration.

## Calibration System

### Motor Stall Detection

The calibration system uses OperationalStatus attribute polling to detect when the motor has stopped:

- **Attribute**: OperationalStatus (0x000A) - standard ZCL attribute
- **Polling interval**: 0.5 seconds
- **Detection**: Motor stopped when status = 0x00 (all bits clear)
- **Timeout**: 120 seconds (generous for large blinds)
- **Retry logic**: Up to 5 consecutive read failures before giving up

**Why OperationalStatus, not Position?**
During calibration mode (mode=0x02), the J1 device does NOT update current_position
(meaningless until calibration completes). Only OperationalStatus updates in real-time.

### Phase-Based Architecture

The calibration follows the official Ubisys procedure:

1. **Phase 1: Preparation** - Configure device (WindowCoveringType → limits → Mode=0x02)
2. **Phase 1B: Position prep** - Move down briefly to ensure not at top limit
3. **Phase 2: Find top** - Send up_open → wait for OperationalStatus=0x00
4. **Phase 3: Find bottom** - Send down_close → wait for OperationalStatus=0x00
5. **Phase 4: Verify** - Send up_open → wait for OperationalStatus=0x00
6. **Phase 5: Finalize** - Write tilt steps (venetian only) → exit calibration mode

**Key insight**: The device auto-stops at physical limits during calibration. We do NOT
send stop commands - this would interrupt calibration before limits are learned.

### TotalSteps Asymmetry Detection

Per official Ubisys procedure, both directional step counts are verified:

- **TotalSteps (0x1002)**: DOWN movement steps (open→closed)
- **TotalSteps2 (0x1004)**: UP movement steps (closed→open)

Asymmetry is normal due to gravity and mechanical factors:
- **<5%**: Optimal mechanical condition
- **5-10%**: Acceptable, within spec
- **>10%**: May indicate binding, friction, or motor wear

### Re-calibration Support

The device refuses to accept 0xFFFF for TotalSteps when already calibrated.
Phase 1 detects this and adapts:
- First calibration: Writes everything including steps reset
- Re-calibration: Only writes physical limits, preserves existing configuration

## ZHA Integration

### Gateway Compatibility

The integration supports both old and new HA ZHA data structures:

**Direct Gateway pattern** (older HA):
```python
devices = gateway.application_controller.devices
```

**Gateway Proxy pattern** (HA 2025.11+):
```python
devices = gateway.gateway.devices
```

Detection is automatic via `hasattr()` checks. The `resolve_zha_gateway()` helper
abstracts this for all gateway access points.

### Cluster Access

Multiple API patterns exist for cluster access on endpoints:

1. `endpoint.in_clusters.get(cluster_id)` - old API
2. `endpoint.zigpy_endpoint.in_clusters.get(cluster_id)` - HA 2025.11+
3. `endpoint.all_cluster_handlers.get(cluster_id).cluster` - alternative

The `get_cluster()` helper tries all patterns in sequence.

### Attribute Read Response Format

HA 2025.11+ changed read_attributes return format:
- **Old**: Returns dict directly
- **New**: Returns tuple `(success_dict, failure_dict)`

Always extract first element when tuple is returned:
```python
if isinstance(result, tuple) and len(result) >= 1:
    result = result[0]
```

### Command Method Lookup

HA 2025.11+ removed `cluster.command(name)`. Commands are now attributes:
- **Old**: `await cluster.command("up_open")`
- **New**: `await getattr(cluster, "up_open")()`

### Standard vs Manufacturer-Specific Attributes

**Critical distinction** that caused early bugs:

- Standard ZCL attributes (0x0000-0x00FF): Access WITHOUT manufacturer code
- Manufacturer-specific (0x10F2:0x0000+): Access WITH manufacturer code 0x10F2

Example: Mode attribute (0x0017) is STANDARD, not manufacturer-specific.
Writing with manufacturer code causes UNSUPPORTED_ATTRIBUTE error.

## Entity Management

### Wrapper Architecture

Ubisys entities wrap underlying ZHA entities:

1. ZHA creates its entity (cover, light, switch)
2. Ubisys creates wrapper entity that delegates to ZHA entity
3. ZHA entity is hidden but enabled for state delegation
4. Wrapper entity filters features and provides custom UI

State synchronization via `async_track_state_change_event()` listener.

### ZHA Entity Lifecycle

The ZHA entity must be enabled (not disabled) for the wrapper to function:

- **Hidden**: Yes (users only see wrapper)
- **Enabled**: Yes (must have state for wrapper to read)

If ZHA detects wrapper and auto-disables its entity, we re-enable it.
Only re-enable if `disabled_by=INTEGRATION` (respect user choice).

### Graceful Degradation

Wrapper entity handles startup race conditions:

1. Predicts ZHA entity ID if not found yet
2. Shows as "unavailable" with reason attribute
3. Automatically recovers when ZHA entity appears
4. No reload/restart required

### Orphaned Entity Cleanup

Entities without valid config_entry_id are cleaned up:
- On integration unload
- On device removal
- Via manual `ubisys.cleanup_orphans` service

Devices in registry's `deleted_devices` list are also removed.

## Input Monitoring

### Command Correlation

The InputActions micro-code maps physical inputs to commands:

1. Read InputActions attribute from DeviceSetup cluster (0xFC00:0x0001)
2. Parse micro-code to build mapping: `{(endpoint, cluster, command) → (input_num, press_type)}`
3. Subscribe to ZHA events from controller endpoints
4. Correlate observed commands to determine which input and press type
5. Fire `ubisys_input_event` with context

### Controller Endpoints

- **J1**: Endpoint 2 (Window Covering Controller)
- **D1**: Endpoints 2, 3 (Primary/Secondary Dimmer Switch)
- **S1**: Endpoint 2 (Level Control Switch)
- **S1-R**: Endpoints 2, 3 (Primary/Secondary Level Control Switch)

### Device Triggers

Triggers are automatically discovered by HA when `device_trigger.py` exists.
User-friendly button names (button_1, button_2) map to internal 0-based input numbers.

## Common Pitfalls

### Falsy Zero Bug

Never use `or` for fallback when valid values can be falsy:
```python
# WRONG - treats 0 as falsy
status = result.get(attr) or result.get("name")

# CORRECT - only fallback if truly None
status = result.get(attr)
if status is None:
    status = result.get("name")
```

This caused motor stop detection (0x00) to be treated as "missing".

### Position Monitoring in Calibration

Position attribute does NOT update during calibration mode. Use OperationalStatus instead.

### Attribute ID vs Name

HA 2025.11+ requires integer attribute IDs, not string names:
```python
# WRONG
await cluster.read_attributes(["total_steps"])

# CORRECT
await cluster.read_attributes([0x1002])
```

### API Parameter Verification

Always verify parameter names against actual Home Assistant API before releasing.
The v1.2.8 incident used `add_config_entry` instead of `add_config_entry_id`.

## Input Configuration Presets

### Preset Architecture

Input presets are defined in `input_config.py` with three key components:

1. **InputConfigPreset enum**: All available preset identifiers
2. **PRESET_INFO dict**: Human-readable names and descriptions
3. **MODEL_PRESETS dict**: Available presets per device model

### Micro-code Generation

Each preset maps to `InputActionBuilder` methods that generate micro-code:

- **build_simple_toggle()**: Single action (short press → toggle)
- **build_dimmer_toggle_dim()**: Three actions (short press + alternating long presses)
- **build_dimmer_up_down()**: Four actions (2 buttons × 2 actions each)
- **build_cover_rocker()**: Four actions (pressed + released for each button)
- **build_cover_toggle()**: Four alternating actions for cycle behavior

### Decoupled Mode Implementation

Decoupled presets return an empty action list (`[]`), meaning:
- No InputActions micro-code is written to the device
- Physical buttons don't control the output directly
- Button press events are still detected by input monitoring
- Device triggers fire to Home Assistant for automations

**Important**: This is NOT the same as "smart bulb mode". The device still processes
button presses locally and sends events - it doesn't require HA to be online.

### Options Flow Integration

The flow sequence varies by device type:

- **S1/S1-R**: configure → input_config
- **D1/D1-R**: configure → d1_options → input_config
- **J1/J1-R**: configure → j1_advanced → input_config

This ensures device-specific settings (phase mode, ballast, tuning) are configured
before input presets.

### J1 Window Covering Presets

J1 presets use WindowCovering cluster (0x0102) commands:

- **CMD_UP_OPEN (0x00)**: Open/raise the covering
- **CMD_DOWN_CLOSE (0x01)**: Close/lower the covering
- **CMD_WC_STOP (0x02)**: Stop movement

**Cover Rocker preset**: Uses pressed/released transitions for continuous movement:
```
Button 1 pressed → up_open
Button 1 released → stop
Button 2 pressed → down_close
Button 2 released → stop
```

**Cover Toggle preset**: Uses alternating short presses for cycling:
```
Press 1 → up_open (alternating=True)
Press 2 → stop (alternating=True)
Press 3 → down_close (alternating=True)
Press 4 → stop (alternating=False, ends cycle)
```

### D1 Dimmer Presets

D1 presets use Level Control (0x0008) and On/Off (0x0006) clusters:

**Toggle + Dim preset**:
```
Short press → toggle (On/Off cluster)
Long press → move up (alternating=True)
Long press → move down (ends cycle)
```

**Up/Down preset**:
```
Button 1 short → on
Button 1 long → move up
Button 2 short → off
Button 2 long → move down
```

### S1 Dimmer Control Presets

S1/S1-R devices can control remote dimmers via ZigBee group binding using
these presets (reuses D1 builder functions for DRY principle):

**Toggle + Dim preset** (single button, S1 or S1-R):
```
Short press → toggle (On/Off cluster)
Long press → move up (alternating=True)
Long press → move down (ends cycle)
```

**Up/Down preset** (dual button, S1-R only):
```
Button 1 short → on
Button 1 long → move up
Button 2 short → off
Button 2 long → move down
```

Use case: Install S1-R near a doorway to control a D1 dimmer in another
location. Local control works even if Home Assistant is offline.

### Latching Switch Presets

Latching switches (push-on/push-off switches that stay in position) require
different control patterns since you can't "hold" them for continuous control.

**D1_STEP preset** (step dimming):
```
Short press 1 → step up (LevelControl CMD_STEP, mode=0x00)
Short press 2 → step down (LevelControl CMD_STEP, mode=0x01)
(cycle repeats)
```

Each press adjusts brightness by ~12.5% (step_size=32 out of 254). This provides
fine-grained control without needing to hold a button.

**J1_ALTERNATING preset** (alternating up/down):
```
Short press 1 → up_open
Short press 2 → down_close
(cycle repeats)
```

Simpler than J1_TOGGLE (2 states vs 4 states). The covering stops at limits
automatically. Press during movement to reverse direction.

**Why these are better for latching switches:**
- Only use SHORT_PRESS transitions (no hold detection needed)
- Simple 2-state alternation is intuitive
- Each press makes immediate progress
- Works naturally with how latching switches function

### Endpoint Constants

Each device type has dedicated endpoint constants:

```python
# S1 endpoints
S1_PRIMARY_ENDPOINT = 2
S1R_SECONDARY_ENDPOINT = 3

# D1 endpoints
D1_PRIMARY_ENDPOINT = 2
D1_SECONDARY_ENDPOINT = 3

# J1 endpoints
J1_PRIMARY_ENDPOINT = 2
J1_SECONDARY_ENDPOINT = 3
```

These are used in `build_preset()` to generate correct source endpoints.

## Dynamic UI Descriptions

### Pattern Implementation

Config flow steps can display dynamic, context-aware descriptions using `description_placeholders`.
The pattern builds information at runtime and injects it into translation strings.

**Input Configuration Step** (implemented):
```python
# Build preset info lines from available presets
preset_info_lines = []
for preset in available_presets:
    name, description = InputConfigPresets.get_preset_info(preset)
    preset_info_lines.append(f"• **{name}**: {description}")

# Pass to form
description_placeholders={
    "device_name": device_name,
    "preset_info": "\n".join(preset_info_lines),
}
```

Translation string uses `{preset_info}` placeholder:
```json
"description": "Select behavior for {device_name}.\n\n**Available presets:**\n{preset_info}"
```

### Future Enhancement Opportunities

**About/Device Status (High Value)**:
- J1: Show TotalSteps, TotalSteps2, asymmetry %, last calibration date
- All devices: Show current input preset, ZigBee signal strength
- Would require reading device attributes asynchronously

**J1 Advanced Tuning (Medium Value)**:
- Show current device values alongside input fields
- User sees what they're changing from/to
- Example: "Current turnaround guard time: 10 (50ms units)"

**D1 Options (Medium Value)**:
- Show current phase mode and ballast levels
- Explain what each phase mode does
- Example: "Current: Automatic | Min: 10% | Max: 100%"

**Implementation Considerations**:
- Device reads add latency to config flow opening
- May need async loading with spinners
- Cache device values to avoid repeated reads
- Consider "Refresh" button for re-reading device state

