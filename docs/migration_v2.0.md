# Migration Guide: v1.x to v2.1.0

## Overview

This guide helps you migrate from earlier versions of the Ubisys integration (v1.x) to version 2.1.0+.

## Breaking Changes

### 1. S1 Input Configuration Service Removed

**What Changed**:
- Service `ubisys.configure_s1_input` has been removed
- Configuration is now done via UI (Settings � Devices � Configure)

**Migration Steps**:

1. **Identify Usage**:
   Search your automations/scripts for `ubisys.configure_s1_input`

2. **Remove Service Calls**:
   Delete any automation/script that calls this service

3. **Reconfigure via UI**:
   - Go to Settings � Devices & Services � Ubisys
   - Select your S1/S1-R device
   - Click "Configure"
   - Select appropriate preset

**Before (v1.x)**:
```yaml
service: ubisys.configure_s1_input
data:
  entity_id: switch.kitchen_s1
  input_config: "01020304..."  # Raw micro-code
```

**After (v2.1.0)**:
- Use Config Flow UI (no YAML needed)
- Select preset from dropdown
- Configuration stored automatically

### 2. File Renames (Developers Only)

If you're developing with this integration:

- `calibration.py` � `j1_calibration.py`
- Update imports: `from .j1_calibration import async_calibrate_j1`

## New Features in v2.1.0

### 1. UI-Based Input Configuration

- **All devices**: Configure inputs through UI, not services
- **Automatic rollback**: Failed configs automatically revert
- **Preset-based**: Choose from user-friendly presets

### 2. Shared Architecture

- **Better code organization**: Reduced duplication across devices
- **Shared helpers**: Common functions centralized
- **Shared quirks**: DeviceSetup cluster shared across all devices

### 3. Enhanced Documentation

- Comprehensive inline code comments
- Device-specific configuration guides
- Architecture documentation

## Upgrade Checklist

- [ ] Update integration to v2.1.0
- [ ] Remove `ubisys.configure_s1_input` service calls
- [ ] Reconfigure S1/S1-R devices via UI
- [ ] Test all physical inputs work as expected
- [ ] Test automations using device triggers
- [ ] Verify D1/J1 configurations still work

## Troubleshooting

### Service Not Found Error

**Symptom**: `ubisys.configure_s1_input service not found`

**Cause**: Service was removed in v2.1.0

**Solution**: Remove service call, use Config Flow UI instead

### Configuration Lost After Upgrade

**Symptom**: Physical switches don't control relay after upgrade

**Cause**: Configuration needs to be reapplied via UI

**Solution**: Reconfigure device through Settings � Devices � Configure

### Import Errors (Developers)

**Symptom**: `cannot import name 'async_calibrate_j1' from 'calibration'`

**Cause**: Module renamed to `j1_calibration.py`

**Solution**: Update import:
```python
# Before
from .calibration import async_calibrate_j1

# After
from .j1_calibration import async_calibrate_j1
```

## Rollback Instructions

If you need to rollback to v1.x:

1. Uninstall v2.1.0 via HACS
2. Install v1.x version
3. Restart Home Assistant
4. Reconfigure devices using old service

**Note**: Rollback not recommended - v2.1.0 has significant improvements

## Support

If you encounter issues during migration:

1. Check [Troubleshooting Guide](troubleshooting.md)
2. Review device-specific docs:
   - [J1 Calibration](devices/j1_window_covering.md)
   - [D1 Configuration](devices/d1_universal_dimmer.md)
   - [S1 Configuration](devices/s1_power_switch.md)
3. Open issue on GitHub with logs

## See Also

- [S1 Configuration Guide](devices/s1_power_switch.md)
- [Contributing Guide](../CONTRIBUTING.md)
- [Troubleshooting](troubleshooting.md)
