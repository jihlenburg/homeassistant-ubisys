# Security & Privacy

Compatibility: Home Assistant 2024.1+ (Python 3.11+)

Docs: [index](index.md) · [diagnostics](../custom_components/ubisys/diagnostics.py) · [logging policy](logging.md)

## Data Scope

This integration operates locally via ZHA and does not send data externally.

## Diagnostics Redaction

Diagnostics payloads redact device IEEE addresses and omit secrets. Endpoint/cluster maps and last calibration results are included for troubleshooting.

## Logging

- Quiet by default. Use Options toggles or HA logger integration to elevate verbosity.
- Avoids printing secrets or raw keys.
- `kv(...)` formatting is consistent and stable for grepping.

## Writes & Safeguards

- Manufacturer code handling is done via quirks or explicit manufacturer arguments.
- Attribute writes use write+verify with readback and rollback on mismatch.
- Zigbee commands use timeouts and limited retries.
