# Usage Examples & Automations

Complete examples for controlling Ubisys devices and creating automations.

## 📖 Table of Contents

- [Basic Control](#basic-control)
- [Automation Examples](#automation-examples)
- [Lovelace UI Cards](#lovelace-ui-cards)
- [Service Calls](#service-calls)
- [Device Triggers](#device-triggers)
- [Templates & Scripts](#templates--scripts)

---

## 🎮 Basic Control

### J1 Window Covering

```yaml
# Open the shade completely
service: cover.open_cover
target:
  entity_id: cover.bedroom_shade

# Close the shade completely
service: cover.close_cover
target:
  entity_id: cover.bedroom_shade

# Stop movement
service: cover.stop_cover
target:
  entity_id: cover.bedroom_shade

# Set to specific position (0=closed, 100=open)
service: cover.set_cover_position
target:
  entity_id: cover.bedroom_shade
data:
  position: 50

# Set tilt position (venetian blinds only)
service: cover.set_cover_tilt_position
target:
  entity_id: cover.south_window_venetian
data:
  tilt_position: 75  # 0=closed, 100=open
```

### D1 Universal Dimmer

```yaml
# Turn on at full brightness
service: light.turn_on
target:
  entity_id: light.living_room_dimmer
data:
  brightness: 255

# Turn on at 50% brightness
service: light.turn_on
target:
  entity_id: light.living_room_dimmer
data:
  brightness_pct: 50

# Dim to 25% over 3 seconds
service: light.turn_on
target:
  entity_id: light.living_room_dimmer
data:
  brightness_pct: 25
  transition: 3

# Turn off
service: light.turn_off
target:
  entity_id: light.living_room_dimmer
```

### S1 Power Switch

```yaml
# Turn on
service: switch.turn_on
target:
  entity_id: switch.washing_machine

# Turn off
service: switch.turn_off
target:
  entity_id: switch.washing_machine

# Toggle
service: switch.toggle
target:
  entity_id: switch.washing_machine
```

---

## 🤖 Automation Examples

### Morning Routine

<details>
<summary>Open bedroom shades at sunrise</summary>

```yaml
automation:
  - alias: "Morning - Open Bedroom Shades"
    description: "Open shades 30 minutes after sunrise on workdays"
    trigger:
      - platform: sun
        event: sunrise
        offset: "00:30:00"
    condition:
      - condition: state
        entity_id: binary_sensor.workday
        state: "on"
    action:
      - service: cover.set_cover_position
        target:
          entity_id:
            - cover.bedroom_shade
            - cover.office_shade
        data:
          position: 100  # Fully open
```
</details>

<details>
<summary>Gradual morning wake-up lighting</summary>

```yaml
automation:
  - alias: "Morning - Gradual Wake-up Light"
    description: "Slowly increase bedroom light brightness"
    trigger:
      - platform: time
        at: "06:30:00"
    condition:
      - condition: state
        entity_id: binary_sensor.workday
        state: "on"
    action:
      # Start at 1% brightness
      - service: light.turn_on
        target:
          entity_id: light.bedroom_dimmer
        data:
          brightness_pct: 1

      # Gradually increase over 15 minutes
      - repeat:
          count: 30
          sequence:
            - delay:
                seconds: 30
            - service: light.turn_on
              target:
                entity_id: light.bedroom_dimmer
              data:
                brightness_pct: "{{ (repeat.index * 3.33) | int }}"
```
</details>

### Sun Protection

<details>
<summary>Close shades when temperature exceeds threshold</summary>

```yaml
automation:
  - alias: "Close Shades When Hot"
    description: "Protect from heat during hot afternoons"
    trigger:
      - platform: numeric_state
        entity_id: sensor.outside_temperature
        above: 30
    condition:
      - condition: sun
        after: sunrise
        before: sunset
      - condition: numeric_state
        entity_id: sun.sun
        attribute: elevation
        above: 30  # Sun is high enough to matter
    action:
      - service: cover.set_cover_position
        target:
          entity_id:
            - cover.south_window
            - cover.west_window
        data:
          position: 10  # Nearly closed
```
</details>

<details>
<summary>Adjust venetian blind tilt based on sun angle</summary>

```yaml
automation:
  - alias: "Adjust Venetian Tilt for Sun"
    description: "Block direct sun while allowing indirect light"
    trigger:
      - platform: numeric_state
        entity_id: sun.sun
        attribute: elevation
    action:
      - choose:
          # Morning/evening: mostly closed
          - conditions:
              - condition: numeric_state
                entity_id: sun.sun
                attribute: elevation
                below: 20
            sequence:
              - service: cover.set_cover_tilt_position
                target:
                  entity_id: cover.south_window_venetian
                data:
                  tilt_position: 20  # Nearly closed

          # Midday: completely closed
          - conditions:
              - condition: numeric_state
                entity_id: sun.sun
                attribute: elevation
                above: 45
            sequence:
              - service: cover.set_cover_tilt_position
                target:
                  entity_id: cover.south_window_venetian
                data:
                  tilt_position: 0  # Fully closed

        # Default: partially open
        default:
          - service: cover.set_cover_tilt_position
            target:
              entity_id: cover.south_window_venetian
            data:
              tilt_position: 40
```
</details>

### Evening & Night

<details>
<summary>Close all shades at sunset</summary>

```yaml
automation:
  - alias: "Evening - Close All Shades"
    description: "Close shades at sunset for privacy"
    trigger:
      - platform: sun
        event: sunset
        offset: "-00:15:00"  # 15 minutes before sunset
    action:
      - service: cover.close_cover
        target:
          entity_id:
            - cover.living_room_shade
            - cover.bedroom_shade
            - cover.kitchen_shade
```
</details>

<details>
<summary>Automatic nighttime lighting</summary>

```yaml
automation:
  - alias: "Night - Auto Dim Lights"
    description: "Dim lights automatically after 10 PM"
    trigger:
      - platform: time
        at: "22:00:00"
    action:
      - service: light.turn_on
        target:
          entity_id:
            - light.living_room_dimmer
            - light.hallway_dimmer
        data:
          brightness_pct: 20  # Dim for nighttime
```
</details>

### Presence Detection

<details>
<summary>Open shades when arriving home</summary>

```yaml
automation:
  - alias: "Arrival - Open Shades"
    description: "Welcome home by opening shades"
    trigger:
      - platform: state
        entity_id: person.john
        to: "home"
    condition:
      - condition: sun
        before: sunset
        after: sunrise
    action:
      - service: cover.open_cover
        target:
          entity_id: all  # All Ubisys covers
```
</details>

<details>
<summary>Close shades and turn off lights when leaving</summary>

```yaml
automation:
  - alias: "Departure - Secure Home"
    description: "Close shades and turn off lights when everyone leaves"
    trigger:
      - platform: state
        entity_id: zone.home
        to: "0"  # Nobody home
        for:
          minutes: 5
    action:
      - service: cover.close_cover
        target:
          entity_id: all

      - service: light.turn_off
        target:
          entity_id: all
```
</details>

### Smart Scheduling

<details>
<summary>Weekend vs. weekday schedules</summary>

```yaml
automation:
  - alias: "Morning Shades - Weekday"
    trigger:
      - platform: time
        at: "07:00:00"
    condition:
      - condition: state
        entity_id: binary_sensor.workday
        state: "on"
    action:
      - service: cover.open_cover
        target:
          entity_id: cover.bedroom_shade

  - alias: "Morning Shades - Weekend"
    trigger:
      - platform: time
        at: "09:00:00"  # Sleep in on weekends
    condition:
      - condition: state
        entity_id: binary_sensor.workday
        state: "off"
    action:
      - service: cover.set_cover_position
        target:
          entity_id: cover.bedroom_shade
        data:
          position: 50  # Partially open for gentle wake-up
```
</details>

---

## 🎨 Lovelace UI Cards

### Minimal Cover Card

```yaml
type: tile
entity: cover.bedroom_shade
name: Bedroom Shade
features:
  - type: "cover-open-close"
  - type: "cover-position"
```

### Detailed Cover Card with Tilt

```yaml
type: entities
title: South Window (Venetian)
entities:
  - entity: cover.south_window_venetian
    name: Position Control

  - type: custom:slider-entity-row
    entity: cover.south_window_venetian
    name: Position
    icon: mdi:window-shutter
    min: 0
    max: 100

  - type: custom:slider-entity-row
    entity: cover.south_window_venetian
    name: Tilt
    attribute: current_tilt_position
    icon: mdi:blinds
    min: 0
    max: 100
    tap_action:
      action: call-service
      service: cover.set_cover_tilt_position
      service_data:
        entity_id: cover.south_window_venetian
        tilt_position: "{{ value }}"

  - entity: button.south_window_calibrate
    name: Run Calibration
```

> [!NOTE]
> The tilt slider requires the [slider-entity-row](https://github.com/thomasloven/lovelace-slider-entity-row) custom card.

### Dimmer Card with Brightness Control

```yaml
type: light
entity: light.living_room_dimmer
name: Living Room
icon: mdi:ceiling-light
```

Or with more controls:

```yaml
type: entities
title: Living Room Lighting
entities:
  - entity: light.living_room_dimmer
    name: Dimmer

  - type: custom:slider-entity-row
    entity: light.living_room_dimmer
    name: Brightness
    icon: mdi:brightness-6
    toggle: true
```

### Multi-Device Dashboard

```yaml
type: vertical-stack
cards:
  - type: markdown
    content: |
      ## 🏠 Ubisys Devices

  - type: horizontal-stack
    cards:
      - type: tile
        entity: cover.bedroom_shade
        name: Bedroom
        icon: mdi:window-shutter

      - type: tile
        entity: cover.living_room_shade
        name: Living Room
        icon: mdi:window-shutter

  - type: horizontal-stack
    cards:
      - type: tile
        entity: light.kitchen_dimmer
        name: Kitchen
        icon: mdi:ceiling-light

      - type: tile
        entity: light.hallway_dimmer
        name: Hallway
        icon: mdi:ceiling-light

  - type: entities
    title: Quick Actions
    entities:
      - type: button
        name: Open All Shades
        icon: mdi:window-shutter-open
        tap_action:
          action: call-service
          service: cover.open_cover
          target:
            entity_id: all

      - type: button
        name: Close All Shades
        icon: mdi:window-shutter
        tap_action:
          action: call-service
          service: cover.close_cover
          target:
            entity_id: all
```

### Picture Elements Card

```yaml
type: picture-elements
image: /local/floorplan.png
elements:
  # Bedroom shade
  - type: state-icon
    entity: cover.bedroom_shade
    tap_action:
      action: toggle
    style:
      top: 20%
      left: 30%

  # Living room shade
  - type: state-icon
    entity: cover.living_room_shade
    tap_action:
      action: toggle
    style:
      top: 50%
      left: 60%

  # Kitchen dimmer
  - type: state-icon
    entity: light.kitchen_dimmer
    tap_action:
      action: toggle
    style:
      top: 70%
      left: 20%
```

---

## 🔧 Service Calls

### J1 Calibration Service

```yaml
# Basic calibration
service: ubisys.calibrate_j1
target:
  entity_id: cover.bedroom_shade

# Test mode (read-only health check)
service: ubisys.calibrate_j1
target:
  entity_id: cover.bedroom_shade
data:
  test_mode: true
```

### J1 Advanced Tuning

```yaml
service: ubisys.tune_j1_advanced
target:
  entity_id: cover.bedroom_shade
data:
  turnaround_guard_time: 10      # 500ms delay between direction changes
  inactive_power_threshold: 4096  # 4W motor stall threshold
  startup_steps: 20               # AC waves to run on startup
  additional_steps: 5             # 5% overtravel
```

### D1 Phase Mode Configuration

```yaml
# Configure for LED compatibility
service: ubisys.configure_d1_phase_mode
target:
  entity_id: light.living_room_dimmer
data:
  phase_mode: reverse  # Trailing edge for LEDs
```

### D1 Ballast Configuration

```yaml
# Set minimum brightness to prevent flickering
service: ubisys.configure_d1_ballast
target:
  entity_id: light.living_room_dimmer
data:
  min_level: 15
  max_level: 254
```

---

## 🎯 Device Triggers

### Button Press Automations

```yaml
# Short press on button 1
automation:
  - alias: "J1 Button 1 - Short Press"
    trigger:
      - platform: device
        domain: ubisys
        device_id: abc123...
        type: button_1_short_press
    action:
      - service: cover.set_cover_position
        target:
          entity_id: cover.bedroom_shade
        data:
          position: 50  # Go to 50%
```

```yaml
# Long press on button 2
automation:
  - alias: "D1 Button 2 - Long Press"
    trigger:
      - platform: device
        domain: ubisys
        device_id: def456...
        type: button_2_long_press
    action:
      - service: light.turn_on
        target:
          entity_id: light.all_lights
        data:
          brightness: 255  # Full brightness everywhere
```

See [Device Triggers Examples](device_triggers_examples.md) for more detailed examples.

---

## 📝 Templates & Scripts

### Template for Shade Position

```yaml
sensor:
  - platform: template
    sensors:
      bedroom_shade_percentage:
        friendly_name: "Bedroom Shade Open Percentage"
        value_template: "{{ state_attr('cover.bedroom_shade', 'current_position') }}"
        unit_of_measurement: "%"
```

### Script for Preset Positions

```yaml
script:
  bedroom_shade_morning:
    alias: "Bedroom Shade - Morning Position"
    sequence:
      - service: cover.set_cover_position
        target:
          entity_id: cover.bedroom_shade
        data:
          position: 75  # 75% open

  bedroom_shade_evening:
    alias: "Bedroom Shade - Evening Position"
    sequence:
      - service: cover.set_cover_position
        target:
          entity_id: cover.bedroom_shade
        data:
          position: 25  # 25% open for privacy
```

### Scene with Shades and Lights

```yaml
scene:
  - name: "Movie Time"
    entities:
      cover.living_room_shade:
        state: closed
      light.living_room_dimmer:
        state: on
        brightness: 51  # 20%

  - name: "Bright and Airy"
    entities:
      cover.living_room_shade:
        state: open
        current_position: 100
      light.living_room_dimmer:
        state: on
        brightness: 255
```

---

## 🔗 Related Documentation

- [J1 Calibration Guide](j1_calibration.md)
- [D1 Configuration Guide](d1_configuration.md)
- [Device Triggers Examples](device_triggers_examples.md)
- [Getting Started](getting_started.md)
