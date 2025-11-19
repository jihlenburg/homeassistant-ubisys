# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]


## [1.3.9] - 2025-11-19

### Fixed
- **CRITICAL: Fixed "infinite loop at top" calibration failure**
  - When shade starts at TOP position, Phase 2 would timeout after 120s
  - Motor reports "running" continuously but can't move (physically blocked)
  - Device auto-stop detection expects MOVEMENT-to-LIMIT, not ALREADY-AT-LIMIT
  - Added Phase 1B: Official Ubisys Procedure Step 4 (move down before finding top)

### Solution (Phase 1B)
**Implements Official Ubisys J1 Technical Reference, Step 4:**
> "Send 'move down' command, then 'stop' after a few centimeters to reach starting position"

**Implementation:**
- After Phase 1 (enter calibration mode), execute Phase 1B
- Send `down_close` command → Wait 2 seconds → Send `stop` command
- Moves ~5-10cm away from top limit (enough to clear limit switch)
- Then Phase 2 can safely find top limit via proper movement-to-limit

**Works from ANY starting position:**
- At TOP: Moves down 6-10cm → **FIXES THE BUG**
- In MIDDLE: Moves down slightly → harmless, adds ~3s
- At BOTTOM: No movement (already at limit) → no-op

### Root Cause Analysis
The J1 device's firmware detects physical limits by monitoring motor current draw:
- **Normal scenario**: Motor moving → hits limit → current spike → auto-stop ✓
- **Bug scenario**: Motor already at limit → tries to move → no current spike → reports "running" indefinitely ✗

The device's calibration mode auto-stop logic is designed for the first scenario. When already at a limit, it can't generate the current spike needed to trigger auto-stop, causing the 120-second timeout.

### Technical Details
- Added `_calibration_phase_1b_prepare_position()` function
- Updated calibration sequence: 1 → **1B** → 2 → 3 → 4 → 5
- Updated UI notifications to show Phase 1B progress
- Module docstring updated to reflect new phase
- Adds ~3 seconds to total calibration time (acceptable trade-off)

### Why This Solution
1. **Manufacturer-documented** - This is the official Ubisys procedure we should have been following
2. **Simple and reliable** - No complex heuristics or attribute monitoring
3. **Handles root cause** - Ensures shade is not at limit before finding limit
4. **Low risk** - Proven approach from manufacturer, worst case adds 3s
5. **Future-proof** - Works for all shade types and starting positions

### Alternative Considered (Rejected)
Monitoring `CurrentPositionLiftPercentage` before calibration was considered but rejected because this attribute **does not update during calibration mode**. Per code analysis and technical reference, position tracking only resumes after calibration completes and device exits calibration mode.


## [1.3.8.5] - 2025-11-19

### Fixed
- **Fixed variable scoping error in v1.3.8.4**
  - `is_recalibration` was defined in Phase 1 but not passed to Phase 5
  - Modified `_calibration_phase_1_enter_mode` to return the flag
  - Captured return value in `_perform_calibration` and passed to Phase 5
  - Emergency hotfix for NameError that broke v1.3.8.4

### Lesson Learned
Variable scoping across phase functions requires proper return values and parameter passing. Phase 1 must return `is_recalibration` so it can be used by Phase 5.


## [1.3.8.4] - 2025-11-19

### Fixed
- **Fixed Phase 5 tilt steps write per official Ubisys documentation**
  - v1.3.8.3 incorrectly skipped tilt steps for ALL re-calibrations
  - **Root cause**: Tilt steps attribute only exists for tilt-capable blinds (venetian)
  - **Per Ubisys J1 Technical Reference Step 8**: "For tilt blinds" (conditional)
  - Roller shades are "lift only" - tilt attribute doesn't exist/isn't writable
  - Device correctly rejected write with MALFORMED_COMMAND error

### Correct Behavior (v1.3.8.4)
**Write tilt steps ONLY when:**
- First-time calibration, AND
- Shade type is venetian (has both lift & tilt capability)

**Skip tilt steps when:**
- Re-calibration (preserve existing configuration), OR
- Shade type is lift-only (roller, cellular, vertical, awning, drapery)

