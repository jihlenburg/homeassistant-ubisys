# Work Log

This log tracks meaningful development work on the Ubisys integration.

## 2025-11-18

### Bugfix: Calibration Buttons on Non-Motor Devices

**Context**: User reported seeing "Calibrate" and "Health Check" buttons on S1 (switch) device, which doesn't have a motor or any calibration needs.

**Root Cause**: `button.py:async_setup_entry()` was creating calibration buttons for ALL devices without checking the model type. Only J1/J1-R window covering devices have motors that need calibration.

**Fix Applied** (button.py:73-118):
- Added model extraction: `model = config_entry.data.get("model", "J1")`
- Added model filtering: `if model not in WINDOW_COVERING_MODELS: return`
- Added comprehensive comments explaining why each device type does/doesn't need calibration
- Mirrors the same pattern used in `cover.py:53-63`

**Device Type Matrix**:
- J1/J1-R (window covering): ✅ Calibration buttons (learns motor travel limits)
- D1/D1-R (dimmer): ❌ No calibration buttons (no motor, has input config via service)
- S1/S1-R (switch): ❌ No calibration buttons (no motor, has input config via service)

**Impact**: S1 and D1 devices will no longer show confusing calibration buttons. Only J1 devices will have them.

**Testing**: Will be validated via CI and manual testing on S1 device.

---

### Documentation: ZHA Gateway Compatibility Layer

**Context**: Following v1.3.6.5-v1.3.6.7 releases that fixed HA 2025.11+ compatibility issues, updated all documentation to reflect the new ZHA gateway compatibility patterns.

**Changes:**

1. **helpers.py:resolve_zha_gateway() docstring** (lines 53-72)
   - Added explanation of `.gateway_proxy` attribute (HA 2025.11+)
   - Documented ZHAGatewayProxy wrapper pattern
   - Added compatibility notes explaining priority ordering

2. **helpers.py:get_cluster() docstring** (lines 275-299)
   - Added "How It Works" section explaining two-path device access
   - Added "Why Two Device Access Patterns" section
   - Documented old API (`gateway.application_controller.devices`) vs new API (`gateway.gateway.devices`)

3. **CLAUDE.md** - Added comprehensive "ZHA Gateway Compatibility Layer" section (lines 216-372)
   - Problem statement: HA 2025.11+ breaking changes
   - Architecture diagram showing compatibility layer
   - Code patterns for gateway access and device registry access
   - Design decisions (graceful fallback, priority ordering, diagnostic logging, centralized functions)
   - Guidance for handling future HA API changes
   - Version history

**Rationale**: After releasing three emergency hotfixes for HA 2025.11+ compatibility (v1.3.6.5, v1.3.6.6, v1.3.6.7), the code was working but documentation was outdated. This update ensures future developers understand:
- Why we check multiple attribute names
- Why we have two device access patterns
- How to handle future HA API changes

**Follow-up**: None required - documentation now accurately reflects implementation.
---

### Feature: Automated Orphan Cleanup Service

**Context**: User encountered "ghost" device named "Jalousie" that kept appearing during integration setup. Investigation revealed orphaned devices in registry's `deleted_devices` list (recycle bin) from previous integration installations.

**Problem Discovery**:
1. SSH'd into HA and inspected `/config/.storage/core.device_registry`
2. Found 2 orphaned devices in `deleted_devices` list:
   - "Jalousie" (from old integration setup)
   - One unnamed orphaned device
3. Manual cleanup required stopping HA, editing registry JSON, restarting HA
4. User requested automated solution to prevent recurrence

**Solution**: Implemented `ubisys.cleanup_orphans` service (v1.3.7)

**Implementation Details**:

1. **Created cleanup.py module** (new file):
   - `async_cleanup_orphans()`: Main service handler with dry_run support
   - `_find_orphaned_devices()`: Scans `deleted_devices` list for Ubisys identifiers
   - `_find_orphaned_entities()`: Finds entities with missing/invalid config_entry_id
   - `_remove_deleted_devices()`: Removes orphans from recycle bin and saves registry
   - Returns detailed results (device IDs, entity IDs, dry_run flag)

2. **Updated __init__.py** (lines 95, 324-402):
   - Added import: `from .cleanup import async_cleanup_orphans`
   - Enhanced `_cleanup_orphans_service()` handler with comprehensive logic
   - Added voluptuous schema: `vol.Optional("dry_run", default=False): cv.boolean`
   - Implemented persistent notifications for user feedback (both dry_run preview and actual cleanup results)
   - Integrated verbose logging with existing logging toggles

3. **Updated services.yaml** (lines 272-327):
   - Added comprehensive service definition with detailed description
   - Documented what gets cleaned, when to use, safety features, example scenarios
   - Added dry_run field with boolean selector
   - Included helpful tip: "Always run with dry_run=true first!"

**Key Features**:
- **Dry Run Mode**: Preview orphans without making changes (shows persistent notification)
- **Safe**: Only removes items with Ubisys identifiers (`DOMAIN="ubisys"`)
- **Comprehensive**: Handles both orphaned entities AND orphaned devices in deleted_devices
- **User Feedback**: Persistent notifications show cleanup results
- **No Downtime**: Runs while HA is running (unlike manual registry editing)

**Testing**: All 81 CI tests passing

**Impact**:
- Users can now clean up ghost devices via Developer Tools → Services → ubisys.cleanup_orphans
- Eliminates need for manual registry editing, SSH access, or HA downtime
- Solves recurring "old device names appearing during setup" issue

**Files Modified**:
- `custom_components/ubisys/cleanup.py` (new, 250 lines)
- `custom_components/ubisys/__init__.py` (enhanced service handler)
- `custom_components/ubisys/services.yaml` (added service definition)
