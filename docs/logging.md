# Logging Policy

Compatibility: Home Assistant 2024.1+ (Python 3.11+)

This integration aims to be quiet by default and richly informative on demand.

## Principles

- Quiet defaults: routine operations at DEBUG, warnings/errors only when needed.
- Structured context: use compact `key=value` logs for greppable, diff‑friendly output.
- Controlled verbosity: Options Flow toggles enable richer INFO logs without editing code.

## Toggles (Options → Configure)

- `Verbose info logging`: elevates selected DEBUG messages to INFO (setup, lifecycle, parsed configurations).
- `Verbose input event logging`: logs each physical input event at INFO (otherwise DEBUG).

Toggles apply globally across all Ubisys entries.

## Log helpers

- `info_banner(logger, title, **kvs)`: 3‑line banner at INFO for major milestones.
- `kv(logger, level, msg, **kvs)`: one‑line message with sorted `key=value` pairs.
- `_LOGGER.log(level, ...)`: plain narrative logging where structure isn’t useful.

`kv` is no‑op if the level is disabled (no formatting cost).

## Examples

- Input event (compact, greppable):
  `Input event — model=J1, endpoint=2, cluster=0x0102, command=0x02`
- Lifecycle (gated by `verbose_info_logging`):
  `Input monitoring ready — device_ieee=…, model=J1, elapsed_s=0.3`

## HA logger integration

You can further tune levels via Home Assistant’s logger integration:

```yaml
logger:
  default: warning
  logs:
    custom_components.ubisys: debug
```
