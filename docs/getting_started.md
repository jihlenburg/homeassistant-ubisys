# Getting Started

Compatibility: Home Assistant 2024.1+ (Python 3.11+)

Docs: [index](index.md) · [support matrix](device_support_matrix.md) · [common tasks](common_tasks.md) · [FAQ](faq.md)

This quick guide helps you install, configure, and use the Ubisys integration in Home Assistant. It links directly to the relevant option flows and task‑focused docs for common scenarios.

## 1) Install the Integration

- Recommended: run `./install.sh` on your HA host. It creates folders, copies files, installs quirks, and validates your config.
- Alternatively follow README → Installation (HACS or manual).
- Restart Home Assistant when finished: `ha core restart` (or UI: Settings → System → Restart).

## 2) Pair Your Device (ZHA)

- Go to Settings → Devices & Services → ZHA → Add Device, then put your device into pairing mode.
- After pairing, ZHA will show your Ubisys device (e.g., J1, D1, S1).

## 3) Configure via Options Flow

Open Settings → Devices & Services → Ubisys → [Your Device] → Configure.

- J1/J1‑R (window covering): select your shade type and proceed. See: docs/j1_calibration.md
- D1/D1‑R (dimmer): configure phase mode and ballast, then input behavior. See: docs/d1_configuration.md
- S1/S1‑R (switch): configure input behavior presets. See: docs/s1_configuration.md
- Input configuration (buttons/rockers) for D1/S1 is preset‑based. See: docs/input_configuration.md

## 4) Calibrate J1 Cover (One‑Click)

- On the device page, click the “Calibrate” button, or call the `ubisys.calibrate_j1` service.
- The integration uses stall detection and verifies results automatically. See: docs/j1_calibration.md

## 5) Verify and Use

- Check the entity in Developer Tools → States. Shade type and features reflect your selection.
- For dimmers, verify flicker‑free range and adjust phase/ballast if needed.

## Helpful Links

- J1 calibration: docs/j1_calibration.md
- D1 configuration: docs/d1_configuration.md
- S1 configuration: docs/s1_configuration.md
- Input configuration presets (D1/S1): docs/input_configuration.md
- Troubleshooting: docs/troubleshooting.md
