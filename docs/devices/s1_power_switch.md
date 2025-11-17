# Ubisys S1/S1-R Power Switch Configuration

Compatibility: Home Assistant 2024.1+ (Python 3.11+)

Docs: [index](../index.md) · [user guide](../README.md) · [troubleshooting](../troubleshooting.md)

## Overview

The Ubisys S1 (flush mount) and S1-R (DIN rail) power switches support physical input configuration via the Options Flow.

Status: Wrapper platform exists; advanced features and quirks are evolving. Input presets are available via Options.

## Inputs and Metering

| Model | Inputs | Mounting    | Metering Endpoint |
|-------|--------|-------------|-------------------|
| S1    | 1      | Flush mount | EP3               |
| S1-R  | 2      | DIN rail    | EP4               |

## Configure Physical Inputs (Presets)

1. Go to Settings → Devices & Services → Ubisys → [Your Device] → Configure.
2. Choose “Configure Physical Inputs”.
3. Select a preset:
   - Toggle
   - On only / Off only
   - Rocker (On/Off pair)
4. Submit. The integration writes InputActions micro-code and verifies the result.

Notes
- Use “Verbose info logging” if you want INFO-level confirmation in logs.
- If verification fails, the integration rolls back to the previous configuration.
