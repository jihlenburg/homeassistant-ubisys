# Ubisys S1/S1-R Power Switch Configuration

## Overview

The Ubisys S1 (flush mount) and S1-R (DIN rail) power switches support physical input configuration through the Home Assistant UI. This document explains how to configure physical wall switches connected to your S1/S1-R devices.

## Hardware Differences

| Model | Inputs | Mounting     | Metering Endpoint |
|-------|--------|--------------|-------------------|
| S1    | 1      | Flush mount  | EP3               |
| S1-R  | 2      | DIN rail     | EP4               |

**Key Difference**: S1-R is NOT just a DIN rail variant - it has 2 physical inputs vs. S1's single input.

## Configuration Via UI

### Step-by-Step Guide

1. **Navigate to Device Settings**
   - Go to: Settings ’ Devices & Services ’ Ubisys
   - Select your S1 or S1-R device
   - Click the "Configure" button

2. **Select Configuration Preset**
   - Choose from available presets based on your physical switch type
   - Configuration is applied immediately
   - If it fails, it automatically rolls back to previous configuration

3. **Test Your Configuration**
   - Press your physical switch
   - Verify the relay toggles as expected
   - Check device triggers in Developer Tools ’ Events

### Available Presets

#### S1 (Single Input) Presets:

**1. Toggle Switch (Default)**
- Description: Standard rocker/toggle wall switch
- Behavior: Any state change toggles the relay
- Use case: Traditional on/off switches

**2. Push Button - On/Off**
- Description: Two momentary push buttons
- Behavior: One button turns on, other turns off
- Use case: Separate on/off buttons

**3. Push Button - Toggle**
- Description: Single momentary push button
- Behavior: Each press toggles on/off
- Use case: Single push button switch

#### S1-R (Dual Input) Presets:

**1. Toggle Switches (Default)**
- Description: Two separate rocker/toggle switches
- Behavior: Each switch independently toggles the relay
- Use case: Multiple locations controlling same light

**2. Push Buttons - Independent**
- Description: Two momentary push buttons
- Behavior: Each button independently toggles the relay
- Use case: Two-location push button control

**3. Push Buttons - On/Off Pair**
- Description: Dedicated on and off buttons
- Behavior: Button 1 turns on, Button 2 turns off
- Use case: Separate on/off control

## Input Configuration Technical Details

### How It Works

1. **InputActions Micro-code**
   - Device stores input behavior as micro-code in cluster 0xFC00 attribute 0x0001
   - Micro-code maps: (input number, press type) ’ (Zigbee command to send)
   - Our integration generates this micro-code from user-friendly presets

2. **Preset-Based Configuration**
   - User selects preset from dropdown (not raw micro-code)
   - Integration converts preset to InputActions micro-code
   - Writes micro-code to device
   - Verifies by reading it back

3. **Automatic Rollback**
   - Old configuration backed up before applying new one
   - If write/verify fails, automatically restores backup
   - User is notified of success or failure

### Configuration Storage

- **Location**: Device non-volatile memory (survives restarts)
- **Persistence**: Configuration persists across power cycles
- **Reset**: Factory reset clears configuration back to defaults

## Troubleshooting

### Configuration Fails

**Symptom**: Configuration dialog shows error message

**Causes**:
1. Device is offline or unreachable
2. ZHA integration not loaded
3. Device is busy (another operation in progress)

**Solutions**:
1. Check device is powered and connected to Zigbee network
2. Restart Home Assistant and try again
3. Wait a few seconds and retry configuration

### Physical Switch Doesn't Work

**Symptom**: Pressing physical switch has no effect

**Causes**:
1. Wrong preset selected (toggle vs. momentary)
2. Physical wiring issue
3. Input not configured properly

**Solutions**:
1. Try different presets to match your switch type
2. Check physical wiring connections
3. Test with default preset (toggle switch)
4. Check input monitoring events in Developer Tools

### Relay Behavior Is Unexpected

**Symptom**: Relay turns on/off at wrong times

**Causes**:
1. Preset doesn't match physical switch type
2. Multiple presets configured incorrectly (S1-R)
3. Input polarity inverted

**Solutions**:
1. Ensure preset matches switch (momentary vs. toggle)
2. For S1-R, verify which physical input is which
3. Try inverting input polarity in advanced configuration

## Advanced: Custom InputActions

For advanced users who need custom input behaviors not covered by presets, see:
- `custom_components/ubisys/input_config.py` - Preset definitions
- Ubisys S1 Technical Reference Manual - InputActions micro-code format

## Device Triggers (Automation Integration)

In addition to controlling the relay, physical inputs can trigger automations:

### Available Triggers (per input)

- **Button 1 pressed** - Button is pushed down
- **Button 1 released** - Button is let go
- **Button 1 short press** - Brief press and release (<1s)
- **Button 1 long press** - Press and hold (>1s)
- **Button 2 pressed** (S1-R only)
- **Button 2 released** (S1-R only)
- **Button 2 short press** (S1-R only)
- **Button 2 long press** (S1-R only)

### Example Automation

```yaml
automation:
  - alias: "S1 Button 1 Long Press - All Lights Off"
    trigger:
      - platform: device
        domain: ubisys
        device_id: YOUR_DEVICE_ID
        type: button_1_long_press
    action:
      - service: light.turn_off
        target:
          area_id: living_room
```

## Migration from v1.x

If you were using the deprecated `ubisys.configure_s1_input` service:

1. **Remove service calls** from automations/scripts
2. **Reconfigure via UI** using the steps above
3. **Test thoroughly** to ensure behavior is correct

The old service has been removed in v2.1.0. All configuration is now done via the Config Flow UI.

## See Also

- [D1 Configuration](d1_configuration.md) - D1 dimmer configuration
- [Input Configuration Technical Details](input_configuration.md) - Deep dive into InputActions
- [Migration Guide](migration_v2.0.md) - Upgrading from v1.x
