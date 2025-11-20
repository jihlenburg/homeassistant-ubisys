# Ubisys S1/S1-R Power Switch Configuration

Compatibility: Home Assistant 2024.1+ (Python 3.11+)

Docs: [index](../index.md) · [user guide](../user_guide.md) · [troubleshooting](../troubleshooting.md)

## Overview

The Ubisys S1 (flush mount) and S1-R (DIN rail) power switches support physical input configuration via the Options Flow. The integration wraps the underlying ZHA switch entity and provides preset-based input configuration.

Status: Full support with wrapper platform, input presets, and device triggers for automations.

## Inputs and Metering

| Model | Inputs | Mounting    | Metering Endpoint |
|-------|--------|-------------|-------------------|
| S1    | 1      | Flush mount | EP3               |
| S1-R  | 2      | DIN rail    | EP4               |

## Input Configuration

### Available Presets

#### S1 (Single Input)

| Preset | Behavior |
|--------|----------|
| **Toggle switch** (default) | Each press toggles output on/off |
| On when pressed | Turns on when pressed, off when released |
| Off when pressed | Turns off when pressed, on when released |
| Toggle + Dim | Short press toggles, long press dims up/down (for controlling remote dimmers) |
| Decoupled | Buttons fire events to HA but don't control output directly |

#### S1-R (Dual Input)

| Preset | Behavior |
|--------|----------|
| **Toggle switch** (default) | Each press toggles output on/off |
| On when pressed | Turns on when pressed, off when released |
| Off when pressed | Turns off when pressed, on when released |
| On/Off button pair | Button 1 turns on, Button 2 turns off |
| Toggle + Dim | Short press toggles, long press dims up/down (for controlling remote dimmers) |
| Brightness up/down buttons | Button 1 brightens, Button 2 dims (for controlling remote dimmers) |
| Decoupled | Buttons fire events to HA but don't control output directly |

### Configuring Input Behavior

1. Go to **Settings → Devices & Services → Ubisys → [Your Device] → Configure**
2. Select **Configure Device** from the menu
3. Choose a preset from the **Input Behavior** dropdown
4. Submit

The integration writes InputActions micro-code to the device and verifies the result. If verification fails, it automatically rolls back to the previous configuration.

### Dimmer Control Presets

The **Toggle + Dim** and **Brightness up/down** presets allow S1/S1-R devices to control remote dimmers through ZigBee group binding:

- **Toggle + Dim**: Uses LevelControl cluster commands (move up/down) with alternating long presses
- **Brightness up/down**: Button 1 sends on + move up, Button 2 sends off + move down

**Use case**: Install S1-R near a door to control a D1 dimmer elsewhere via ZigBee binding. Local control works even if Home Assistant is offline.

### Decoupled Mode

Use the **Decoupled** preset when you want full Home Assistant control:

- Physical buttons no longer control the switch directly
- Button presses are detected and sent to Home Assistant as events
- Create automations using device triggers

**Important**: Decoupled mode means the device won't respond to button presses if Home Assistant is unavailable. Use this only when HA-controlled automation is required.

### Automation Example (Decoupled Mode)

```yaml
automation:
  - alias: "S1 Button 1 Controls Scene"
    trigger:
      - platform: device
        domain: ubisys
        device_id: !input device_id
        type: button_1_short_press
    action:
      - service: scene.turn_on
        target:
          entity_id: scene.living_room_evening
```

## Device Triggers

The integration exposes physical button presses as device triggers for automations:

| S1 Triggers | S1-R Triggers |
|-------------|---------------|
| Button 1 pressed | Button 1 pressed |
| Button 1 released | Button 1 released |
| Button 1 short press | Button 1 short press |
| Button 1 long press | Button 1 long press |
| | Button 2 pressed |
| | Button 2 released |
| | Button 2 short press |
| | Button 2 long press |

These triggers work with all presets, not just decoupled mode. You can use button presses for additional automations while maintaining local control.

## Logging Options

- **Verbose info logging**: Enable INFO-level logs for configuration operations
- **Verbose input logging**: Enable INFO-level logs for each button press event
