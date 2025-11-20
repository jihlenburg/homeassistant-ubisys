# Changelog

All notable changes to the Ubisys Home Assistant Integration.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

#### Input Configuration Presets for D1 and J1

- **D1 input presets** with 4 configurations:
  - Toggle + Dim (default): Short press toggles, long press dims up/down
  - Separate up/down buttons: Button 1 brightens, Button 2 dims
  - Rocker switch: Continuous dimming while pressed
  - Decoupled: Events only, HA automation control

- **J1 input presets** with 3 configurations:
  - Up/Down buttons (default): Button 1 opens, Button 2 closes, release stops
  - Single button cycle: Each press cycles open→stop→close→stop
  - Decoupled: Events only, HA automation control

- **S1/S1-R enhanced presets** with dimmer control:
  - Toggle + Dim: Short press toggles, long press dims (control remote dimmers)
  - Brightness up/down buttons (S1-R): Button 1 brightens, Button 2 dims
  - Decoupled: Events only, HA automation control

- **Latching switch presets** for D1 and J1:
  - D1_STEP: Step dimming for latching switches - each press steps brightness up/down
  - J1_ALTERNATING: Alternating up/down for latching switches - simpler 2-state cycle

- **Dynamic UI descriptions** for input configuration:
  - Config flow shows all available presets with descriptions inline
  - Preset explanations customized per device model
  - Uses `description_placeholders` pattern for runtime-built content

- **Options Flow integration** for D1 and J1 input configuration
  - D1: Configure → D1 Advanced Options → Input Configuration
  - J1: Configure → J1 Advanced → Input Configuration
  - S1: Configure → Input Configuration (existing)

- **Input configuration translations** for all new presets

### Documentation

- Updated D1 documentation with input configuration section
- Updated J1 documentation with input configuration section
- Updated S1 documentation with expanded input configuration section
- Added decoupled mode examples with device trigger automations
- Added dimmer control preset use cases for S1/S1-R

### Fixed

- **ZHA entity recovery for D1/S1** - Light and switch platforms now predict entity IDs and automatically recover when ZHA entity appears (matches cover platform behavior)
- **Per-entry input monitoring teardown** - Unloading one device no longer removes input monitors for all devices
- **Consistent service naming** - Changed `calibrate_cover` to `calibrate_j1` for clarity
- **Documentation accuracy** - Fixed all service name references and removed obsolete python_script instructions

## [1.0.0] - 2025-11-19

Initial release with complete feature set.

### Reliability Improvements

- **Motor stall detection** for calibration using OperationalStatus attribute polling
- **Exponential backoff** for transient ZigBee communication failures
- **Orphaned entity cleanup** on device removal and integration unload
- **ZHA entity auto-enable** to prevent wrapper deadlock (hidden but enabled)
- **Graceful degradation** when ZHA entity not yet available (startup race)
- **Per-device locking** to prevent concurrent calibration operations
- **Asymmetry detection** with diagnostic warnings for motor issues

### Features

#### Device Support

- **J1 Window Covering Controller** with smart feature filtering based on shade type
  - Supports roller, cellular, vertical, venetian, and exterior venetian shades
  - Automatic feature masking (tilt controls only for venetian types)
  - Wrapper entity delegates to underlying ZHA cover entity

- **D1 Universal Dimmer** with phase control and ballast configuration
  - Phase mode selection: automatic, forward (leading edge), reverse (trailing edge)
  - Ballast min/max brightness level configuration
  - Multi-entity service support with per-device locking

- **S1/S1-R Power Switch** with input configuration
  - UI-based preset selection with automatic rollback on failure
  - Supports rocker, momentary, and toggle switch types

#### Calibration System

- **5-phase automated calibration** with motor stall detection:
  1. Configure device (WindowCoveringType, limits, Mode)
  2. Find top limit (motor auto-stops at physical limit)
  3. Find bottom limit (device calculates total_steps)
  4. Verification return to top (TotalSteps2 for asymmetry detection)
  5. Configure tilt steps (for venetian blinds)

- **Position preparation phase** ensures shade not at top before calibration
- **OperationalStatus monitoring** for reliable motor stop detection
- **TotalSteps/TotalSteps2 verification** per official Ubisys procedure
- **Re-calibration support** with existing configuration preservation
- **UI notifications** for real-time progress feedback

#### Input Monitoring

- **Physical button press detection** for all Ubisys devices
- **Device triggers** for automations (short press, long press, double press)
- **InputActions parsing** for command correlation
- **Event firing** via `ubisys_input_event` bus event

#### Configuration Services

- `ubisys.calibrate_j1` - Automated J1 calibration
- `ubisys.tune_j1_advanced` - Advanced J1 tuning parameters
- `ubisys.configure_d1_phase_mode` - D1 phase control mode
- `ubisys.configure_d1_ballast` - D1 ballast min/max levels
- `ubisys.cleanup_orphans` - Manual orphaned entity cleanup

### API Compatibility

- **HA 2025.11+ gateway proxy pattern** support
  - `gateway.gateway.devices` (new) vs `gateway.application_controller.devices` (old)
- **Cluster access abstraction** for both API versions
  - `endpoint.zigpy_endpoint.in_clusters` vs `endpoint.in_clusters`
- **Tuple return format** handling for attribute reads
  - `(success_dict, failure_dict)` vs dict
- **Attribute ID parameters** (integers) instead of string names
- **Command method lookup** via `getattr(cluster, command_name)()`

### Developer Experience

- **Comprehensive diagnostics** with redacted output
  - Config entry and options data
  - Device info and ZHA endpoint snapshots
  - Last calibration results with asymmetry data

- **Logbook entries** for input events and calibration completion
- **Repairs integration** for missing clusters or quirks
- **Verbose logging toggles** in options (info logging, input logging)
- **Fast deployment scripts** for SSH-based development workflow
- **Local CI tooling** via Makefile (`ci`, `fmt`, `lint`, `typecheck`, `test`)
- **GitHub Actions** for hassfest, HACS, linting, and pytest

### Breaking Changes

- Removed `ubisys.configure_s1_input` service (use Config Flow UI instead)
- Removed deprecated constant aliases:
  - `UBISYS_ATTR_CONFIGURED_MODE` → use `UBISYS_ATTR_WINDOW_COVERING_TYPE`
  - `SERVICE_CALIBRATE` → use `SERVICE_CALIBRATE_COVER`
  - `D1_DIMMER_ENDPOINT` → use `D1_DIMMABLE_LIGHT_ENDPOINT`

### Architecture

- **Wrapper entity pattern** - Ubisys entities delegate to ZHA entities
- **DRY principle** - Shared components in `helpers.py` and `ubisys_common.py`
- **Single responsibility** - Device-specific logic in dedicated modules
- **Quiet-by-default logging** with structured `kv(...)` output
- **Phase-based calibration** for testability and clear error messages

### Testing

- 82 unit tests with 50% code coverage
- Test coverage for:
  - InputActions parsing (valid/invalid)
  - Attribute write+verify (timeouts/retry, mismatch)
  - Options Flow (about menu, device configuration)
  - Platform wrappers (cover, light, switch)
  - Input monitoring (event correlation)
  - Device triggers (button press filtering)
  - ZHA quirks (manufacturer code injection)

## Links

- [GitHub Repository](https://github.com/jihlenburg/homeassistant-ubisys)
- [Issue Tracker](https://github.com/jihlenburg/homeassistant-ubisys/issues)
- [Documentation](docs/)
