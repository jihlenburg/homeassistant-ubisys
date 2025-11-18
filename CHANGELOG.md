# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.3.6.8] - 2025-11-18

### Fixed
- **Bug**: Calibration buttons incorrectly created for D1/S1 devices
  - Calibration buttons now only appear for J1/J1-R window covering devices
  - D1 (dimmer) and S1 (switch) devices don't have motors, so calibration makes no sense
  - Added model filtering to `button.py:async_setup_entry()` (same pattern as `cover.py`)
  - Prevents confusing UI where non-applicable buttons appear on device pages

### Documentation
- **Developer Documentation**: Comprehensive update to reflect HA 2025.11+ ZHA compatibility layer
  - Updated `helpers.py:resolve_zha_gateway()` docstring with `.gateway_proxy` attribute explanation
  - Updated `helpers.py:get_cluster()` docstring with two-path device access pattern explanation
  - Added new "ZHA Gateway Compatibility Layer" section to CLAUDE.md (architecture documentation)
  - Documents gateway access patterns, device registry access patterns, design decisions, and future guidance
  - Created `docs/work_log.md` to track development work chronologically

## [1.3.6.7] - 2025-11-17

### Fixed
- **Critical**: Fixed ZHAGatewayProxy device access API compatibility
  - Added support for new `gateway_proxy.gateway.devices` API (HA 2025.11+)
  - Maintains backward compatibility with `gateway.application_controller.devices` (older HA)
  - Resolves "ZHAGatewayProxy object has no attribute 'application_controller'" error
  - Calibration and input monitoring now work on HA 2025.11+

### Technical Details
- Updated `helpers.py:get_cluster()` to check for both API patterns:
  - New: `gateway.gateway.devices` (ZHAGatewayProxy wrapping gateway)
  - Old: `gateway.application_controller.devices` (direct gateway object)
- Enhanced error logging shows gateway type and available attributes if unknown pattern
- Full backward compatibility maintained for all HA versions

## [1.3.6.6] - 2025-11-17

### Fixed
- **Critical**: Added missing `logbook` dependency to manifest.json
  - Resolves hassfest CI validation error introduced in v1.3.6.4
  - When logbook registration was moved inline, dependency declaration was missed
  - Home Assistant's hassfest validator requires all component imports to be declared
  - Integration functionality unaffected (only CI validation failed)

### Technical Details
- Updated `manifest.json` dependencies from `["zha"]` to `["zha", "logbook"]`
- Satisfies Home Assistant integration quality requirements
- No code changes - purely metadata fix for CI compliance

## [1.3.6.5] - 2025-11-17

### Fixed
- **Critical**: Fixed ZHA gateway resolution for Home Assistant 2025.11+ with new HAZHAData structure
  - Updated `resolve_zha_gateway()` to support both `gateway_proxy` (HA 2025.11+) and `gateway` (older versions)
  - Resolves "ZHA gateway not found" errors preventing calibration and input monitoring
  - Backward compatible with older Home Assistant versions
  - Debug logging enhanced to show which attribute pattern was found (`gateway_proxy` vs `gateway`)
- **Critical**: Fixed KeyError when loading J1 cover entities with missing shade_type in config
  - Added graceful fallback: checks `options` first, then `data`, defaults to "roller"
  - Prevents integration setup failure for config entries created in older versions
  - Maintains backward compatibility with all previous config entry formats
  - Existing users will see "roller" shade type behavior until they reconfigure via UI

### Technical Details
- `helpers.py:resolve_zha_gateway()` now checks for both `.gateway_proxy` and `.gateway` attributes
- `cover.py:async_setup_entry()` uses safe multi-level lookup: `options → data → default`
- ZHA data structure changed in HA 2025.11.x from `.gateway` to `.gateway_proxy`
- All 81 tests passing, code formatted and linted

## [1.3.6.4] - 2025-11-17

### Fixed
- **Critical**: Eliminated Python 3.13+ blocking I/O warning for logbook platform
  - Moved logbook event registration from separate `logbook.py` file to inline code in `__init__.py`
  - Python 3.13+ warns about synchronous `import_module()` calls in async event loop
  - Home Assistant's platform loader was importing `logbook.py` synchronously
  - Solution: Register logbook events directly in `async_setup()` to avoid platform discovery
  - Deleted obsolete `logbook.py` file and associated test
  - No more "Detected blocking call to import_module" warnings in logs

### Improved
- Enhanced diagnostic logging in `resolve_zha_gateway()` helper
  - Added comprehensive debug output showing ZHA data structure inspection
  - Logs data type, dict keys/values, candidate checks, and search results
  - Helps troubleshoot "ZHA gateway not found" errors on different HA versions
  - Warning logged if gateway not found with instructions to report with debug logs
  - Makes future ZHA data structure changes easier to diagnose and fix

