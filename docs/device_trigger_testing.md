# Device Trigger Testing Guide (Phase 3)

This guide describes how to test device automation triggers for Ubisys input events.

## Prerequisites

- Phase 2 complete and tested (input monitoring working)
- Home Assistant 2023.3+ (for device automation support)
- At least one Ubisys device configured
- Access to Home Assistant UI (Settings → Automations & Scenes)

## Overview

Device triggers expose physical button presses as automation triggers in the Home Assistant UI. Users can create automations by selecting:
1. Trigger type: **Device**
2. Device: **[Select Ubisys device]**
3. Trigger: **[Select button and press type]**

No need to understand event structures or write YAML!

## Phase 3 Testing: Device Triggers

### Test 1: Verify Triggers Appear in UI

**Goal:** Confirm that Ubisys devices show automation triggers in the UI.

**Steps:**
1. Navigate to Settings → Automations & Scenes
2. Click "+ CREATE AUTOMATION"
3. Click "Create new automation"
4. Click "+ ADD TRIGGER"
5. Select trigger type: "Device"
6. In the "Device" dropdown, find your Ubisys device

**Expected Result:**

**For J1 devices**, you should see 8 triggers:
- Button 1 pressed
- Button 1 released
- Button 1 short press
- Button 1 long press
- Button 2 pressed
- Button 2 released
- Button 2 short press
- Button 2 long press

**For D1 devices**, same 8 triggers as J1.

**For S1 devices**, you should see 4 triggers:
- Button 1 pressed
- Button 1 released
- Button 1 short press
- Button 1 long press

**For S1-R devices**, you should see 8 triggers (2 inputs).

**Troubleshooting:**
- If device doesn't appear: Check device is configured in Ubisys integration
- If no triggers shown: Check device_trigger.py is loaded
- If wrong trigger count: Check device model detection

### Test 2: Create Simple Test Automation

**Goal:** Create a working automation using device triggers.

**Steps:**
1. Create new automation (as above)
2. Add trigger: Device → [Your J1] → "Button 1 short press"
3. Add action: "Call service"
4. Service: `notify.persistent_notification`
5. Service data:
   ```yaml
   message: "J1 Button 1 was short pressed!"
   title: "Input Test"
   ```
6. Save automation as "Test J1 Button 1"
7. Press button 1 on your J1 device (short press)

**Expected Result:**
- Notification appears in Home Assistant within ~100ms
- Notification message: "J1 Button 1 was short pressed!"
- Automation runs successfully

**Troubleshooting:**
- If automation doesn't trigger: Check Phase 2 events are firing
- If wrong trigger fires: Check input number mapping
- If delayed trigger: Check system load

### Test 3: Test All Trigger Types

**Goal:** Verify each trigger type works correctly.

**For each device, test:**

**J1 (Window Covering):**
1. Button 1 short press → Create automation → Test
2. Button 1 long press (hold >1s) → Create automation → Test
3. Button 1 pressed (press and hold) → Create automation → Test
4. Button 1 released (after press) → Create automation → Test
5. Repeat for Button 2

**D1 (Dimmer):**
1. Button 1 short press (toggle) → Test
2. Button 1 long press (dim up/down) → Test
3. Same for Button 2

**S1 (Switch):**
1. Toggle switch → Button 1 short press fires
2. Toggle back → Button 1 short press fires again

**S1-R (Dual Switch):**
1. Press button 1 → Button 1 short press fires
2. Press button 2 → Button 2 short press fires

**Expected Result:**
- All trigger types work correctly
- No false positives (wrong trigger firing)
- No missed triggers
- Consistent timing (<100ms latency)

### Test 4: Test Trigger Context Variables

**Goal:** Verify trigger context provides useful information.

**Steps:**
1. Create automation with J1 Button 1 short press trigger
2. Add action: Call service `notify.persistent_notification`
3. Use template in message:
   ```yaml
   message: >
     Trigger: {{ trigger.type }}
     Input: {{ trigger.input_number }}
     Press: {{ trigger.press_type }}
     Description: {{ trigger.description }}
   ```
