# Device Triggers — Examples

Compatibility: Home Assistant 2024.1+ (Python 3.11+)

This integration fires a `ubisys_input_event` for physical input activity. You can use it to build automations without YAML quirks.

## Basic toggle on short press

```yaml
alias: Toggle light on short press
trigger:
  - platform: event
    event_type: ubisys_input_event
    event_data:
      device_ieee: "00:12:4b:00:xx:xx:xx:xx"  # your device IEEE
      input_number: 0
      press_type: short_press
action:
  - service: light.toggle
    target:
      entity_id: light.living_room
```

## Dim while long press

```yaml
alias: Dim on long press
trigger:
  - platform: event
    event_type: ubisys_input_event
    event_data:
      device_ieee: "00:12:4b:00:xx:xx:xx:xx"
      input_number: 0
      press_type: long_press
action:
  - service: light.turn_on
    data:
      entity_id: light.living_room
      brightness_step: -25
```

## Use device triggers (GUI)

Device triggers are available in the UI for supported models. Choose your Ubisys device → Automations → Add trigger → Device → “Input pressed”.

- input_number 0 = first input (EP2)
- input_number 1 = second input (EP3, if present)

## Notes

- You can enable per-event INFO logs via Options → “Verbose input event logging” to help map presses while testing.
- For structured debugging, look for `Input event — model=..., endpoint=..., cluster=..., command=...` lines in the log.