### Technical Details
- Logbook registration now calls `logbook.async_describe_event()` directly in `async_setup()`
- Event descriptions: `ubisys_calibration_complete` and `ubisys_input_event`
- Enhanced `resolve_zha_gateway()` logging shows candidate types and search progress
- All 81 tests passing, code formatted and linted

## [1.3.6.3] - 2025-11-17

### Documentation
- Updated v1.3.6 release notes to properly document D1 multi-entity service support
  - `ubisys.configure_d1_phase_mode` and `ubisys.configure_d1_ballast` multi-entity capability
  - ZHA gateway discovery improvements documented
- Enhanced D1 Universal Dimmer documentation with multi-entity examples
- Updated user guide with D1 service usage patterns

## [1.3.6.2] - 2025-11-17

### Changed
- Completed DRY refactoring for ZHA gateway resolution
  - Applied `resolve_zha_gateway()` helper to diagnostics.py
  - Eliminated final instance of duplicated gateway resolution code
  - Diagnostics now benefit from robust multi-pattern gateway discovery
  - Improved code coverage: diagnostics.py 87% → 90%
  - All modules now use centralized helper from helpers.py

### Fixed
- Fixed documentation formatting in `resolve_zha_gateway()` docstring
  - Consistent indentation for all bullet points

## [1.3.6.1] - 2025-11-17

### Fixed
- **Critical**: Fixed ZHA gateway resolution failure on newer Home Assistant versions
  - Calibration was failing with "ZHA gateway not found" error
  - Root cause: Inline gateway resolution only handled 2 of 3 HA data structure patterns
  - Newer HA versions use `{entry_id: HAZHAData}` pattern which was not handled
  - Solution: Extracted robust `resolve_zha_gateway()` helper to `helpers.py`
  - Now handles all 3 known HA patterns: direct object, dict with "gateway" key, and dict of HAZHAData objects
  - Uses defensive `iter_candidates()` pattern to probe both dict itself and dict values
  - Eliminates duplication across codebase (used in calibration, config, input modules)
  - Future-proof: extensible design for HA's evolving data structures

### Technical Details
- Added `resolve_zha_gateway(zha_data)` to `helpers.py`
- Updated `_get_window_covering_cluster()` in `j1_calibration.py` to use new helper
- Gateway resolution now checks: `zha_data.gateway`, `zha_data["gateway"]`, and `zha_data[entry_id].gateway`
- Graceful failure: returns None if gateway not found, lets callers provide context-specific error messages

## [1.3.6] - 2025-11-17