4. Save and test

**Expected Result:**
Notification shows:
```
Trigger: button_1_short_press
Input: 0
Press: short_press
Description: Button 1 short press
```

**Troubleshooting:**
- If variables missing: Check async_attach_trigger implementation
- If wrong values: Check PRESS_TYPE_TO_TRIGGER mapping

### Test 5: Test Multiple Automations

**Goal:** Verify multiple automations can use same device triggers.

**Steps:**
1. Create automation 1: J1 Button 1 short press → Turn on light
2. Create automation 2: J1 Button 1 short press → Send notification
3. Create automation 3: J1 Button 1 long press → Turn off light
4. Test each trigger

**Expected Result:**
- All automations fire correctly
- Multiple automations for same trigger all run
- No interference between automations
- Each automation receives trigger context

### Test 6: Test Automation Enable/Disable

**Goal:** Verify triggers respect automation state.

**Steps:**
1. Create automation: J1 Button 1 short press → Notification
2. Test (should work)
3. Disable automation via UI
4. Test trigger (should NOT work)
5. Enable automation
6. Test trigger (should work again)

**Expected Result:**
- Disabled automations don't trigger
- Enabling/disabling works immediately
- No lingering subscriptions

### Test 7: Test Trigger Conditions

**Goal:** Verify triggers work with conditions.

**Steps:**
1. Create automation: J1 Button 1 short press
2. Add condition: "Time" - Only after 10:00 AM
3. Test before 10:00 AM (should not run)
4. Test after 10:00 AM (should run)

**Expected Result:**
- Conditions properly evaluated
- Trigger fires but action doesn't run if condition fails
- Automation logs show condition evaluation

### Test 8: Test with Multiple Devices

**Goal:** Verify triggers work correctly with multiple Ubisys devices.

**Setup:** Pair multiple Ubisys devices (e.g., J1 + D1 + S1)

**Steps:**
1. Create automation for J1 Button 1
2. Create automation for D1 Button 1
3. Create automation for S1 Button 1
4. Test each device's button

**Expected Result:**
- Each device triggers only its own automation
- No cross-device triggering
- Device IDs correctly differentiate triggers

### Test 9: Test Automation Reload

**Goal:** Verify triggers survive automation reload.

**Steps:**
1. Create automation: J1 Button 1 → Notification
2. Test (should work)
3. Go to Settings → System → Restart → "Reload Automations"
4. Wait for reload to complete
5. Test trigger again

**Expected Result:**
- Trigger still works after reload
- No errors in logs
- Subscriptions re-established correctly

### Test 10: Test with Templates in Actions

**Goal:** Verify trigger variables work in templates.

**Steps:**
1. Create automation: J1 Button 1 short press
2. Add action: Turn on light with brightness template:
   ```yaml
   service: light.turn_on
   target:
     entity_id: light.living_room
   data:
     brightness: >
       {% if trigger.input_number == 0 %}255{% else %}128{% endif %}
   ```
3. Test

**Expected Result:**
- Template evaluates correctly
- Light turns on with correct brightness
- Trigger variables accessible in templates

## Success Criteria for Phase 3

- [ ] All Ubisys devices show triggers in automation UI
- [ ] Correct number of triggers for each device model
- [ ] Trigger names are user-friendly and descriptive
- [ ] All trigger types fire correctly (pressed, released, short, long)
- [ ] Trigger context variables provide complete information
- [ ] Multiple automations can use same trigger
- [ ] Automation enable/disable works correctly
- [ ] Conditions work with device triggers
- [ ] Multiple devices don't interfere with each other
- [ ] Triggers survive automation reload
- [ ] No errors or warnings in logs during normal operation

## Common Automation Examples

### Example 1: Turn on Lights with Short Press

```yaml
alias: "Bedroom Lights - J1 Button 1"
trigger:
  - platform: device
    domain: ubisys
    device_id: abc123def456
    type: button_1_short_press
action:
  - service: light.turn_on
    target:
      entity_id: light.bedroom
```

### Example 2: Toggle Lights with Any Button Press

