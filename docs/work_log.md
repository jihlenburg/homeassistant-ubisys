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
