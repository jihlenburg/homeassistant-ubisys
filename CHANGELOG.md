# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed
- **Critical**: Fixed ZHA entity auto-enable race condition
  - Added entity registry update listener to continuously monitor ZHA entity
  - Automatically re-enables ZHA entity if disabled by ZHA integration
  - Previous fix only ran during setup, missing entities that loaded after ubisys
  - Now responds immediately when ZHA disables its entity after detecting wrapper

## [1.3.2] - 2025-11-17

### Documentation
- **Clarity improvement**: Renamed `docs/README.md` → `docs/user_guide.md`
  - Eliminates confusion between top-level README.md (GitHub intro) and comprehensive user guide
  - Top-level README.md remains as GitHub-focused introduction with badges and quick start
  - docs/user_guide.md is now clearly identified as the comprehensive integration documentation
  - All internal links updated to reflect new naming
- **Major restructuring**: Consolidated documentation from 31 files to 12 files (61% reduction)
  - **Phase 1**: Consolidated 5 troubleshooting files into comprehensive `troubleshooting.md`
  - **Phase 2**: Organized device guides into `docs/devices/` subdirectory
    - Merged J1 calibration and advanced tuning into `devices/j1_window_covering.md`
    - Moved D1 and S1 configuration guides to devices subdirectory
  - **Phase 3**: Created comprehensive user guide `docs/README.md` following HA integration template
    - Merged 8 user-facing files: getting_started, installation, common_tasks, examples, services_reference, events_reference, device_support_matrix, device_triggers_examples
  - **Phase 4**: Consolidated developer documentation
    - All developer content now in root-level `CONTRIBUTING.md`
    - Deleted 7 architecture/development files: development, architecture_overview, shared_architecture, window_covering_architecture, device_trigger_testing, input_monitoring_testing, work_log
  - **Phase 5**: Cleanup and validation
    - Fixed all internal documentation links
    - Removed orphaned file references
    - Validated markdown formatting
- Documentation structure now follows best practices with clear separation of concerns:
  - User documentation: `docs/README.md` (comprehensive integration guide)
  - Device guides: `docs/devices/` (J1, D1, S1 specific documentation)
  - Troubleshooting: `docs/troubleshooting.md` (consolidated problem-solving)
  - Developer documentation: `CONTRIBUTING.md` (architecture, testing, contributing)

### Fixed
- **Critical**: Fixed multiple Home Assistant 2024.1+ compatibility issues
  - Fixed service registration pattern - D1 service handlers now receive correct parameters
  - Fixed ZHA data access compatibility (HAZHAData object vs dictionary)
  - Applied compatibility fixes in: `__init__.py`, `j1_calibration.py`, `diagnostics.py`, `helpers.py`

### Technical Details
- **Service Registration Bug**: D1 service wrappers were passing `call` object, but handlers expected individual parameters (`entity_id`, `phase_mode`, etc.)
  - Fixed `_configure_phase_mode_handler()` to extract and pass parameters correctly
  - Fixed `_configure_ballast_handler()` to extract and pass parameters correctly
- **ZHA Data Access Bug**: HA 2024.1+ changed ZHA data from `dict` to `HAZHAData` object
  - Old pattern: `zha_data.get("gateway")` or `zha_data["gateway"]`
  - New pattern: `zha_data.gateway` (object attribute)
  - Applied compatibility layer that checks `hasattr()` first, falls back to dict access
  - Ensures backward compatibility with older HA versions
  - Fixed in 3 locations: `j1_calibration.py`, `diagnostics.py`, and `helpers.py` (from v1.3.1)

## [1.3.1] - 2025-11-16

### Fixed
- **Critical**: ZHA entity auto-disabled causing wrapper to be unavailable
- Wrapper entity now auto-enables ZHA entity if disabled by integration
- Respects user's choice if entity disabled manually (doesn't override)
- ZHA entity remains hidden (users only see wrapper), but is enabled for state delegation

### Technical Details
- v1.3.0's graceful degradation created a chicken-and-egg problem:
  - ZHA detected wrapper entity and auto-disabled its own entity to prevent duplicates
  - Wrapper depended on ZHA entity having a state
  - Result: wrapper showed as "unavailable" indefinitely
- v1.3.1 solution: Auto-enable ZHA entity during setup if `disabled_by=INTEGRATION`
  - ZHA entity: `hidden=true` + `enabled=true` = "internal state source"
  - Wrapper entity: `visible=true` + `enabled=true` = "user-facing entity"
  - This pattern prevents deadlock while respecting both integrations' roles

### Architecture
- Added comprehensive inline documentation explaining the problem and solution
- Defensive checks: only enables if disabled by integration (not by user)
- Error handling: logs warning if enable fails, graceful degradation continues
- Idempotent: safe to run multiple times (checks before acting)

## [1.3.0] - 2025-11-16

### Fixed
- **Critical**: Startup race condition where Ubisys cover entity wouldn't be created if it loaded before ZHA
- Cover wrapper entity now uses graceful degradation pattern from HA core best practices
- Entity shows as "unavailable" with clear reason when ZHA entity doesn't exist yet
- Automatic recovery when ZHA entity appears (no reload/restart needed)

### Technical Details
- `_find_zha_cover_entity()` now predicts entity ID if ZHA entity not found yet
- Added `_zha_entity_available` flag to track ZHA entity state
- Added `available` property that checks ZHA entity existence and availability
- Enhanced `_sync_state_from_zha()` to handle missing entity gracefully and detect when it appears
- State change listener automatically triggers recovery when ZHA entity becomes available
- Pattern based on `homeassistant/components/template/cover.py` and `homeassistant/components/group/cover.py`

### Reliability
- Wrapper entity ALWAYS created, even if ZHA entity missing (shows as unavailable until ready)
- No more "Could not find ZHA cover entity" errors during startup
- Works for both startup race conditions and devices that haven't been paired with ZHA yet
- Added debug attribute `unavailable_reason` for troubleshooting

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