```yaml
alias: "Living Room Toggle - D1 Any Button"
trigger:
  - platform: device
    domain: ubisys
    device_id: def456ghi789
    type: button_1_short_press
  - platform: device
    domain: ubisys
    device_id: def456ghi789
    type: button_2_short_press
action:
  - service: light.toggle
    target:
      entity_id: light.living_room
```

### Example 3: Scene Activation with Long Press

```yaml
alias: "Movie Mode - J1 Long Press"
trigger:
  - platform: device
    domain: ubisys
    device_id: abc123def456
    type: button_1_long_press
action:
  - service: scene.turn_on
    target:
      entity_id: scene.movie_mode
```

### Example 4: Conditional Action Based on Input

```yaml
alias: "Smart Dimming - D1 Buttons"
trigger:
  - platform: device
    domain: ubisys
    device_id: def456ghi789
    type: button_1_short_press
    id: button_1
  - platform: device
    domain: ubisys
    device_id: def456ghi789
    type: button_2_short_press
    id: button_2
action:
  - choose:
      - conditions:
          - condition: trigger
            id: button_1
        sequence:
          - service: light.turn_on
            target:
              entity_id: light.kitchen
            data:
              brightness_step_pct: 20
      - conditions:
          - condition: trigger
            id: button_2
        sequence:
          - service: light.turn_on
            target:
              entity_id: light.kitchen
            data:
              brightness_step_pct: -20
```

### Example 5: Notification with Trigger Details

```yaml
alias: "Debug Input Events"
trigger:
  - platform: device
    domain: ubisys
    device_id: abc123def456
    type: button_1_short_press
action:
  - service: notify.mobile_app
    data:
      title: "Ubisys Input Event"
      message: >
        {{ trigger.description }} detected
        (input {{ trigger.input_number }}, {{ trigger.press_type }})
```

## Debugging Tips

### Check Triggers Are Registered

Navigate to: Developer Tools → Events → Listen to Event
Event type: `ubisys_input_event`

Press a button. If event fires but automation doesn't, issue is with trigger attachment.

### Check Automation Logs

Navigate to: Settings → Automations & Scenes → [Your Automation] → Traces

View automation traces to see:
- When trigger fired
- Whether conditions passed
- Which actions ran
- Any errors

### Enable Debug Logging

```yaml
logger:
  logs:
    custom_components.ubisys.device_trigger: debug
    custom_components.ubisys.input_monitor: debug
```

Look for:
```
Attaching trigger: device_id=abc123, type=button_1_short_press
Trigger matched: button_1_short_press (input=0, press=short_press)
```

### Common Issues

**Issue:** Triggers don't appear in UI
- **Check:** Device is configured in Ubisys integration
- **Check:** Device model is correctly detected
- **Fix:** Restart Home Assistant

**Issue:** Trigger fires for wrong button
- **Check:** Input number mapping in PRESS_TYPE_TO_TRIGGER
- **Check:** Physical wiring matches expected button numbers
- **Fix:** Verify InputActions configuration

**Issue:** Automation runs multiple times
- **Check:** Multiple automations using same trigger
- **Check:** Trigger appearing twice in event logs
- **Fix:** Review automation configurations

**Issue:** Long press not detected
- **Check:** Button held for >1 second
- **Check:** InputActions includes long press transitions
- **Fix:** May need to reconfigure InputActions

## Next Steps (Phase 4)

After Phase 3 testing is complete:

1. **Implement event entities** (`event.py`)
   - Create event entity for each input
   - Show last press in dashboard
   - Provide history tracking

2. **Update documentation**
   - Add device trigger examples to README
   - Create user guide for automation creation
   - Document trigger types for each device

3. **Test user experience**
   - Get feedback on trigger names
   - Verify automation UI is intuitive
   - Consider additional trigger types

## Reporting Issues

When reporting trigger issues, include:

1. Device model and firmware version
2. Home Assistant version
3. Automation configuration (YAML)
4. Automation trace (if available)
5. Logs with debug enabled
6. Steps to reproduce
7. Expected vs actual behavior
