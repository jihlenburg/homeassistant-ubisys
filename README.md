# Ubisys Zigbee Devices for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)
[![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)](https://github.com/jihlenburg/homeassistant-ubisys)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

A complete Home Assistant integration for Ubisys Zigbee window covering controllers, providing enhanced support with custom ZHA quirks, smart feature filtering, and automated calibration.

## ✨ Features

- 🔌 **Custom ZHA Quirks** - Access manufacturer-specific attributes (total steps, tilt transition steps, configured mode)
- 🎯 **Smart Feature Filtering** - Only show controls that match your shade type configuration
- 🎚️ **Shade Type Support** - Roller, cellular, vertical blinds, venetian blinds, and exterior venetian blinds
- 🔧 **Automated Calibration** - One-command calibration service for accurate position tracking
- 🏗️ **Config Flow** - Easy setup through the Home Assistant UI
- 📦 **HACS Compatible** - Simple installation and automatic updates
- 🔄 **State Synchronization** - Real-time updates from the underlying ZHA entity

## 🎛️ Supported Devices

| Device | Lift Control | Tilt Control | Calibration |
|--------|--------------|--------------|-------------|
| **Ubisys J1** | ✅ | ✅ | ✅ |

### Shade Types

| Type | Features | WindowCoveringType |
|------|----------|-------------------|
| Roller Shade | Open, Close, Stop, Set Position | 0x00 |
| Cellular Shade | Open, Close, Stop, Set Position | 0x00 |
| Vertical Blind | Open, Close, Stop, Set Position | 0x04 |
| Venetian Blind | Position + Tilt controls | 0x08 |
| Exterior Venetian | Position + Tilt controls | 0x08 |

## 📦 Installation

### Method 1: One-Line Installer (Recommended for Raspberry Pi / Home Assistant OS)

**For Raspberry Pi / Home Assistant OS:**

```bash
# SSH into your Home Assistant instance
ssh root@homeassistant.local
# (or use your IP: ssh root@192.168.1.xxx)

# Run the installer
curl -sSL https://raw.githubusercontent.com/jihlenburg/homeassistant-ubisys/main/install.sh | bash
```

**For standard Linux/macOS installations:**

```bash
curl -sSL https://raw.githubusercontent.com/jihlenburg/homeassistant-ubisys/main/install.sh | bash
```

The installer will:
- Create all required directories (`custom_components`, `custom_zha_quirks`, `python_scripts`)
- Download all integration files from GitHub
- Install ZHA quirk for manufacturer-specific attributes
- Install calibration Python script
- Update your `configuration.yaml` with required settings
- Create timestamped backups of existing files
- Validate your Home Assistant configuration
- Provide rollback capability on errors

**Post-installation:**
1. Restart Home Assistant: `ha core restart` (or via UI: Configuration → System → Restart)
2. Verify installation in logs: `grep -i ubisys /config/home-assistant.log`
3. Check integration appears: Configuration → Integrations → Add Integration → Search "Ubisys"

### Method 2: HACS

1. Open HACS in Home Assistant
2. Go to **Integrations**
3. Click the **⋮** menu → **Custom repositories**
4. Add repository: `https://github.com/jihlenburg/homeassistant-ubisys`
5. Category: **Integration**
6. Click **Add**
7. Search for "Ubisys Zigbee Devices"
8. Click **Download**
9. Restart Home Assistant

### Method 3: Manual Installation

1. Download the latest release
2. Copy `custom_components/ubisys` to your `config/custom_components/` directory
3. Copy `custom_zha_quirks/ubisys_j1.py` to your `config/custom_zha_quirks/` directory
4. Copy `python_scripts/ubisys_j1_calibrate.py` to your `config/python_scripts/` directory
5. Add to `configuration.yaml`:

```yaml
zha:
  custom_quirks_path: custom_zha_quirks

python_script:
```

6. Restart Home Assistant

## 🚀 Quick Start

### 1. Pair Your Device

First, pair your Ubisys J1 with ZHA:

1. Go to **Configuration** → **Integrations** → **ZHA**
2. Click **Add Device**
3. Put your J1 into pairing mode
4. Wait for discovery and setup

### 2. Add Ubisys Integration

1. Go to **Configuration** → **Integrations**
2. Click **+ Add Integration**
3. Search for "Ubisys"
4. Select your ZHA cover entity from the dropdown
5. Choose your shade type:
   - **Roller Shade** - Standard roller blinds
   - **Cellular Shade** - Honeycomb/cellular blinds
   - **Vertical Blind** - Vertical slat blinds
   - **Venetian Blind** - Indoor horizontal slat blinds with tilt
   - **Exterior Venetian Blind** - Outdoor horizontal slat blinds with tilt
6. Click **Submit**

### 3. Calibrate Your Device

Run the calibration service to set up accurate position tracking:

**Via UI:**
1. Go to **Developer Tools** → **Services**
2. Service: `ubisys.calibrate`
3. Entity: Select your Ubisys cover
4. Click **Call Service**

**Via YAML:**
```yaml
service: ubisys.calibrate
data:
  entity_id: cover.bedroom_shade
```

**Via Automation:**
```yaml
automation:
  - alias: "Calibrate Ubisys on Startup"
    trigger:
      - platform: homeassistant
        event: start
    action:
      - service: ubisys.calibrate
        data:
          entity_id: cover.bedroom_shade
```

## 🔧 Calibration Process

The calibration service performs the following steps automatically:

1. **Set Window Covering Type** - Configures the device based on your shade type
2. **Move to Open** - Moves the shade to fully open position
3. **Reset Counter** - Sets the position counter to zero
4. **Move to Closed** - Moves to fully closed while counting motor steps
5. **Read Total Steps** - Retrieves and stores the total step count
6. **Read Tilt Steps** - For venetian blinds, reads tilt transition steps
7. **Notification** - Sends a completion notification with results

### What You'll See

During calibration (30-90 seconds):
- The shade opens completely
- Brief pause
- The shade closes completely
- You'll receive a notification when complete

**Success Notification:**
```
Calibration Complete

Ubisys device cover.bedroom_shade has been calibrated successfully.

Shade type: venetian
Total steps: 4523
Tilt transition steps: 267
```

## 📖 Usage Examples

### Basic Control

```yaml
# Open the shade
service: cover.open_cover
target:
  entity_id: cover.bedroom_shade

# Set to 50% open
service: cover.set_cover_position
target:
  entity_id: cover.bedroom_shade
data:
  position: 50

# Set tilt to 75% (venetian only)
service: cover.set_cover_tilt_position
target:
  entity_id: cover.bedroom_shade
data:
  tilt_position: 75
```

### Automation Examples

**Morning Routine:**
```yaml
automation:
  - alias: "Morning - Open Bedroom Shades"
    trigger:
      - platform: time
        at: "07:00:00"
    condition:
      - condition: state
        entity_id: binary_sensor.workday
        state: "on"
    action:
      - service: cover.set_cover_position
        target:
          entity_id: cover.bedroom_shade
        data:
          position: 100  # Fully open
```

**Sun Protection:**
```yaml
automation:
  - alias: "Close Shades When Hot"
    trigger:
      - platform: numeric_state
        entity_id: sensor.outside_temperature
        above: 30
    condition:
      - condition: sun
        after: sunrise
        before: sunset
    action:
      - service: cover.close_cover
        target:
          entity_id: cover.living_room_shade
```

**Venetian Blind Tilt Based on Sun:**
```yaml
automation:
  - alias: "Adjust Tilt for Sun Angle"
    trigger:
      - platform: numeric_state
        entity_id: sun.sun
        attribute: elevation
        above: 45
    action:
      - service: cover.set_cover_tilt_position
        target:
          entity_id: cover.south_window_venetian
        data:
          tilt_position: 30  # Nearly closed
```

## 🎨 Lovelace Card Example

```yaml
type: entities
title: Bedroom Shade
entities:
  - entity: cover.bedroom_shade
    name: Position
  - type: custom:slider-entity-row
    entity: cover.bedroom_shade
    name: Position
    min: 0
    max: 100
  - type: custom:slider-entity-row
    entity: cover.bedroom_shade
    name: Tilt
    attribute: current_tilt_position
    min: 0
    max: 100
  - type: button
    name: Calibrate
    tap_action:
      action: call-service
      service: ubisys.calibrate
      service_data:
        entity_id: cover.bedroom_shade
```

## 🔄 Changing Shade Type

You can change the configured shade type at any time:

1. Go to **Configuration** → **Integrations**
2. Find your Ubisys device
3. Click **Configure**
4. Select the new shade type
5. Click **Submit**

The supported features will update immediately. Re-run calibration after changing shade type.

## 🛠️ Troubleshooting

### Shade doesn't respond to commands

1. Check that the ZHA integration shows the device as available
2. Try restarting the ZHA integration
3. Check Zigbee signal strength - consider adding a router

### Position is inaccurate

1. Run the calibration service: `ubisys.calibrate`
2. Make sure the shade can move freely (no obstructions)
3. Ensure the shade is at a known position before calibration

### Tilt controls don't appear

1. Check that you selected a venetian blind shade type
2. Reconfigure the integration and select the correct type
3. Restart Home Assistant

### Calibration fails

1. Ensure the shade has power and is responsive to basic commands
2. Check Home Assistant logs for error details
3. Manually test open/close commands through ZHA first
4. Make sure python_script integration is enabled

### Integration not showing in UI

1. Verify files are in `custom_components/ubisys/`
2. Check `configuration.yaml` for the ZHA quirks path
3. Restart Home Assistant
4. Check logs: `grep -i ubisys home-assistant.log`

## 📚 Advanced Configuration

### Direct ZHA Cluster Access

For advanced users who want to directly access manufacturer attributes:

```python
# Read total steps
service: zha.issue_zigbee_cluster_command
data:
  ieee: "00:12:4b:00:1c:a1:b2:c3"
  endpoint_id: 2
  cluster_id: 0x0102
  cluster_type: in
  command: read_attributes
  command_type: client
  args:
    attribute: 0x1002
  manufacturer: 0x10F2
```

## 🏗️ Development

### Project Structure

```
homeassistant-ubisys/
├── custom_components/ubisys/     # Main integration
│   ├── __init__.py              # Setup and services
│   ├── config_flow.py           # Configuration UI
│   ├── const.py                 # Constants
│   ├── cover.py                 # Cover platform
│   ├── manifest.json            # Integration metadata
│   ├── services.yaml            # Service definitions
│   ├── strings.json             # UI strings
│   └── translations/
│       └── en.json              # English translations
├── custom_zha_quirks/
│   └── ubisys_j1.py             # ZHA quirk for J1
├── python_scripts/
│   └── ubisys_j1_calibrate.py   # Calibration script
├── docs/                        # Documentation
├── install.sh                   # Installation script
└── README.md                    # This file
```

### Testing

1. Clone the repository
2. Create a symbolic link to your HA config:
   ```bash
   ln -s /path/to/repo/custom_components/ubisys ~/.homeassistant/custom_components/ubisys
   ```
3. Restart Home Assistant
4. Check logs for errors

### Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Home Assistant community
- ZHA integration maintainers
- Ubisys for their excellent Zigbee devices

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/jihlenburg/homeassistant-ubisys/issues)
- **Discussions**: [GitHub Discussions](https://github.com/jihlenburg/homeassistant-ubisys/discussions)
- **Home Assistant Community**: [Community Forum](https://community.home-assistant.io/)

## 🗺️ Roadmap

- [ ] Support for Ubisys J1-R (roller shutter variant)
- [ ] Support for Ubisys S1/S2 switches
- [ ] Scene support for preset positions
- [ ] Position offset configuration
- [ ] Speed control configuration
- [ ] Web-based calibration wizard
- [ ] Multi-language support

---

**Made with ❤️ for the Home Assistant community**
