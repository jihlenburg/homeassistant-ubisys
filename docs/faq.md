# Frequently Asked Questions (FAQ)

Compatibility: Home Assistant 2024.1+ (Python 3.11+)

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

