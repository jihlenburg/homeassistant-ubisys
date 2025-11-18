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
