# Ubisys Zigbee Devices Integration

This integration provides enhanced support for Ubisys Zigbee window covering controllers (J1) in Home Assistant.

## Features

- **Custom ZHA Quirks** - Extends the standard ZHA support with manufacturer-specific attributes
- **Shade Type Configuration** - Configure your specific shade type (roller, venetian, etc.) for proper feature support
- **Feature Filtering** - Only shows relevant controls based on your shade configuration
- **Calibration Service** - Automated calibration sequence for accurate position tracking
- **HACS Compatible** - Easy installation and updates through HACS

## Supported Devices

- **Ubisys J1** - Window covering controller with support for:
  - Roller shades (position control)
  - Cellular shades (position control)
  - Vertical blinds (position control)
  - Venetian blinds (position + tilt control)
  - Exterior venetian blinds (position + tilt control)

## Installation

### Via HACS (Recommended)

1. Open HACS in Home Assistant
2. Click "Integrations"
3. Click the three dots in the top right corner
4. Select "Custom repositories"
5. Add this repository URL: `https://github.com/jihlenburg/homeassistant-ubisys`
6. Select "Integration" as the category
7. Click "Add"
8. Find "Ubisys Zigbee Devices" in HACS and install it
9. Restart Home Assistant

### Manual Installation

Run the one-line installer:

```bash
curl -sSL https://raw.githubusercontent.com/jihlenburg/homeassistant-ubisys/main/install.sh | bash
```

Or download and run:

```bash
wget https://raw.githubusercontent.com/jihlenburg/homeassistant-ubisys/main/install.sh
chmod +x install.sh
./install.sh
```

## Setup

1. Make sure your Ubisys device is paired with ZHA
2. Go to **Configuration** → **Integrations**
3. Click **+ Add Integration**
4. Search for "Ubisys"
5. Select your ZHA cover entity
6. Choose your shade type
7. Click Submit

## Calibration

After setup, run the calibration service to configure accurate position tracking:

1. Go to **Developer Tools** → **Services**
2. Select service: `ubisys.calibrate`
3. Select your Ubisys cover entity
4. Click **Call Service**

The calibration will:
- Move the shade to fully open
- Reset the position counter
- Move to fully closed while counting steps
- Save the total step count for accurate positioning

## Support

- **Issues**: https://github.com/jihlenburg/homeassistant-ubisys/issues
- **Documentation**: https://github.com/jihlenburg/homeassistant-ubisys

## Configuration

You can change the shade type at any time:

1. Go to **Configuration** → **Integrations**
2. Find the Ubisys integration
3. Click **Configure**
4. Select a new shade type
5. Click Submit

The available controls will update automatically based on your selection.
