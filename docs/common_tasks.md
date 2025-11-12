# Common Tasks (Cookbook)

Compatibility: Home Assistant 2024.1+ (Python 3.11+)

A quick set of recipes for everyday tasks.

## Calibrate a J1 Cover

- UI: Go to the device page and click the “Calibrate” button.
- Service:

```yaml
service: ubisys.calibrate_j1
data:
  entity_id: cover.bedroom_shade
```

## Change Shade Type

- Options: Settings → Devices & Services → Ubisys → [Device] → Configure → select shade type → Submit.
- Re-run calibration afterwards.

## Configure D1 Phase Mode

```yaml
service: ubisys.configure_d1_phase_mode
data:
  entity_id: light.kitchen_dimmer
  phase_mode: reverse  # automatic | forward | reverse
```

## Configure D1 Ballast Range

```yaml
service: ubisys.configure_d1_ballast
data:
  entity_id: light.kitchen_dimmer
  min_level: 15
  max_level: 254
```

## Enable Verbose Logs

- Options: toggle “Verbose info logging” or “Verbose input event logging”.
- Or set HA logger:

```yaml
logger:
  default: warning
  logs:
    custom_components.ubisys: debug
```

## Create Automations using Input Events

See docs/device_triggers_examples.md for copy‑paste examples using `ubisys_input_event` and device triggers.
