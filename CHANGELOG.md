# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.2.9] - 2025-11-16

### Fixed
- Hotfix: Corrected parameter names in device registry API calls
- `add_config_entry` → `add_config_entry_id`
- `remove_config_entry_id` (correct)
- Made config_entries access more defensive using getattr()

### Technical Details
- v1.2.8 used incorrect parameter name `add_config_entry` instead of `add_config_entry_id`
- This caused `TypeError: DeviceRegistry.async_update_device() got an unexpected keyword argument`
- Integration failed to set up completely
- v1.2.9 fixes parameter names and adds defensive attribute access

## [1.2.8] - 2025-11-16

### Fixed
- Critical device registry bug where v1.2.7 created separate Ubisys and ZHA devices instead of sharing one device
- Wrapper entities can now find ZHA entities (previously failed because entities were on different devices)
- Calibration and other features now work correctly (previously failed with "Unknown error")
- `_ensure_device_entry()` now searches for existing ZHA device and links Ubisys config entry to it
- Device identifiers properly merged: both ("zha", ieee) and ("ubisys", ieee) on same device

### Technical Details
- Home Assistant's device registry matches identifiers as exact tuples
- v1.2.7 used `("ubisys", ieee)` which created a NEW device separate from ZHA's `("zha", ieee)` device
- v1.2.8 searches device registry for existing ZHA device and uses `async_update_device()` to link both integrations
- This is the correct multi-integration device pattern: both ZHA and Ubisys share one physical device entry

### Added
- Automatic cleanup of orphaned Ubisys devices created by v1.2.7
- `_cleanup_orphaned_ubisys_device()` removes config entry from orphaned devices
- Home Assistant will garbage-collect empty devices automatically

### Migration Note
- Users upgrading from v1.2.7: orphaned Ubisys devices are automatically cleaned up
- No manual intervention required - cleanup happens during first startup with v1.2.8
- Cleanup is non-destructive and logged at INFO level

## [1.2.7] - 2025-11-16

### Fixed
- Critical bug where entities would link to deleted devices when re-configuring the integration
- Entities no longer appear orphaned with wrong device name after deleting and re-adding integration

### Added
- Explicit device entry creation during setup to prevent entity-device mismatches
- Automated cleanup for orphaned entities (runs during setup and unload)
- `_ensure_device_entry()` helper that creates/restores device entry before entities are created
- `_cleanup_orphaned_entities()` helper that removes orphaned entities automatically

### Reliability
- Device registry entries now explicitly linked to config entries
- Deleted devices automatically restored when re-adding integration
- Clear logging when orphaned entities are cleaned up

## [1.2.6] - 2025-11-14

### Fixed
- Service registration schemas corrected (use vol.Schema instead of cv.make_entity_service_schema)
- Fixes "missing 1 required positional argument: 'call'" error in HA 2025.x
- All services now work correctly: calibrate_j1, tune_j1_advanced, configure_d1_phase_mode, configure_d1_ballast

## [1.2.5] - 2025-11-14

### Fixed
- Service registration now includes schemas for HA 2025.x compatibility (fixes "missing 1 required positional argument" error)
- All services (calibrate_j1, tune_j1_advanced, configure_d1_phase_mode, configure_d1_ballast) now work correctly

## [1.2.4] - 2025-11-13

### Fixed
- Options menu translation error ("device_name" variable not provided)

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
