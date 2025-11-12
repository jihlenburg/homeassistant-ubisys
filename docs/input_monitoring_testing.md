# Input Monitoring Testing Guide

This guide describes how to test the input monitoring implementation (Phase 2) with real Ubisys hardware.

## Prerequisites

- Home Assistant with ZHA integration running
- Ubisys integration installed (v2.0+)
- At least one Ubisys device paired with ZHA:
  - J1/J1-R (Window covering controller)
  - D1/D1-R (Universal dimmer)
  - S1/S1-R (Power switch)
- Physical access to the device's input buttons/switches

## Phase 2 Testing: InputActions Reading & Correlation

### Test 1: Verify Input Monitor Startup

**Goal:** Confirm that input monitoring starts successfully for all devices.

**Steps:**
1. Enable debug logging in `configuration.yaml`:
   ```yaml
   logger:
     logs:
       custom_components.ubisys.input_monitor: debug
       custom_components.ubisys.input_parser: debug
   ```

2. Restart Home Assistant

3. Check logs for startup messages:
   ```
   Started input monitoring for J1 (00:12:4b:00:1c:a1:b2:c3)
   Reading InputActions from 00:12:4b:00:1c:a1:b2:c3 (J1)
   Read X bytes of InputActions data from 00:12:4b:00:1c:a1:b2:c3
   Registered N InputActions for J1 (00:12:4b:00:1c:a1:b2:c3)
   ```

**Expected Result:**
- Input monitor starts for each Ubisys device
- InputActions successfully read from DeviceSetup cluster
- Actions parsed and registered (count matches device configuration)

**Troubleshooting:**
- If "DeviceSetup cluster not found": Check device is properly paired with ZHA
- If "Failed to read InputActions": Check manufacturer code injection
- If "Invalid array type": Check ZigBee quirk is loaded

### Test 2: Verify InputActions Parsing

**Goal:** Confirm that InputActions micro-code is correctly parsed.

**Steps:**
1. With debug logging enabled, examine logs for each device
2. Look for detailed InputActions breakdown:
   ```
   Input 0 (short_press) → ep2 cluster=0x0102 cmd=0x00
   Input 0 (released) → ep2 cluster=0x0102 cmd=0x02
   Input 1 (short_press) → ep2 cluster=0x0102 cmd=0x01
   Input 1 (released) → ep2 cluster=0x0102 cmd=0x02
   ```

**Expected Result for Each Device:**

**J1 (Default Configuration - Momentary Switches):**
- Input 0: up_open (0x00), stop (0x02)
- Input 1: down_close (0x01), stop (0x02)
- Press types: `short_press`, `long_press`, `released`

**D1 (Default Configuration - Single Push-Button):**
- Input 0: toggle (0x02 on OnOff), move up/down (LevelControl)
- Input 1: toggle (0x02 on OnOff), move up/down (LevelControl)
- Press types: `short_press`, `long_press`

**S1 (Default Configuration - Rocker Switch):**
- Input 0: toggle on press and release
- Press types: `short_press`, `released`

**S1-R (Default Configuration - Two Push-Buttons):**
- Input 0: toggle on press
- Input 1: toggle on press
- Press types: `short_press`

**Troubleshooting:**
- If parsing fails with "Invalid array type": Check micro-code format
- If wrong input number: Check InputAndOptions byte parsing
- If wrong press type: Check Transition byte parsing

### Test 3: Verify ZHA Event Subscription

**Goal:** Confirm that input monitor subscribes to ZHA events.

**Steps:**
1. Check logs for subscription confirmation:
   ```
   Subscribed to zha_event for 00:12:4b:00:1c:a1:b2:c3 (endpoints [2])
   ```

2. Use Developer Tools → Events → Listen to Event
3. Event type: `zha_event`
4. Press a physical button on the device

**Expected Result:**
- `zha_event` fires with:
  - `device_ieee`: matches your device
  - `endpoint_id`: 2 or 3 (controller endpoint)
  - `cluster_id`: 0x0102 (J1), 0x0006/0x0008 (D1), 0x0006 (S1)
  - `command`: command ID (0x00, 0x01, 0x02, etc.)

**Troubleshooting:**
- If no `zha_event` fires: Check ZHA integration is properly configured
- If wrong endpoint: Check device signature in ZHA
- If command data missing: Check ZHA quirk implementation

### Test 4: Verify Command Correlation

**Goal:** Confirm that observed commands are correlated with InputActions.

**Steps:**
1. Press button 1 on the device (short press)
2. Check logs for correlation:
   ```
   ZHA event from J1 ep2: cluster=0x0102, cmd=0x00, args=[]
   Matched command (ep=2, cluster=0x0102, cmd=0x00) → input 0 (short_press)
   J1 input 1: short_press
   ```

3. Release button 1
4. Check logs for release correlation:
   ```
   Matched command (ep=2, cluster=0x0102, cmd=0x02) → input 0 (released)
   J1 input 1: released
   ```

**Expected Result:**
- Commands correctly correlated to input number (0 or 1)
- Press type correctly identified (short_press, long_press, released)
- Input number displayed as 1-based for user readability in logs

**Troubleshooting:**
- If "No match for command": Check InputActions correlation mapping
- If wrong input number: Check InputAndOptions parsing
- If wrong press type: Check Transition state parsing

### Test 5: Verify Event Firing

**Goal:** Confirm that Home Assistant events are fired correctly.

**Steps:**
1. Use Developer Tools → Events → Listen to Event
2. Event type: `ubisys_input_event`
3. Press button 1 on the device

