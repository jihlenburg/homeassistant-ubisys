# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.2.3] - 2025-11-13

### Fixed
- Platform files now skip creating entities for wrong device types, eliminating spurious error logs and extra entities

## [1.2.2] - 2025-11-13

### Fixed
- Config flow now handles ZHA device models with parenthetical suffixes (e.g., "J1 (5502)")

### Added
- Troubleshooting documentation for device discovery issues

## [1.2.1] - 2025-11-13

### Added
- Options Flow: "About" menu step with links to docs/issues and device info.
- Diagnostics: redacted config entry/device info, ZHA endpoints/clusters snapshot, last calibration results.
- Logbook: friendly entries for `ubisys_input_event` and calibration completion.
- Repairs: issues created when required clusters/quirks are missing.
- Logging toggles: `verbose_info_logging` and `verbose_input_logging` in Options.
- Local CI tooling: `scripts/run_ci_local.sh` and Makefile (`ci`, `fmt`, `lint`, `typecheck`, `test`).
- GitHub Actions CI: hassfest/HACS, lint/type, and tests against HA 2024.1.*.

### Changed
- Quieter default logging; many INFO logs gated behind verbose toggles.
- Calibration banners gated by verbose toggle; added persistent notifications for start/success/failure.
- Documentation refreshed (README, logging policy, triggers examples, CLAUDE.md).

### Fixed
- button.py: cleaned up duplicate/odd `async_press` definitions; explicit calibration vs. health check buttons.

### Reliability
- helpers: `async_write_and_verify_attrs` now includes async timeouts and a limited retry.
- helpers: new `async_zcl_command` wrapper for cluster commands with timeouts/retry; used in calibration.

## [1.2.0] - 2025-11-12

### Breaking Changes

- **Removed**: `ubisys.configure_s1_input` service (deprecated since v2.0)
  - S1/S1-R input configuration is now done via Config Flow UI
  - See [Migration Guide](docs/migration_v2.0.md) for upgrade instructions

### Added

- **Documentation**: Comprehensive inline code comments across all modules
- **Documentation**: New user guides:
  - S1/S1-R configuration guide (`docs/s1_configuration.md`)
  - Migration guide v1.x � v2.1.0 (`docs/migration_v2.0.md`)
- **Architecture**: Detailed endpoint allocation comments in `const.py`
- **Architecture**: Explained button�service pattern in `button.py`
- **Architecture**: Detailed InputActions correlation documentation

### Changed

- **Refactor**: Renamed `calibration.py` � `j1_calibration.py` for consistency
- **Refactor**: Extracted shared helper functions to `helpers.py`:
  - `extract_model_from_device()` - shared by device_trigger and input_monitor
  - `extract_ieee_from_device()` - shared by device_trigger and input_monitor
- **Refactor**: Created shared quirk module `custom_zha_quirks/ubisys_common.py`:
  - `UbisysDeviceSetup` cluster - shared by D1, S1, and J1 quirks
  - Common constants (`UBISYS_MANUFACTURER_CODE`, etc.)
- **Documentation**: Enhanced module docstrings with detailed explanations

### Removed

- **Deprecated**: Removed `s1_config.py` module entirely (obsoleted by Config Flow)
- **Deprecated**: Removed `SERVICE_CONFIGURE_S1_INPUT` constant
- **Deprecated**: Removed duplicate helper function implementations
- **Deprecated**: Removed duplicate DeviceSetup cluster definitions

### Fixed

- **Input Config**: Corrected D1 preset availability (both D1 and D1-R have 2 inputs)
- **Input Config**: Fixed S1_ROCKER preset to use endpoint constants
- **Input Config**: Updated preset descriptions for clarity

## [1.1.1] - Previous Release

### Added
- J1 window covering calibration support
- D1 universal dimmer configuration
- S1/S1-R power switch support
- Input monitoring and device triggers

## Migration Notes

### Upgrading to 1.2.0

1. **S1/S1-R Users**: Remove any `ubisys.configure_s1_input` service calls from automations
2. **S1/S1-R Users**: Reconfigure devices via UI (Settings � Devices � Configure)
3. **Developers**: Update imports from `.calibration` to `.j1_calibration`
4. **All Users**: Test functionality after upgrade

See [Migration Guide](docs/migration_v2.0.md) for detailed instructions.

## Links

- [GitHub Repository](https://github.com/jihlenburg/homeassistant-ubisys)
- [Issue Tracker](https://github.com/jihlenburg/homeassistant-ubisys/issues)
- [Documentation](docs/)
