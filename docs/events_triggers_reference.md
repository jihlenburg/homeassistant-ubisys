# Events & Triggers Reference

Compatibility: Home Assistant 2024.1+ (Python 3.11+)

Docs: [index](index.md) · [device triggers examples](device_triggers_examples.md) · [services reference](services_reference.md)

## ubisys_input_event (bus event)

Fired for physical input activity (buttons/switches).

Payload:
- `device_ieee` (string)
- `device_id` (string)
- `model` (string): e.g., J1, D1
- `input_number` (int): 0-based
- `press_type` (string): pressed | released | short_press | long_press
- `command` (object): { endpoint, cluster, command }

Use via event triggers or Device Triggers in the UI.

## Device Triggers (UI)
- Triggers are exposed per device; select the Ubisys device and choose an input press type.
- See examples: docs/device_triggers_examples.md

## Calibration Events

### ubisys_calibration_complete
- Fired when J1 calibration completes successfully
- Fields: entity_id, device_ieee, shade_type, duration_s

### ubisys_calibration_failed
- Fired when J1 calibration fails
- Fields: entity_id, device_ieee, shade_type, error

Notes
- Logbook shows friendly messages for these events.
- Diagnostics includes last calibration results (redacted).