**Expected Event Data:**
```yaml
event_type: ubisys_input_event
data:
  device_ieee: "00:12:4b:00:1c:a1:b2:c3"
  device_id: "abc123def456"
  model: "J1"
  input_number: 0
  press_type: "short_press"
  command:
    endpoint: 2
    cluster: 258  # 0x0102
    command: 0
```

**Expected Result:**
- Event fires within ~100ms of button press
- `input_number` is correct (0-based)
- `press_type` matches action (short_press, long_press, etc.)
- `device_id` matches Home Assistant device registry
- `command` includes raw ZigBee command details

**Troubleshooting:**
- If event doesn't fire: Check ZHA event subscription
- If wrong input_number: Check command correlation
- If wrong press_type: Check InputActions parsing

### Test 6: Test All Input Types

**Goal:** Verify all press types work correctly.

**For Each Device:**

**J1:**
1. Short press button 1 → expect `short_press` + `released`
2. Long press button 1 (>1s) → expect `long_press` + `released`
3. Short press button 2 → expect `short_press` + `released`
4. Long press button 2 → expect `long_press` + `released`

**D1:**
1. Short press button 1 → expect `short_press` (toggle)
2. Long press button 1 → expect `long_press` (dim up/down)
3. Same for button 2

**S1:**
1. Toggle switch → expect `short_press` + `released`
2. Repeat toggle → expect events again

**S1-R:**
1. Press button 1 → expect `short_press`
2. Press button 2 → expect `short_press`

**Expected Result:**
- All press types detected correctly
- Input numbers match physical buttons (1-based in logs, 0-based in events)
- No missed events or false positives

### Test 7: Test Error Handling

**Goal:** Verify graceful degradation when errors occur.

**Test Cases:**

**Missing DeviceSetup Cluster:**
1. Temporarily rename quirk file to disable it
2. Restart HA
3. Check logs: "DeviceSetup cluster not found - input correlation disabled"
4. Events should still fire but with generic input numbers

**Invalid InputActions Data:**
1. If possible, corrupt InputActions via ZigBee tool
2. Check logs: "Failed to parse InputAction entry"
3. Monitor continues but correlation may be incomplete

**Device Offline:**
1. Power off device
2. Check logs: No crashes, graceful warnings
3. Power on device
4. Monitor should resume automatically

**Expected Result:**
- No crashes or exceptions
- Clear warning/error messages
- Graceful degradation (events fire without correlation if needed)
- Automatic recovery when device comes back online

## Success Criteria for Phase 2

- [ ] Input monitors start for all Ubisys devices (J1, D1, S1)
- [ ] InputActions successfully read and parsed for all devices
- [ ] ZHA events subscription works for all devices
- [ ] Command correlation accuracy >95% for all press types
- [ ] Events fire within 100ms of physical button press
- [ ] Correct input number and press type in events
- [ ] No crashes or exceptions during normal operation
- [ ] Graceful error handling when devices offline or errors occur

## Next Steps (Phase 3)

Once Phase 2 testing is complete and all success criteria are met:

1. **Implement device triggers** (`device_trigger.py`)
   - Define trigger types for each device model
   - Integrate with HA automation UI
   - Test trigger selection in automation builder

2. **Test automation workflows**
   - Create sample automations using device triggers
   - Verify triggers fire reliably
   - Test trigger conditions and actions

3. **User documentation**
   - Create user-facing documentation
   - Add examples and troubleshooting
   - Update README with input monitoring features

## Debugging Tips

### Enable Maximum Logging

```yaml
logger:
  default: info
  logs:
    custom_components.ubisys: debug
    custom_components.ubisys.input_monitor: debug
    custom_components.ubisys.input_parser: debug
    homeassistant.components.zha: debug
    zigpy: debug
```

### Useful Log Filters

```bash
# Show all input monitoring activity
grep "input_monitor" home-assistant.log

# Show InputActions parsing
grep "InputAction" home-assistant.log

# Show ZHA events from controller endpoints
grep "ZHA event from" home-assistant.log

# Show correlation matches
grep "Matched command" home-assistant.log

# Show events fired
grep "ubisys_input_event" home-assistant.log
```

### Developer Tools Commands

```yaml
# Listen for all Ubisys input events
# Developer Tools → Events → Listen to Event
# Event type: ubisys_input_event

# Check device registry
# Developer Tools → States → Filter: "device_registry"

# Check entity registry for Ubisys entities
# Developer Tools → States → Filter: "ubisys"
```

## Known Limitations

### Phase 2 Limitations:
- No GUI for viewing/configuring inputs (Phase 6)
- No device automation triggers yet (Phase 3)
- No event entities for dashboard visibility (Phase 4)
- No binary sensors for stationary switches (Phase 5)
- Events only accessible via Developer Tools or event triggers in automations

### Workaround for Automations:
Until Phase 3 (device triggers) is complete, create automations using event triggers:

```yaml
automation:
  - alias: "J1 Button 1 Pressed"
    trigger:
      - platform: event
        event_type: ubisys_input_event
        event_data:
          device_id: "YOUR_DEVICE_ID"  # Get from event data
          input_number: 0  # 0-based (0 = button 1)
          press_type: "short_press"
    action:
      - service: light.turn_on
        target:
          entity_id: light.living_room
```

## Reporting Issues

When reporting issues with input monitoring, include:

1. Home Assistant version
2. ZHA integration version
3. Ubisys integration version
4. Device model (J1, D1, S1, etc.)
5. Relevant logs (with debug enabled)
6. Steps to reproduce
7. Expected vs actual behavior

File issues at: https://github.com/YOUR_REPO/issues
