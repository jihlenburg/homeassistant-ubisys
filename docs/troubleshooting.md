# Troubleshooting Guide

Compatibility: Home Assistant 2024.1+ (Python 3.11+)

Docs: [index](index.md) · [user guide](user_guide.md) · [logging policy](logging.md)

This guide helps you diagnose and fix common issues with the Ubisys Home Assistant integration.

## Table of Contents

- [Installation Issues](#installation-issues)
- [Integration Setup Issues](#integration-setup-issues)
- [Device Communication Issues](#device-communication-issues)
- [Calibration Issues](#calibration-issues)
- [Position Control Issues](#position-control-issues)
- [Tilt Control Issues](#tilt-control-issues)
- [Logging and Debugging](#logging-and-debugging)
 - [Repairs](#repairs)

## Installation Issues

### Integration Not Showing in Add Integration Menu

**Symptoms:**
- Cannot find "Ubisys" when searching for integrations
- Integration exists in `custom_components` but not visible

**Diagnostic Steps:**
```bash
# Check if files exist
ls -la ~/.homeassistant/custom_components/ubisys/

# Check manifest
cat ~/.homeassistant/custom_components/ubisys/manifest.json
```

**Solutions:**

1. **Verify file structure:**
   ```
   custom_components/ubisys/
   ├── __init__.py
   ├── manifest.json
   ├── config_flow.py
   ├── const.py
   ├── cover.py
   ├── services.yaml
   ├── strings.json
   └── translations/
       └── en.json
   ```

2. **Check manifest.json syntax:**
   ```bash
   python3 -m json.tool ~/.homeassistant/custom_components/ubisys/manifest.json
   ```

3. **Restart Home Assistant:**
   ```bash
   # Via CLI
   ha core restart

   # Or restart the host
   sudo systemctl restart home-assistant@homeassistant
   ```

4. **Check logs:**
   ```bash
   grep -i ubisys ~/.homeassistant/home-assistant.log
   ```

### Quirk Not Loading

**Symptoms:**
- Manufacturer-specific attributes not available
- Standard ZHA functionality works but enhanced features don't

**Diagnostic Steps:**
```bash
# Check quirk file exists
ls -la ~/.homeassistant/custom_zha_quirks/ubisys_j1.py

# Check configuration.yaml
grep -A 2 "^zha:" ~/.homeassistant/configuration.yaml
```

**Solutions:**

1. **Verify configuration.yaml:**
   ```yaml
   zha:
     custom_quirks_path: custom_zha_quirks
   ```

2. **Check quirk syntax:**
   ```bash
   python3 -m py_compile ~/.homeassistant/custom_zha_quirks/ubisys_j1.py
   ```

3. **Restart ZHA:**
   - Go to Configuration → Integrations
   - Find ZHA
   - Click ⋮ → Reload

4. **Verify quirk loaded:**
   - Go to Configuration → Integrations → ZHA
   - Click Configure → Devices
   - Select your J1 device
   - Check "Signature" - should show custom cluster

### Python Script Not Working

**Symptoms:**
- Calibration service fails
- Error: "Service python_script.ubisys_j1_calibrate not found"

**Diagnostic Steps:**
```bash
# Check file exists
ls -la ~/.homeassistant/python_scripts/ubisys_j1_calibrate.py

# Check configuration
grep -i "python_script" ~/.homeassistant/configuration.yaml
```

**Solutions:**

1. **Enable python_script in configuration.yaml:**
   ```yaml
   python_script:
   ```

2. **Verify file permissions:**
   ```bash
   chmod 644 ~/.homeassistant/python_scripts/ubisys_j1_calibrate.py
   ```

3. **Restart Home Assistant**

4. **Check available services:**
   - Go to Developer Tools → Services
   - Filter for "python_script"
   - Should see `python_script.ubisys_j1_calibrate`

## Integration Setup Issues

### No ZHA Cover Entities Found

**Symptoms:**
- Config flow shows "No ZHA cover entities available"
- Cannot proceed with setup

**Causes:**
- J1 not paired with ZHA
- J1 paired but not exposed as cover entity
- Cover entity is disabled

**Solutions:**

1. **Pair device with ZHA:**
   - Configuration → Integrations → ZHA
   - Click "Add Device"
   - Put J1 in pairing mode

2. **Check entity is enabled:**
   - Configuration → Integrations → ZHA
   - Click "Devices"
   - Find your J1
   - Click device name
   - Check if cover entity is disabled (click to enable)

3. **Force reconfigure ZHA device:**
   - ZHA → Devices → Your J1
   - Click ⋮ → Reconfigure

### Selected Entity Not Working

**Symptoms:**
- Setup completes but entity doesn't respond
- Entity shows as "unavailable"

**Solutions:**

1. **Verify ZHA entity works:**
   - Go to Developer Tools → States
   - Find your ZHA cover entity
   - Try controlling it directly
   - If ZHA entity doesn't work, issue is with ZHA not this integration

2. **Check device power:**
   - Verify device has power
   - Check ZHA signal strength

3. **Reload integration:**
   - Configuration → Integrations → Ubisys
   - Click ⋮ → Reload

## Device Communication Issues

### Device Unavailable

**Symptoms:**
- Entity shows "unavailable" state
- Commands have no effect

**Diagnostic Steps:**

Check ZHA device status:
- Configuration → Integrations → ZHA → Devices
- Find your J1
- Check "Last seen" timestamp
- Check LQI (Link Quality Indicator)

**Solutions:**

1. **Check power supply:**
   - Verify device is powered
   - Check wiring connections
   - Measure voltage if possible

2. **Improve Zigbee signal:**
   - Move coordinator closer
   - Add Zigbee router devices
   - Remove sources of interference (WiFi, Bluetooth, USB 3.0)

3. **Re-interview device:**
   - ZHA → Devices → Your J1
   - Click ⋮ → Reconfigure device

4. **Check Zigbee network health:**
   ```bash
   # View ZHA logs
   grep -i "zigbee" ~/.homeassistant/home-assistant.log | tail -50
   ```

### Commands Delayed or Ignored

**Symptoms:**
- Commands take several seconds to execute
- Some commands don't execute
- Intermittent response

**Causes:**
- Poor Zigbee signal
- Network congestion
- Coordinator overloaded

**Solutions:**

1. **Check LQI value:**
   - Should be > 100 for reliable operation
   - < 50 indicates poor signal

2. **Add Zigbee routers:**
   - Place powered Zigbee devices between coordinator and J1
   - Many smart plugs act as routers

3. **Reduce Zigbee network traffic:**
   - Limit polling of Zigbee devices
   - Stagger automation timing
   - Use Zigbee groups for multiple devices

4. **Update coordinator firmware:**
   - Check for firmware updates
   - Backup network before updating

## Calibration Issues

### Calibration Service Not Found

**Symptoms:**
- Error: "Service ubisys.calibrate does not exist"

**Solutions:**

1. **Verify integration is loaded:**
   ```bash
   grep "ubisys" ~/.homeassistant/home-assistant.log
   ```

2. **Check services.yaml:**
   ```bash
   cat ~/.homeassistant/custom_components/ubisys/services.yaml
   ```

3. **Reload integration:**
   - Configuration → Integrations → Ubisys → ⋮ → Reload

### Calibration Fails to Start

**Symptoms:**
- No movement when calling calibration
- Error notification immediately

**Diagnostic Steps:**
```bash
# Check python_script logs
grep -i "ubisys_j1_calibrate" ~/.homeassistant/home-assistant.log

# Test python_script component
# Go to Developer Tools → Services
# Try: python_script.reload
```

**Solutions:**

1. **Enable python_script:**
   ```yaml
   # configuration.yaml
   python_script:
   ```

2. **Check script syntax:**
   ```bash
   python3 -m py_compile ~/.homeassistant/python_scripts/ubisys_j1_calibrate.py
   ```

3. **Verify entity ID:**
   - Developer Tools → States
   - Copy exact entity_id
   - Use in calibration call

### Calibration Times Out

**Symptoms:**
- Shade starts moving but calibration fails
- Timeout error after 60 seconds

**Causes:**
- Shade obstructed
- Motor stalling
- Communication issues

**Solutions:**

1. **Remove obstructions:**
   - Check shade path is clear
   - Verify mounting is correct

2. **Test manual movement:**
   - Try open/close via ZHA entity
   - If manual fails, issue is mechanical

3. **Increase timeout (advanced):**
   - Edit calibration script
   - Increase timeout in for loops (line ~180, ~205)

### Position Inaccurate After Calibration

**Symptoms:**
- Calibration completes successfully
- But positions don't match commands (e.g., 50% not halfway)

**Solutions:**

1. **Verify calibration values:**
   - Check notification for total_steps
   - Should be in reasonable range (2000-10000 typically)

2. **Check for mechanical slippage:**
   - Verify fabric doesn't slip on roller
   - Check motor coupling is secure

3. **Recalibrate from known position:**
   - Manually move to fully open
   - Run calibration again

4. **Test position consistency:**
   ```yaml
   # Test position accuracy
   - Open to 100%
   - Set to 50%
   - Check physical position
   - Set to 0%
   - Set to 50% again
   - Should match previous 50% position
   ```

## Position Control Issues

### Position Commands Don't Work

**Symptoms:**
- Open/close works
- Set position has no effect

**Solutions:**

1. **Verify shade type supports position:**
   - All types should support position
   - Check configuration

2. **Check calibration:**
   - Position control requires calibration
   - Run `ubisys.calibrate`

3. **Verify supported features:**
   - Developer Tools → States
   - Find your entity
   - Check `supported_features` attribute
   - Should include bit for SET_POSITION (4)

### Wrong Shade Type Selected

**Symptoms:**
- Expected features not available
- Wrong controls showing

**Solutions:**

1. **Reconfigure integration:**
   - Configuration → Integrations
   - Find Ubisys entry
   - Click "Configure"
   - Select correct shade type

2. **Reload integration:**
   - After reconfiguring, reload integration

3. **Recalibrate:**
   - Run calibration with new shade type

## Tilt Control Issues

### Tilt Controls Not Showing

**Symptoms:**
- Have venetian blinds
- Only see position controls, no tilt

**Solutions:**

1. **Verify shade type:**
   - Must be "venetian" or "exterior_venetian"
   - Configuration → Integrations → Ubisys → Configure

2. **Check supported features:**
   ```yaml
   # Developer Tools → States → your entity
   # Venetian should have:
   supported_features: 255  # All features
   ```

3. **Reconfigure with correct type:**
   - Change to venetian
   - Restart integration
   - Recalibrate

### Tilt Commands Have No Effect

**Symptoms:**
- Tilt controls appear
- Commands don't move slats

**Solutions:**

1. **Verify mechanical tilt connection:**
   - Check tilt mechanism is connected
   - Some J1 installations may be lift-only

2. **Run calibration:**
   - Venetian calibration includes tilt setup
   - Check tilt_steps in notification

3. **Test via ZHA:**
   - Try tilt via ZHA entity directly
   - If ZHA works but Ubisys doesn't, file bug report

## Logging and Debugging

### Enable Debug Logging

Add to `configuration.yaml`:

```yaml
logger:
  default: info
  logs:
    custom_components.ubisys: debug
    homeassistant.components.zha: debug
    zigpy: debug
```

Restart Home Assistant.

### View Logs

```bash
# Follow logs in real-time
tail -f ~/.homeassistant/home-assistant.log | grep -i ubisys

# Search for errors
grep -i "error" ~/.homeassistant/home-assistant.log | grep -i ubisys

# View last 100 ubisys entries
grep -i ubisys ~/.homeassistant/home-assistant.log | tail -100
```

### Check Entity State

Developer Tools → States:
- Find your entity
- Check all attributes
- Verify state updates

### Test Services Directly

Developer Tools → Services:

```yaml
# Test basic open
service: cover.open_cover
target:
  entity_id: cover.bedroom_shade

# Test position
service: cover.set_cover_position
target:
  entity_id: cover.bedroom_shade
data:
  position: 50

# Test calibration
service: ubisys.calibrate
data:
  entity_id: cover.bedroom_shade
```

### Collect Diagnostic Info

When reporting issues, include:

1. **Home Assistant version:**
   ```bash
   ha core info
   ```

2. **Integration version:**
   ```bash
   cat ~/.homeassistant/custom_components/ubisys/manifest.json | grep version
   ```

3. **ZHA info:**
   - Configuration → Integrations → ZHA → Configure
   - Screenshot Zigbee network topology

4. **Device signature:**
   - ZHA → Devices → Your J1
   - Copy "Signature" section

5. **Relevant logs:**
   ```bash
   grep -i ubisys ~/.homeassistant/home-assistant.log > ubisys_logs.txt
   ```

6. **Configuration:**
   ```yaml
   # Sanitize any sensitive info
   # Include relevant parts of configuration.yaml
   ```

## Common Error Messages

### "Entity not found"

**Meaning:** The specified entity_id doesn't exist

**Fix:** Verify entity_id in Developer Tools → States

### "Service not found"

**Meaning:** The integration or service isn't loaded

**Fix:** Reload integration or restart Home Assistant

### "Timeout waiting for position"

**Meaning:** Shade didn't reach expected position in time

**Fix:** Check for obstructions, mechanical issues

### "Failed to read attribute"

**Meaning:** Couldn't communicate with device

**Fix:** Check Zigbee connection, device power

### "ZHA gateway not found"

**Meaning:** ZHA integration not loaded or running

**Fix:** Verify ZHA integration is set up and running

## Getting Help

If you've tried these troubleshooting steps and still have issues:

1. **Check existing issues:**
   - https://github.com/jihlenburg/homeassistant-ubisys/issues

2. **Create new issue with:**
   - Clear description of problem
   - Steps to reproduce
   - Diagnostic info (see above)
   - Relevant logs
   - Screenshots if applicable

3. **Community support:**
   - Home Assistant Community Forum
   - Tag post with "ubisys" and "zha"

4. **Emergency workaround:**
   - Use ZHA entity directly
   - Bypass Ubisys integration temporarily
   - File issue for permanent fix

## J1 Cover Unavailable Issues


This guide helps you diagnose and fix issues where your J1 cover entity shows as "Unavailable" in Home Assistant.

## Understanding the Two-Entity Architecture

When you configure a J1 device in Ubisys, you get **TWO** cover entities:

| Entity | Platform | Visible | Enabled | Purpose |
|--------|----------|---------|---------|---------|
| `cover.ubisys_j1_5502` | ZHA | ❌ Hidden | ✅ Enabled | Internal state source |
| `cover.jalousie_none` | Ubisys | ✅ Visible | ✅ Enabled | User-facing entity |

**Why two entities?**

- **ZHA entity**: Handles Zigbee communication and maintains device state
- **Ubisys entity**: Filters features based on shade type and provides user interface

You should only see **one** entity in the UI (the Ubisys wrapper). The ZHA entity works in the background but remains hidden.

## How It Works (Quick Overview)

```
User clicks "Open" in UI
    ↓
Ubisys wrapper entity receives command
    ↓
Checks supported_features (filtered by shade type)
    ↓
Delegates command to ZHA entity
    ↓
ZHA entity sends Zigbee command to device
    ↓
Device executes movement
    ↓
ZHA entity receives state update from device
    ↓
Ubisys wrapper syncs state from ZHA entity
    ↓
User sees updated position in UI
```

**Key points:**
- Ubisys wrapper **never talks to Zigbee directly**
- All communication goes through ZHA entity
- Wrapper only filters features and provides UI

## Auto-Recovery Features (v1.3.0+)

The Ubisys integration includes two automatic recovery features:

### 1. Graceful Degradation (v1.3.0)

**Problem:** During Home Assistant startup, integrations load in parallel. Ubisys might load before ZHA has created its cover entity.

**Solution:** The wrapper entity:
1. Predicts the ZHA entity ID if not found yet
2. Creates itself anyway (shows in UI)
3. Marks itself as "Unavailable" with clear reason
4. Listens for state changes
5. **Automatically becomes available** when ZHA entity appears

**User experience:**
- Wrapper entity always shows in UI (never missing)
- Shows as "Unavailable" with reason: "ZHA entity not found or unavailable"
- Automatically recovers when ready (no reload needed)

### 2. Auto-Enable Logic (v1.3.1)

**Problem:** When the Ubisys integration creates its wrapper entity, ZHA detects this and automatically **disables** its own cover entity to prevent duplicate UI elements. However, the Ubisys wrapper **depends** on the ZHA entity having a state to delegate to.

This created a chicken-and-egg problem:
- Wrapper exists → ZHA disables its entity
- ZHA entity disabled → Has no state
- Wrapper has no state to sync from → Shows as "Unavailable"

**Solution:** Starting in v1.3.1, the Ubisys integration **automatically re-enables** the ZHA entity during setup, but keeps it **hidden**. This creates:

- **ZHA entity**: `hidden=true` + `enabled=true` = "internal state source"
- **Wrapper entity**: `visible=true` + `enabled=true` = "user-facing entity"

**Result:** Users see ONE entity in the UI (the wrapper), while the ZHA entity provides state in the background.

### Respecting User Intent

The auto-enable logic **only** enables if the entity was disabled by the integration:

| Scenario | Action | Reason |
|----------|--------|--------|
| Disabled by integration | ✅ Auto-enable | ZHA auto-disabled to prevent duplicates |
| Disabled by user | ❌ Leave disabled | Respect user's explicit choice |
| Already enabled | ✅ No action | Already in desired state |

**Logs you'll see:**

```
INFO: Enabling ZHA entity cover.ubisys_j1_5502 (disabled by integration).
      Entity remains hidden; wrapper provides user interface.
```

or if user disabled it:

```
INFO: ZHA entity cover.ubisys_j1_5502 is disabled by user (not enabling).
      Wrapper will be unavailable until ZHA entity is manually enabled.
```

## Troubleshooting Steps

### Wrapper Shows as "Unavailable"

**Possible causes:**

#### 1. ZHA entity disabled by user

**Check:**
1. Go to Settings → Devices & Services → Entities
2. Search for "ubisys_j1"
3. Find the ZHA cover entity (will show as disabled)

**Fix:**
1. Enable it manually
2. Wrapper will become available automatically

#### 2. Device not paired with ZHA

**Check:**
1. Go to Settings → Devices & Services → ZHA
2. Verify device is listed

**Fix:**
1. If not listed, pair device with ZHA first
2. Then configure Ubisys integration

#### 3. Startup timing issue (rare after v1.3.0)

**Check:**
- Wait 30-60 seconds for all integrations to finish loading

**Fix:**
- Wrapper should auto-recover
- If not, reload Ubisys integration:
  1. Settings → Devices & Services → Ubisys
  2. Click three dots (⋮) → Reload

#### 4. ZHA entity deleted

**Check:**
- Go to Settings → Devices & Services → Entities
- Search for `cover.ubisys_j1_*`

**Fix:**
1. If missing, remove and re-add device in ZHA
2. Reconfigure Ubisys integration

### Wrapper Exists But No Controls Showing

**Cause:** Wrapper is disabled or hidden in Home Assistant

**Fix:**
1. Settings → Devices & Services → Entities
2. Search for "jalousie" or your device name
3. Find the Ubisys cover entity
4. Enable it if disabled
5. Unhide it if hidden

### Commands Not Working

**Cause:** ZHA entity is unavailable or offline

**Fix:**
1. Check if ZHA device is online (Settings → Devices & Services → ZHA)
2. Verify Zigbee coordinator is working
3. Check device battery/power
4. Try reloading ZHA integration

## Quick Fix Checklist

When wrapper shows as unavailable, try these steps in order:

1. ✅ **Wait 60 seconds** - Auto-recovery might be in progress
2. ✅ **Check ZHA entity status** - Ensure it's enabled (not by user)
3. ✅ **Reload Ubisys integration** - This re-runs the auto-enable logic
4. ✅ **Check ZHA device** - Ensure device is paired and online
5. ✅ **Check logs** - Look for specific error messages

## Understanding Entity States

| State | Meaning | Has State | Shows in UI | Can Be Controlled |
|-------|---------|-----------|-------------|-------------------|
| Visible + Enabled | Normal entity | ✅ | ✅ | ✅ |
| Hidden + Enabled | Internal use | ✅ | ❌ | ✅ (via code) |
| Visible + Disabled | User disabled | ❌ | ✅ (as disabled) | ❌ |
| Hidden + Disabled | Integration disabled | ❌ | ❌ | ❌ |

**Our pattern:** ZHA entity is **Hidden + Enabled** = invisible to users but provides state for wrapper.

## Version History

### v1.3.1 (Current)
- ✅ Auto-enables ZHA entity if disabled by integration
- ✅ Respects user's choice if manually disabled
- ✅ Comprehensive logging for troubleshooting
- ✅ Idempotent and safe for multiple reloads

### v1.3.0
- ✅ Graceful degradation for startup race conditions
- ✅ Automatic recovery when ZHA entity appears
- ✅ Clear unavailability reasons
- ⚠️ Issue: ZHA entity auto-disabled causing wrapper unavailable (fixed in v1.3.1)

### v1.2.x and earlier
- ⚠️ Hard failure if ZHA entity not found
- ⚠️ No automatic recovery
- ⚠️ Required manual intervention

## See Also

- [J1 Calibration Guide](devices/j1_window_covering.md)
- [Migration Guide](migration_v2.0.md)
- [Main Troubleshooting Guide](troubleshooting.md)
- [Window Covering Architecture](window_covering_architecture.md) (Developer reference)


## Device Discovery Issues


If ZHA shows your Ubisys device but the Ubisys integration doesn't auto-discover it, follow these steps:

## Step 1: Verify Integration is Loaded

1. Go to **Settings** → **Devices & Services** → **Integrations**
2. Look for "Ubisys Zigbee Devices" in the list
3. If NOT present, the integration isn't installed correctly

**If missing:**
- Check that files are in `config/custom_components/ubisys/`
- Restart Home Assistant
- Check logs for errors: `grep -i ubisys home-assistant.log`

## Step 2: Check Device Model Name

The integration looks for exact model names. Check what ZHA sees:

1. Go to **Settings** → **Devices & Services** → **ZHA**
2. Click on your Ubisys device
3. Look at the **Model** field
4. It should be one of: `J1`, `J1-R`, `D1`, `D1-R`, `S1`, `S1-R`

**Common Issues:**
- Model has extra text: e.g., "J1 (Router)" → Integration strips "(Router)" automatically
- Model is blank or different → Device might not be recognized by ZHA quirk

## Step 3: Enable Debug Logging

Add to `configuration.yaml`:

```yaml
logger:
  default: info
  logs:
    custom_components.ubisys: debug
    homeassistant.components.zha: debug
```

Restart Home Assistant and check logs:

```bash
grep -i "ubisys" home-assistant.log | tail -50
```

Look for:
- `Scanning device registry for Ubisys devices...`
- `Found Ubisys device: ubisys J1 (IEEE: ...)`
- `Auto-discovering Ubisys device: ubisys J1`
- `Device discovery complete: X Ubisys devices found, Y already configured, Z new config flows triggered`

## Step 4: Manual Discovery Trigger

If auto-discovery doesn't work, manually trigger discovery:

### Option A: Restart Home Assistant
Discovery runs on every startup, so a restart should trigger it.

### Option B: Developer Tools Service Call

1. Go to **Developer Tools** → **Services**
2. Call this service (requires custom script):

```yaml
service: python_script.trigger_ubisys_discovery
```

### Option C: Manual Configuration

If auto-discovery fails, you can manually add via UI:

1. **Settings** → **Devices & Services** → **Add Integration**
2. Search for "Ubisys"
3. Select your device from the dropdown
4. Configure shade type (for J1) or other settings
5. Click **Submit**

## Step 5: Check for Config Flow

Even if auto-discovery triggers, the config flow might be waiting:

1. Go to **Settings** → **Devices & Services**
2. Look for a notification badge or "Discovered" section
3. Click **Configure** on any pending Ubisys discovery

## Common Issues

### Issue: "Found unsupported Ubisys device"

**Symptom:** Logs show `Found unsupported Ubisys device: XYZ`

**Cause:** Device model not in `SUPPORTED_MODELS` list

**Fix:**
- Check if you have an S2/S2-R (not yet supported)
- File an issue with your device model

### Issue: "Device already configured"

**Symptom:** Logs show `Device XXX already configured`

**Cause:** Config entry already exists for this device

**Fix:**
- Check **Settings** → **Devices & Services** for existing Ubisys entry
- If duplicate, remove one and restart

### Issue: No logs at all

**Symptom:** No "Scanning device registry" messages in logs

**Cause:** Integration not loading or discovery not running

**Fix:**
1. Check integration files are in correct location
2. Check `manifest.json` has correct domain: "ubisys"
3. Restart Home Assistant
4. Check for Python errors in logs

### Issue: ZHA Quirk Not Loading

**Symptom:** Device attributes (calibration, phase mode) not available

**Cause:** Custom ZHA quirk not loaded

**Fix:**
1. Check files in `config/custom_zha_quirks/`
2. Verify `configuration.yaml` has:
   ```yaml
   zha:
     custom_quirks_path: custom_zha_quirks
   ```
3. Restart Home Assistant
4. Check ZHA device signature shows custom clusters

## Getting Help

If none of the above works, collect this information:

1. Home Assistant version
2. ZHA version
3. Device model from ZHA device page
4. Logs with debug enabled (last 100 lines):
   ```bash
   grep -i "ubisys" home-assistant.log | tail -100
   ```
5. Integration version from `manifest.json`

Post this information to:
- GitHub Issues: https://github.com/jihlenburg/homeassistant-ubisys/issues
- Home Assistant Community: https://community.home-assistant.io/


## Frequently Asked Questions

## Do I need to run calibration for J1?
Yes. After installation or changing shade type, run calibration to measure `total_steps` for accurate position control.
## My J1 does not expose tilt controls.
Check your shade type. Tilt is available for venetian/exterior venetian. Change via Options → Configure and re‑calibrate.
## Which D1 phase mode should I use for LEDs?
Try `reverse` (trailing edge) first; if buzzing or instability persists, test `forward` or `automatic`.
## I don’t see input events in the log.
Enable “Verbose input event logging” in Options, or set `logger:` to DEBUG for `custom_components.ubisys`.
## The integration can’t find the WindowCovering cluster.
The integration probes EP1 then EP2. If neither is found, a Repairs issue is created. Ensure the device is properly paired and quirks are enabled.
## How do I test locally without hardware?
Use `make ci` to run tests with mocked ZHA/zigpy via `pytest-homeassistant-custom-component`.
## Will my data be exposed in diagnostics?
Diagnostics payloads are redacted (IEEE removed). See docs/security_privacy.md for details.

## Known Issues & Limitations

---
## 🚧 Device Support Gaps
###  S1/S1-R Power Switch
| Component | Status | Notes |
|-----------|--------|-------|
| Platform Wrapper | ✅ Implemented | Basic switch functionality |
| Input Configuration | ✅ Implemented | Options Flow presets |
| ZHA Quirk | ✅ Implemented | DeviceSetup cluster |
| Power Metering | ⚠️ Via ZHA | Standard sensors (no wrapper needed) |
| Advanced Features | 🔄 Evolving | Quirks and platform still being refined |
**Current limitations:**
- Input configuration presets are basic
- Advanced power metering features not fully exposed
- Needs more real-hardware testing
### S2/S2-R Dual Power Switch
| Status | ❌ Not Implemented |
|--------|-------------------|
**Required work:**
- Add `S2`, `S2-R` to `SWITCH_MODELS` constant
- Create platform support for dual endpoints
- Implement ZHA quirk with proper endpoint mapping
- Test with real hardware
**Blocker:** No S2 hardware available for testing
---
## 🔬 Hardware Validation Needed
The following features exist but **require real hardware testing** for validation:
### D1 Input Configuration
**Status:** ⚠️ Not Implemented
**Reason:** Requires understanding DeviceSetup cluster format with real hardware
**Workaround:** Default input configuration works for most users
**Status:** Phase 3 feature blocked pending hardware access
### D1 Phase Mode Configuration
**Status:** ⚠️ Implemented, needs validation
**Service:** `ubisys.configure_d1_phase_mode`
**Validation needed:**
- Behavior with different LED types
- Behavior with incandescent loads
- Behavior with halogen loads
- Phase mode persistence across power cycles
### J1 Calibration
**Status:** ✅ Mostly validated
**Known issues:**
- Very large shades (>3m) may timeout
- Needs testing across more shade types
- Edge cases with unusual motor behavior
---
## 📋 Planned Features (Roadmap)
See also: [Roadmap](roadmap.md)
<details>
<summary><strong>Input Monitoring Enhancements</strong></summary>
**Event Entities** (Phase 4)
- Show last button press in dashboard
- Display press history
- Timestamp of last event
**Binary Sensors** (Phase 5)
- For stationary rocker switches
- Show current state (on/off)
- Track state history
**Scene-Only Mode** (Phase 6)
- Buttons trigger automations only
- Disable local device control
- Useful for scene controllers
</details>
<details>
<summary><strong>J1 Window Covering Enhancements</strong></summary>
**Scene Support**
- Save preset positions
- Recall specific positions
- Name preset scenes
**Position Offset Configuration**
- Adjust reporting to match physical reality
- Useful when limits don't align with 0%/100%
**Speed Control**
- Configure motor speed
- Slow/medium/fast presets
**Web-Based Calibration Wizard**
- Interactive step-by-step guide
- Visual feedback during calibration
- Diagnostics and troubleshooting
</details>
<details>
<summary><strong>Energy Monitoring</strong></summary>
**Energy Dashboard Integration**
- Leverage S1/D1 0.5% accuracy power monitoring
- Energy metering dashboard
- Historical usage tracking
- Cost calculations
**Status:** Depends on S1 platform completion
</details>
<details>
<summary><strong>Developer Experience</strong></summary>
**Test Coverage** (Current: ~58%)
- Unit test suite expansion
- Integration test suite
- End-to-end testing framework
- Target: 80%+ coverage
**Documentation**
- Manual testing procedures (`docs/testing.md`)
- Contributor guidelines enhancement
- Architecture deep-dives
</details>
<details>
<summary><strong>Localization</strong></summary>
**Multi-Language Support**
- Currently: English, German, French, Spanish (partial)
- Target: Complete translations for all languages
- Community contributions welcome
</details>
---
## 📝 Documentation Gaps
### Missing Guides
- **S2/S2-R Configuration** - Blocked until device support implemented
- **Manual Testing Procedures** - No structured checklist for contributors
- **Translation Guide** - How to add new languages
### Incomplete Documentation
- **S1 Advanced Features** - Power metering integration with Energy dashboard
- **Performance Tuning** - Optimizing for large installations
- **Network Troubleshooting** - Zigbee mesh optimization
---
## 💡 Architectural Notes
### J1 Unused Attributes
Technical reference documents these manufacturer attributes:
- `0x1003` (LiftToTiltTransitionSteps2)
- `0x1004` (TotalSteps2)
**Status:** Not currently used by integration
**Reason:** Existing calibration approach works well without them
**Future:** May be useful for advanced scenarios
### Button→Service Pattern
Calibration button delegates to service for flexibility:
- ✅ UI access via button
- ✅ Automation access via service
- ✅ Single implementation (DRY)
**Tradeoff:** Slightly more complex than direct button action
### Wrapper Entity Architecture
Entities delegate to ZHA rather than talking directly to Zigbee:
- ✅ Leverages ZHA's excellent communication layer
- ✅ No need to reimplement Zigbee protocol
- ✅ Easier maintenance
**Tradeoff:** Dependency on ZHA entity existence
---
## 🔧 How You Can Help
### High Priority Contributions
<details>
<summary><strong>Hardware Testing</strong></summary>
**D1/D1-R Validation:**
- Test phase mode with various load types
- Validate ballast configuration
- Document LED compatibility
**J1 Calibration:**
- Test with more shade types
- Validate on large shades (>2m)
- Edge case discovery
**S1/S1-R:**
- Test input configuration presets
- Validate power metering accuracy
- Document real-world usage
</details>
<details>
<summary><strong>S2 Implementation</strong></summary>
**Requirements:**
- Access to S2 or S2-R hardware
- Python development experience
- Understanding of ZHA quirks
**Tasks:**
1. Add model constants
2. Implement dual-endpoint platform
3. Create ZHA quirk
4. Write tests
5. Document usage
</details>
<details>
<summary><strong>Test Suite Expansion</strong></summary>
**Current coverage:** ~58%
**Target:** 80%+
**Focus areas:**
- Input monitoring correlation
- Diagnostics content validation
- Calibration flow testing
- Config flow edge cases
</details>
<details>
<summary><strong>Documentation</strong></summary>
**Needed:**
- Translation to additional languages
- More automation examples
- Troubleshooting guides
- Video tutorials
</details>
---
## 📞 Reporting Issues
### Before Reporting
1. Check [Existing Issues](https://github.com/jihlenburg/homeassistant-ubisys/issues)
2. Review [Troubleshooting Guide](troubleshooting.md)
3. Enable debug logging
4. Gather diagnostics
### Issue Template
```markdown
**Home Assistant Version:** 2025.x.x
**Integration Version:** x.y.z
**Device Model:** J1 / D1 / S1 / etc.
**Expected Behavior:**
[What you expected to happen]
**Actual Behavior:**
[What actually happened]
**Steps to Reproduce:**
1. ...
2. ...
**Logs:**
```
[Paste relevant logs here]
```
**Diagnostics:**
[Attach diagnostics file if applicable]
```
### Where to Report
- **Bugs:** [GitHub Issues](https://github.com/jihlenburg/homeassistant-ubisys/issues)
- **Feature Requests:** [GitHub Discussions](https://github.com/jihlenburg/homeassistant-ubisys/discussions)
- **Questions:** [Home Assistant Forum](https://community.home-assistant.io/)
---
##  🔗 Related Documentation
- [Roadmap](roadmap.md) - Detailed future plans
- [User Guide](user_guide.md) - Complete integration documentation
- [Contributing Guide](../CONTRIBUTING.md) - Developer documentation

## Repairs



If expected clusters are not found (e.g., WindowCovering or DeviceSetup), the integration raises a Home Assistant Repairs issue to guide recovery steps (ensure ZHA is loaded, device is paired, quirks enabled). Open Settings → Repairs for details and remediation.
