# Ubisys Zigbee Devices Integration

This integration provides enhanced support for Ubisys Zigbee devices in Home Assistant, including window covering controllers (J1), universal dimmers (D1), and power switches (S1).

## Features

- **Custom ZHA Quirks** - Extends standard ZHA support with manufacturer-specific attributes
- **Smart Feature Filtering** - J1: Shows only relevant controls based on shade type
- **Automated Calibration** - J1: One-click calibration with motor stall detection
- **Phase Control** - D1: Forward/reverse/automatic phase mode configuration
- **Ballast Configuration** - D1: Min/max brightness level tuning
- **Input Configuration** - S1/D1/J1: Preset-based physical button behavior
- **Device Triggers** - Physical button presses as automation triggers
- **HACS Compatible** - Easy installation and updates through HACS

## Supported Devices

- **Ubisys J1/J1-R** - Window covering controller
  - Roller, cellular, vertical, venetian, exterior venetian shades
  - Position and tilt control (based on shade type)
  - Automated calibration with motor stall detection

- **Ubisys D1/D1-R** - Universal dimmer
  - Phase mode configuration (automatic/forward/reverse)
  - Ballast min/max brightness levels
  - Input configuration presets

- **Ubisys S1/S1-R** - Power switch
  - Input configuration presets
  - Device triggers for automation

## Installation

### Via HACS (Recommended)

1. Open HACS in Home Assistant
2. Click "Integrations"
3. Click the three dots menu → "Custom repositories"
4. Add: `https://github.com/jihlenburg/homeassistant-ubisys`
5. Select "Integration" as the category
6. Find "Ubisys Zigbee Devices" and install
7. Restart Home Assistant

## Setup

1. Ensure your Ubisys device is paired with ZHA
2. Go to **Settings** → **Devices & Services**
3. Click **+ Add Integration**
4. Search for "Ubisys"
5. Select your device (auto-discovered from ZHA)
6. For J1: Choose your shade type
7. Click Submit

## J1 Calibration

After setup, calibrate your J1 for accurate position tracking:

1. Go to **Developer Tools** → **Services**
2. Select service: `ubisys.calibrate_j1`
3. Select your Ubisys J1 cover entity
4. Click **Call Service**

Or use the **Calibrate** button in the device controls.

## Support

- **Issues**: https://github.com/jihlenburg/homeassistant-ubisys/issues
- **Documentation**: https://github.com/jihlenburg/homeassistant-ubisys

## Configuration

Access device options via **Settings** → **Devices & Services** → **Ubisys** → Select device → **Configure**

- **J1**: Shade type, advanced tuning, input configuration
- **D1**: Phase mode, ballast levels, input configuration
- **S1**: Input configuration presets