### Added
- Multi-entity calibration support for `ubisys.calibrate_j1` service
  - Accepts single entity ID or list of entity IDs
  - Processes entities sequentially with per-device locking
  - Reports partial failures with detailed summary
  - Each entity processed independently (failure doesn't stop others)

### Changed
- Refactored J1 calibration module for better separation of concerns
  - `async_calibrate_j1()`: Entry point handling multiple entities
  - `_async_calibrate_single_entity()`: Single entity validation & calibration
  - `_async_run_calibration_health_check()`: Dedicated test mode function
- Updated documentation and service descriptions for multi-entity workflow
- `ubisys.configure_d1_phase_mode` / `ubisys.configure_d1_ballast` now accept
  multiple entities per call and serialize writes with per-device locks.

### Fixed
- Restored missing helper functions after refactoring
  - `_find_zha_cover_entity()`: ZHA entity lookup
  - `_validate_device_ready()`: Pre-flight checks
  - `async_tune_j1()`: Advanced tuning service handler
- Cleaned up imports (removed duplicates, restored required constants)
- ZHA gateway discovery now handles Home Assistant's entry-scoped ZHA data
  structure, preventing "ZHA gateway not found" errors during calibration
  and D1 service calls.

## [1.3.5.2] - 2025-11-17

### Fixed
- **Critical**: Fixed J1 calibration test_mode indentation bug
  - Health check block now properly nested under `if test_mode:`
  - Verbose logging flag now only controls banner display, not entire check
  - Previously: health check ran when verbose logging enabled, regardless of test_mode
  - When verbose=on + test_mode=off: calibration aborted (returned early)
  - When verbose=off + test_mode=on: motor driven (health check skipped)
- **Tests**: Fixed test failures in integration bootstrap tests
  - Added mocks for `_ensure_zha_entity_enabled` and `_untrack_zha_entities`
  - Tests now properly initialize entity registry mocks
- **Code Quality**: Removed unused variables in `__init__.py` (flake8 cleanup)
  - Removed unused `orphaned_count` and `tracked` variables

### Documentation
- **Workflow**: Added comprehensive pre-commit CI workflow guidelines to CLAUDE.md
  - Documents required steps before every commit (fmt, lint, test, ci)
  - Historical lesson from v1.3.5.1 CI failures
  - Test-driven development pattern for core files
  - Common pitfalls and CI failure recovery procedures

### Technical Details
- Bug was in `j1_calibration.py:208-245` where `if is_verbose_info_logging(hass):` was not indented under `if test_mode:`
- This caused the health check to execute based on logging settings instead of test_mode flag
- Fix ensures test_mode always runs health check and returns before real calibration
- Verbose logging now only controls whether info_banner is displayed during health check

## [1.3.5.1] - 2025-11-17

### Fixed
- **Critical**: Fixed uninstall regression introduced in v1.3.5
  - `_unhide_zha_entity()` now checks `hidden_by` instead of `disabled_by`
  - ZHA entities are properly restored when integration is removed
  - Respects "easy to revert to ZHA" architectural constraint
- **Critical**: Automatic orphaned entity cleanup on device removal
  - Device registry listener now handles device deletion
  - Orphaned entities cleaned up immediately when device removed
  - Prevents ghost entities from persisting after device deletion or crashes
- Removed unused `Event` import from cover.py (lint compliance)

### Added
- **Manual cleanup service**: `ubisys.cleanup_orphans`
  - Manually trigger orphaned entity cleanup for all devices
  - Useful for historical orphans or troubleshooting
  - Shows persistent notification with cleanup results
  - No parameters required

### Technical Details
- v1.3.5 changed ZHA entity state from `disabled_by=INTEGRATION` to `disabled_by=None`
- Original unhide logic checked for `disabled_by=INTEGRATION`, always failing
- New logic checks `hidden_by=INTEGRATION` (what we actually care about)
- Conditionally clears `disabled_by` only if set by integration (respects user choice)
- Device registry listener enhanced to handle "remove" action
- Hybrid cleanup approach: automatic (device removal) + manual (service call)

### Version Note
- Adopted 4-part versioning (a.b.c.d) for better hotfix granularity
- This is hotfix 1 for v1.3.5 (hence 1.3.5.1)

## [1.3.5] - 2025-11-17

### Fixed
- **Critical**: Centralized ZHA entity auto-enable logic to fix all wrapper platforms
  - v1.3.3/v1.3.4 only protected cover platform (J1), leaving light platform (D1) broken
  - Unified architecture: single integration-level listener in `__init__.py`
  - All wrapper platforms (cover, light, future platforms) now protected automatically
  - Removed duplicate per-platform logic (~100 lines of boilerplate eliminated)

### Architecture
- **Major refactoring**: Moved auto-enable logic from platform files to integration core
  - New `_ensure_zha_entity_enabled()` helper in `__init__.py`
  - Single integration-level entity registry listener (replaces per-platform listeners)
  - Platforms no longer need setup-time enable or registry monitoring code
  - Future wrapper platforms get protection "for free"

### Technical Details
- Integration-level listener monitors all tracked ZHA entities via shared set
- `tracked_zha_entities` set maintained in `hass.data[DOMAIN]`
- Thread-safe via `@_typed_callback` decorator on listener
- DRY principle: one source of truth for ZHA entity lifecycle management
- Pattern scales: adding new wrapper platforms requires zero enable/disable logic

## [1.3.4] - 2025-11-17

### Fixed
- **Critical**: Fixed thread safety violation in entity registry listener
  - Refactored nested function to class method to enable @callback decorator
  - Added @_typed_callback decorator to ensure execution in event loop thread
  - Prevents "calls async_update_entity from wrong thread" error
  - v1.3.3 attempted to fix mypy by removing decorator, which broke thread safety
  - Now satisfies both thread safety requirements AND mypy type checking

### Technical Details
- Entity registry update handlers must run in event loop thread, not thread pool
- Without @callback decorator, Home Assistant schedules handler as Executor job (separate thread)
- Calling async_update_entity() from wrong thread triggers verify_event_loop_thread() check
- Solution: @callback decorator sets _hass_callback attribute → runs in event loop
- Matches device_tracker pattern from Home Assistant core

## [1.3.3] - 2025-11-17

### Fixed
- **Critical**: Fixed ZHA entity auto-enable race condition
  - Added entity registry update listener to continuously monitor ZHA entity
  - Automatically re-enables ZHA entity if disabled by ZHA integration
  - Previous fix only ran during setup, missing entities that loaded after ubisys
  - Now responds immediately when ZHA disables its entity after detecting wrapper
  - Pattern validated against Home Assistant core (device_tracker integration uses identical logic)

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
