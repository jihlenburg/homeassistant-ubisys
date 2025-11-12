# Services Reference

Compatibility: Home Assistant 2024.1+ (Python 3.11+)

Docs: [index](index.md) · [events reference](events_triggers_reference.md) · [common tasks](common_tasks.md)

## ubisys.calibrate_j1
- Purpose: Run automated calibration for J1 cover.
- Fields:
  - `entity_id` (string): Ubisys cover entity.
  - Optional: `test_mode` (bool) — read-only health check (no movement).

## ubisys.tune_j1_advanced
- Purpose: Write J1 advanced manufacturer attributes.
- Fields (optional unless noted):
  - `entity_id` (string, required)
  - `turnaround_guard_time` (0–65535, 50ms units)
  - `inactive_power_threshold` (0–65535, mW)
  - `startup_steps` (0–65535)
  - `additional_steps` (0–100, %)

## ubisys.configure_d1_phase_mode
- Purpose: Set D1 phase control mode.
- Fields:
  - `entity_id` (string): Ubisys light entity
  - `phase_mode` (string): `automatic` | `forward` | `reverse`

## ubisys.configure_d1_ballast
- Purpose: Set D1 ballast min/max brightness levels.
- Fields:
  - `entity_id` (string)
  - `min_level` (1–254, optional)
  - `max_level` (1–254, optional)

Notes
- Prefer Options Flow for presets and routine configuration.
- Advanced attribute writes are verified with readback; failures roll back.
