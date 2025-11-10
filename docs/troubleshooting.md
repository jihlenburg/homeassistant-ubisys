# Troubleshooting Guide

This guide helps you diagnose and fix common issues with the Ubisys Home Assistant integration.

## Table of Contents

- [Installation Issues](#installation-issues)
- [Integration Setup Issues](#integration-setup-issues)
- [Device Communication Issues](#device-communication-issues)
- [Calibration Issues](#calibration-issues)
- [Position Control Issues](#position-control-issues)
- [Tilt Control Issues](#tilt-control-issues)
- [Logging and Debugging](#logging-and-debugging)

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