### Technical Details
Ubisys shade types:
- Type 0-5, 9: **Lift only** (roller, awning, etc.) - No tilt attribute
- Type 6-7: **Tilt only** (shutters) - Different use case
- Type 8: **Lift & Tilt** (venetian) - Has LiftToTiltTransitionSteps attribute

The attribute `0x10F2:0x1001` (LiftToTiltTransitionSteps) is configuration-specific to the mechanical blind type, not a measured value. Writing it to non-tilt shades causes MALFORMED_COMMAND error.


## [1.3.8.3] - 2025-11-18

### Fixed
- **Fixed Phase 5 tilt steps write for re-calibration**
  - Device rejects tilt steps write when already calibrated
  - Phase 5 now skips tilt steps write for re-calibration (device won't accept)
  - First-time calibration still writes tilt steps normally
  - Re-calibration now completes all 5 phases successfully!

### Technical Details
Similar to TotalSteps in Phase 1, the device locks LiftToTiltTransitionSteps after initial calibration. For re-calibration, we detect this in Phase 1 and skip the tilt steps write in Phase 5. The device retains its original tilt configuration.


## [1.3.8.2] - 2025-11-18

### Fixed
- **Fixed undefined function error in v1.3.8.1**
  - Used non-existent `async_read_attrs()` function
  - Changed to use `cluster.read_attributes()` directly
  - Emergency hotfix for v1.3.8.1 which broke calibration entirely


## [1.3.8.1] - 2025-11-18

### Fixed
- **Fixed re-calibration attribute write failure**
  - Device was correctly refusing to accept 0xFFFF for TotalSteps when already calibrated
  - Modified `_prepare_calibration_limits()` to detect already-calibrated devices
  - For re-calibration: Only writes physical limits, skips steps reset
  - For first-time calibration: Writes everything including steps reset (0xFFFF)
  - Entering calibration mode (Step 3) is what triggers re-calibration, not writing 0xFFFF

### Technical Details
The J1 device refuses to accept 0xFFFF for TotalSteps/TotalSteps2 attributes when it already has a valid calibration. This is correct device behavior - it prevents accidental de-calibration. The fix reads the current TotalSteps value first and adapts the write operation accordingly.


## [1.3.8.0] - 2025-11-18

### Added
- **UI Notifications for Calibration Progress**
  - Persistent notifications show real-time calibration progress
  - Updates after each phase with visual progress indicators
  - Shows estimated time remaining (2-3 minutes)
  - Success notification with total steps measured
  - Error notification with helpful troubleshooting info
  - Solves issue where UI gave no feedback after clicking "Calibrate"

### User Experience
When you click "Calibrate" button, you'll now see:
1. **Initial notification**: "Calibration started" with Phase 1 status
2. **Progress updates**: Each phase shows ✅ when complete, next phase in progress
3. **Success notification**: Shows all completed phases and total steps
4. **Error notification**: Shows what went wrong if calibration fails

The notification updates automatically as the calibration progresses through all 5 phases, giving you visibility into what's happening during the 2-3 minute process.


## [1.3.7.9] - 2025-11-18

### Fixed
- **Fixed undefined variable in Phase 4 verification**
  - Phase 4 was trying to return `final_position` which didn't exist
  - Changed to return 100 (interface compatibility - verification doesn't track position)
  - Calibration now completes all 5 phases successfully!

### Success
With v1.3.7.9, the complete calibration flow is now working:
- ✅ Phase 1: Preparation (WindowCoveringType, limits, Mode)
- ✅ Phase 2: Find top limit (motor auto-stops at ~37s)
- ✅ Phase 3: Find bottom limit (motor auto-stops at ~35s)
- ✅ Phase 4: Verification return to top (motor auto-stops at ~37s)
- ✅ Phase 5: Finalization (tilt steps, exit calibration mode)

All three motor stop detections working correctly thanks to v1.3.7.8 falsy zero fix!


## [1.3.7.8] - 2025-11-18

### Fixed
- **CRITICAL**: Fixed "falsy zero" bug in OperationalStatus detection
  - Motor stopped status (0x00) was being treated as "attribute missing"
  - Code used `result.get(attr) or result.get("name")` which treats 0 as falsy
  - Changed to proper `is None` checking: `if result.get(attr) is None: try fallback`
  - Device WAS returning correct value, but Python's `or` operator was the culprit
  - Classic Python gotcha: `<bitmap8: 0> or None` evaluates to `None`, not `0`!

### Technical Details
The bug was in j1_calibration.py line 1574-1576:
```python
# WRONG - treats 0 as falsy!
operational_status = result.get(OPERATIONAL_STATUS_ATTR) or result.get("operational_status")

# CORRECT - only use fallback if truly None
operational_status = result.get(OPERATIONAL_STATUS_ATTR)
if operational_status is None:
    operational_status = result.get("operational_status")
```

When device returned `{10: <bitmap8: 0>}` (motor stopped), the `or` operator saw the zero value as falsy and evaluated the right side, returning `None` instead of `0`. This caused calibration to fail with "OperationalStatus attribute missing" errors even though the device was correctly reporting motor stopped.

**Lesson**: Never use `or` for fallback when the valid value might be 0, False, empty string, or other falsy values. Always check `is None` explicitly.


## [1.3.7.7] - 2025-11-18

### Fixed
- **CRITICAL**: Fixed Mode attribute (0x0017) access - it's STANDARD ZCL, not manufacturer-specific!
  - v1.3.7.6 was writing with manufacturer code 0x10F2, but 0x0017 is a standard attribute
  - Device correctly returned UNSUPPORTED_ATTRIBUTE (134) because 0x10F2:0x0017 doesn't exist
  - Mode attribute must be accessed WITHOUT manufacturer parameter
  - Fixed `_enter_calibration_mode()` and `_exit_calibration_mode()` functions

### Added
- **Official Procedure Step 2**: Write initial calibration limits before entering mode
  - Added `_prepare_calibration_limits()` function
  - Writes physical limits (0-240cm lift, 0-90° tilt) per official documentation
  - Marks TotalSteps/transition steps as 0xFFFF (uncalibrated) for clean calibration
  - Required for re-calibration scenarios (resets device to uncalibrated state)
  - Reference: Ubisys J1 Technical Reference, Section 7.2.5.1, Step 2

### Changed
- **Architecture improvements** for maintainability:
  - Added clear constants: `MODE_ATTR`, `MODE_CALIBRATION`, `MODE_NORMAL`
  - Added limit attribute constants: `UBISYS_ATTR_INSTALLED_*_LIMIT_*`
  - Updated Phase 1 to follow official 3-step procedure (WindowCoveringType → Limits → Mode)
  - Comprehensive documentation explaining standard vs manufacturer-specific attributes

### Technical Details
According to official Ubisys documentation (line 228 of Technical Reference):
- Attribute 0x0017 (Mode) is listed under "Window Covering Cluster - Standard Attributes"
- NOT under "Manufacturer-Specific Attributes (Cluster 0x10F2)" (line 230)
- This is why our code was failing - we were accessing the wrong namespace!

**Correct Attribute Access:**
- Standard attributes (like 0x0017 Mode): Write WITHOUT manufacturer code
- Manufacturer attributes (like 0x10F2:0x1002 TotalSteps): Write WITH manufacturer code 0x10F2

### Testing
- All 81 tests passing
- Coverage improved from 22% → 52% (test mock enhancements)
- Updated test imports to use new constant names

### Why v1.3.7.6 Failed
The v1.3.7.6 rewrite was architecturally correct (OperationalStatus monitoring, auto-stop detection), but had a simple parameter bug: passing `manufacturer=0x10F2` when writing the standard Mode attribute. This version fixes that critical bug and adds the missing Step 2 from the official procedure.


## [1.3.7.6] - 2025-11-18

### Fixed
- **MAJOR**: Rewrote J1 calibration to match official Ubisys procedure
  - **Root cause**: v1.3.7.1-7.5 fixed API compatibility but calibration logic itself was fundamentally wrong
  - Old approach monitored `current_position` which doesn't update during calibration mode
  - Falsely detected "stall" after 3 seconds → sent stop command → motor never reached limits
  - Device returned total_steps=0xFFFF (uninitialized) because calibration never completed

### Changed
- **Calibration algorithm completely rewritten** based on "Ubisys J1 Technical Reference" official documentation
  - Device **auto-stops** at physical limits during calibration (current spike detection)
  - Monitor `OperationalStatus` (0x000A) to detect when motor stopped, NOT position
  - REMOVED all "stop" commands from Phases 2, 3, 4 (device stops itself)
  - Added `_wait_for_motor_stop()` function with 230 lines of comprehensive documentation
  - Kept `_wait_for_stall()` unchanged for safety (non-breaking approach)

### Technical Details
- Added OperationalStatus monitoring constants (0x000A attribute, bitmap flags)
- Phase 2: Send up_open → wait for OperationalStatus=0x00 → top limit learned
- Phase 3: Send down_close → wait for OperationalStatus=0x00 → device calculates total_steps
- Phase 4: Send up_open → wait for OperationalStatus=0x00 → verification complete
- Updated test mocks to return written values for verification
- All 81 tests passing

### Why This Matters
During calibration mode (mode=0x02), the Ubisys J1:
- Does NOT update `current_position` attribute (meaningless until calibration completes)
- DOES update `OperationalStatus` to show motor running/stopped state
- AUTOMATICALLY detects limits via current spike and stops motor itself
- Only calculates `total_steps` AFTER completing full top→bottom movement

This matches Step 5-7 of official Ubisys calibration procedure and should finally allow successful calibration on HA 2025.11+.


## [1.3.7.5] - 2025-11-18

### Fixed
- **Critical**: Fixed attribute read parameter format in `read_attributes` calls
  - HA 2025.11+ requires attribute IDs (integers), not attribute names (strings)
  - Error: `Failed to read total_steps attribute: 'total_steps'` during Phase 3
  - Fixed `j1_calibration.py:888` to use `UBISYS_ATTR_TOTAL_STEPS` constant instead of string
  - Also fixed health check attribute read (lines 483-493) to handle tuple responses

### Technical Details
- `read_attributes()` parameter format changed:
  - Old: `read_attributes(["total_steps"])` - accepts strings
  - New: `read_attributes([0x1002])` - requires integer attribute IDs only
- Health check now handles both tuple and list response formats from HA 2025.11+


## [1.3.7.4] - 2025-11-18

### Fixed
- **Critical**: Fixed cluster command execution in `async_zcl_command`
  - HA 2025.11+ changed cluster command API
  - Old: `cluster.command(command_name, *args, **kwargs)`
  - New: `getattr(cluster, command_name)(*args, **kwargs)` - call command method directly
  - Error: `Cluster command failed: up_open: 'up_open'` during calibration
  - Fixed `helpers.py:741-745` to use getattr for command method lookup
  - J1 calibration motor commands now work correctly (up_open, down_close, stop)
  - Also affects D1 configuration commands

### Technical Details
- The `cluster.command()` method no longer exists in HA 2025.11+
- Commands are now attributes on the cluster object (e.g., `cluster.up_open()`)
- Used `getattr(cluster, command_name)` to dynamically look up and call command methods
- Updated test mocks to use `__getattr__` to support dynamic command method creation

## [1.3.7.3] - 2025-11-18

### Fixed
- **Critical**: Fixed `read_attributes` response handling in `write_and_verify_attribute`
  - HA 2025.11+ returns tuple `(success_dict, failure_dict)` instead of dict
  - Normalization code only handled list, not tuple
  - Error: `'tuple' object has no attribute 'get'` during calibration attribute writes
  - Fixed `helpers.py:806-811` to extract success dict from tuple before accessing
  - J1 calibration attribute writes now work correctly

### Technical Details
- `read_attributes()` return format changed in HA 2025.11+:
  - Old: returns dict directly
  - New: returns tuple `({attr_id: value}, {attr_id: error})`
- Added tuple handling before list handling in response normalization
- Affects all device types (J1, D1, S1) that use `write_and_verify_attribute`

## [1.3.7.2] - 2025-11-18

### Fixed
- **Critical**: Fixed ZHA Endpoint API compatibility (missed in v1.3.7.1)
  - Fixed `'Endpoint' object has no attribute 'in_clusters'` error on HA 2025.11+
  - Updated `j1_calibration.py:_get_window_covering_cluster()` EP1 and EP2 probing with endpoint compatibility wrapper
  - Updated `helpers.py:get_cluster()` with endpoint compatibility wrapper
  - Updated `diagnostics.py:async_get_config_entry_diagnostics()` endpoint iteration with compatibility wrapper
  - J1 calibration now actually works on HA 2025.11+ (was still broken in v1.3.7.1)
  - Diagnostics endpoint snapshots now load correctly

### Technical Details
- HA 2025.11+ changed both gateway AND endpoint structure
- Endpoints now wrap underlying zigpy endpoints
- Old API: `endpoint.in_clusters`, `endpoint.out_clusters`
- New API: `endpoint.zigpy_endpoint.in_clusters` or `endpoint.all_cluster_handlers`
- Added three-tier compatibility check for all cluster access points
- v1.3.7.1 only fixed gateway device access but missed endpoint cluster access

## [1.3.7.1] - 2025-11-18

### Fixed
- **Critical**: Fixed incomplete ZHA Gateway API compatibility (missed in v1.3.6.7)
  - Fixed `j1_calibration.py:_get_window_covering_cluster()` still using old `gateway.application_controller.devices` API
  - Fixed `diagnostics.py:async_get_config_entry_diagnostics()` still using old API
  - Calibration now works on HA 2025.11+ (was broken despite v1.3.6.7 claiming to fix it)
  - Diagnostics endpoint data now loads correctly on HA 2025.11+
  - Both functions now use same compatibility pattern as `helpers.py:get_cluster()`
  - Comprehensive audit verified all ZHA gateway device accesses now wrapped

### Technical Details
- `j1_calibration.py` line 1591: Added hasattr() check for `application_controller` vs `gateway.devices`
- `diagnostics.py` line 65: Added same compatibility wrapper
- The v1.3.6.7 fix only updated `helpers.py:get_cluster()` but missed direct gateway access in J1 calibration
- Root cause: J1 calibration has custom endpoint probing logic (EP1 then EP2) so doesn't use `get_cluster()` helper

## [1.3.7] - 2025-11-18

### Added
- **New Service**: `ubisys.cleanup_orphans` - Automated cleanup of orphaned devices and entities
  - Removes orphaned entities with no valid config entry
  - Removes deleted devices still in registry's recycle bin (like the "Jalousie" ghost device)
  - Supports `dry_run` parameter for safe preview without making changes
  - Displays persistent notifications with cleanup results
  - Solves the "old device names appearing during setup" problem
  - Eliminates need for manual registry editing or Home Assistant downtime
  - Created new `cleanup.py` module with comprehensive cleanup logic
  - Updated `services.yaml` with detailed service documentation and examples
  - Enhanced `__init__.py` service handler with user feedback notifications

### Changed
- Service registration now includes comprehensive orphan cleanup handler
  - Replaces stub `_cleanup_orphans_service()` with full implementation
  - Integrates with new `cleanup.py` module for device/entity detection and removal

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

## [1.3.7.5] - 2025-11-18

### Fixed
- **Critical**: Fixed attribute read using string name instead of ID
  - J1 calibration read_attributes() called with string `["total_steps"]` instead of attribute ID
  - HA 2025.11+ requires attribute IDs (integers), not names (strings)
  - Error: `'total_steps'` during calibration Phase 3
  - Fixed `j1_calibration.py:888` to use `UBISYS_ATTR_TOTAL_STEPS` constant
  - Added tuple response handling for consistency
  - J1 calibration total_steps reading now works

### Technical Details
- `read_attributes()` parameter changed in HA 2025.11+:
  - Old: Accepted string names OR integer IDs
  - New: Only accepts integer IDs
- Always use attribute ID constants, never string names
