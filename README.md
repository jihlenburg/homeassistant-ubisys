# Ubisys Zigbee Devices for Home Assistant

[![CI](https://github.com/jihlenburg/homeassistant-ubisys/actions/workflows/ci.yml/badge.svg)](https://github.com/jihlenburg/homeassistant-ubisys/actions/workflows/ci.yml)
[![HACS](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)
[![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)](https://github.com/jihlenburg/homeassistant-ubisys/releases/latest)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

**Smart feature filtering for Ubisys Zigbee window coverings, dimmers, and switches** — Show only the controls that match your device's capabilities.

📚 **[Documentation](docs/index.md)** | 🚀 **[Quick Start](#-quick-start)** | 🛠️ **[Supported Devices](#%EF%B8%8F-supported-devices)** | 💬 **[Community](https://github.com/jihlenburg/homeassistant-ubisys/discussions)**

---

## 🎯 Why Use This Integration?

**The Problem:** Home Assistant's default ZHA shows *all* window covering controls for every blind — confusing tilt sliders on roller shades that don't tilt, no guidance on which controls actually work for your shade type.

**The Solution:** This integration filters controls based on your actual shade type:

| Your Shade Type | What You See | What's Hidden |
|-----------------|--------------|---------------|
| Roller / Cellular / Vertical | Open, Close, Stop, Position | ❌ Tilt controls |
| Venetian (indoor/outdoor) | Position **+** Tilt | ✅ All controls |

**Plus:** One-click calibration, auto-discovery when paired with ZHA, persistent device configuration.

---

## ✨ Features

- 🔍 **Auto-Discovery** — Detects Ubisys devices automatically when paired with ZHA
- 🎯 **Smart Feature Filtering** — Show only controls that match your shade/device type
- 🔧 **One-Click Calibration** — Automated J1 calibration via button or service
- 🎛️ **Phase Control** — Configure D1 dimmers for LED compatibility (reverse/forward/auto)
- 🏠 **Device Triggers** — Physical button presses trigger Home Assistant automations
- 📊 **Diagnostics & Repairs** — Actionable issues when clusters/quirks are missing
- 🔇 **Quiet by Default** — Optional verbose logging for troubleshooting
- 📦 **HACS Compatible** — Easy installation and automatic updates

---

## 🛠️ Supported Devices

| Device | Type | Status | Key Features |
|--------|------|--------|--------------|
| **J1 / J1-R** | Window Covering | ✅ Fully Supported | Position, Tilt, Auto-Calibration |
| **D1 / D1-R** | Universal Dimmer | ✅ Fully Supported | Phase Control, Ballast Config |
| **S1 / S1-R** | Power Switch | ✅ Supported | Input Config, Power Metering (via ZHA) |
| **S2 / S2-R** | Dual Switch | 📋 Planned | Not yet implemented |

> [!NOTE]
> **J1 Shade Types:** Roller, Cellular, Vertical Blind, Venetian, Exterior Venetian
> **Full device support matrix:** [Device Support Matrix](docs/device_support_matrix.md)

---

## 🚀 Quick Start

### 1. Install via HACS

<details>
<summary>Click to expand installation steps</summary>

1. Open **HACS** in Home Assistant
2. Go to **Integrations**
3. Click **⋮** menu → **Custom repositories**
4. Add: `https://github.com/jihlenburg/homeassistant-ubisys`
5. Category: **Integration**
6. Search "Ubisys Zigbee Devices"
7. Click **Download**
8. **Restart Home Assistant**

**Other installation methods:** [Installation Guide](docs/installation.md)
</details>

<details>
<summary><strong>Want to test beta features?</strong></summary>

1. In HACS, go to the Ubisys integration
2. Click **⋮** → **Redownload**
3. Enable **"Show beta versions"**
4. Select the beta version (e.g., `v1.1.0-beta.1`)
5. **Restart Home Assistant**

**Note:** Beta versions may contain bugs. Report issues with the `beta-feedback` tag.
</details>

### 2. Pair Your Device with ZHA

1. **Settings** → **Devices & Services** → **ZHA** → **Add Device**
2. Put your Ubisys device in pairing mode
3. Wait for ZHA to discover it

### 3. Configure the Integration

The integration auto-discovers your device! Look for the notification:

1. Click notification or go to **Settings** → **Devices & Services**
2. Find **"Ubisys [Device]"** in discovered integrations
3. Click **Configure**
4. Select shade type (J1) or configure options (D1/S1)
5. **Submit**

**Result:** One cover/light/switch entity with correct features. Original ZHA entity auto-hidden.

### 4. Calibrate (J1 only)

**Via Button:**
1. Go to device page: **Settings** → **Devices & Services** → **Ubisys** → Your Device
2. Click **Calibrate** button
3. Wait 60-120 seconds

**Or via Service:**
```yaml
service: ubisys.calibrate_j1
target:
  entity_id: cover.bedroom_shade
```

**Learn more:** [J1 Calibration Guide](docs/j1_calibration.md)

---

## 📖 Usage

<details>
<summary><strong>J1 Window Covering</strong></summary>

```yaml
# Basic control
service: cover.open_cover
target:
  entity_id: cover.bedroom_shade

# Set position (0=closed, 100=open)
service: cover.set_cover_position
target:
  entity_id: cover.bedroom_shade
data:
  position: 50

# Set tilt (venetian only)
service: cover.set_cover_tilt_position
target:
  entity_id: cover.south_window
data:
  tilt_position: 75
```

**More examples:** [Usage Examples](docs/examples.md)
</details>

<details>
<summary><strong>D1 Universal Dimmer</strong></summary>

```yaml
# Turn on at 50% brightness
service: light.turn_on
target:
  entity_id: light.living_room_dimmer
data:
  brightness_pct: 50

# Configure for LED compatibility
service: ubisys.configure_d1_phase_mode
target:
  entity_id: light.living_room_dimmer
data:
  phase_mode: reverse  # Trailing edge for LEDs

# Prevent flickering
service: ubisys.configure_d1_ballast
target:
  entity_id: light.living_room_dimmer
data:
  min_level: 15  # Adjust until flickering stops
  max_level: 254
```

**Full configuration guide:** [D1 Configuration](docs/d1_configuration.md)
</details>

<details>
<summary><strong>Device Triggers (Button Press Automations)</strong></summary>

```yaml
automation:
  - alias: "Button 1 Short Press - Open Shade 50%"
    trigger:
      - platform: device
        domain: ubisys
        device_id: abc123...
        type: button_1_short_press
    action:
      - service: cover.set_cover_position
        target:
          entity_id: cover.bedroom_shade
        data:
          position: 50
```

**More trigger examples:** [Device Triggers Guide](docs/device_triggers_examples.md)
</details>

---

## 🔧 Configuration

### Change Shade Type (J1)

1. **Settings** → **Integrations** → Find your Ubisys device
2. Click **Configure**
3. Select new shade type
4. **Submit**
5. Re-run calibration

### Configure Logging

**Enable verbose logging:**
1. Device page → **Configure** → **Options**
2. Enable "Verbose info logging" and/or "Verbose input event logging"

Or via `configuration.yaml`:
```yaml
logger:
  logs:
    custom_components.ubisys: debug
```

**Logging guide:** [Logging Policy](docs/logging.md)

---

## 🛠️ Troubleshooting

<details>
<summary><strong>Device not discovered after pairing with ZHA</strong></summary>

1. Verify device appears in ZHA: **Settings** → **Devices & Services** → **ZHA**
2. Check device model matches exactly (e.g., "J1", not "J1 (5502)")
3. Restart Home Assistant
4. Manually add: **Settings** → **Integrations** → **Add Integration** → "Ubisys"

**Full troubleshooting:** [Troubleshooting Guide](docs/troubleshooting.md)
</details>

<details>
<summary><strong>Calibration fails or times out</strong></summary>

1. Ensure shade has power and responds to basic commands
2. Remove physical obstructions
3. Check logs: `grep -i "calibration\|ubisys" /config/home-assistant.log`
4. Try test mode first: `test_mode: true`

**Detailed debugging:** [J1 Calibration Guide](docs/j1_calibration.md#troubleshooting)
</details>

<details>
<summary><strong>Tilt controls missing (Venetian blinds)</strong></summary>

1. Verify shade type: **Developer Tools** → **States** → Find entity → Check `shade_type` attribute
2. Reconfigure: Select "Venetian Blind" or "Exterior Venetian Blind"
3. Re-run calibration
4. Restart Home Assistant

</details>

**More solutions:** [Troubleshooting Guide](docs/troubleshooting.md) • [FAQ](docs/faq.md)

---

## 📚 Documentation

### User Guides
- 📖 [Getting Started](docs/getting_started.md)
- 🪟 [J1 Calibration Guide](docs/j1_calibration.md)
- 💡 [D1 Configuration Guide](docs/d1_configuration.md)
- 🎯 [Device Triggers & Automations](docs/device_triggers_examples.md)
- 📝 [Usage Examples & Lovelace Cards](docs/examples.md)

### Reference
- 🛠️ [Installation Guide](docs/installation.md)
- 🐛 [Troubleshooting](docs/troubleshooting.md)
- ❓ [FAQ](docs/faq.md)
- ⚠️ [Known Issues & Roadmap](docs/known_issues.md)
- 🗺️ [Roadmap](docs/roadmap.md)

### Developer
- 🏗️ [Architecture Overview](docs/architecture_overview.md)
- 🤝 [Contributing Guide](CONTRIBUTING.md)
- 🧪 [Testing Guide](docs/development.md)

---

## 🤝 Contributing

Contributions welcome! See [Contributing Guide](CONTRIBUTING.md) for:

- Development setup & local CI (`make ci`)
- Code quality standards & testing
- Pull request guidelines
- How to add device support

**Ways to help:**
- 🧪 Test with real hardware (D1 phase modes, J1 calibration)
- 📝 Improve documentation
- 🌐 Add translations
- 🐛 Report bugs with detailed logs

---

## ⚖️ Legal

> [!IMPORTANT]
> **This integration is not affiliated with, endorsed by, or sponsored by Ubisys Elektronik GmbH.**
>
> All Ubisys trademarks, logos, and brand assets are the intellectual property of Ubisys Elektronik GmbH. This is an independent, community-developed integration provided "as-is" without warranty.

---

## 📝 License

MIT License - see [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- Home Assistant community
- ZHA integration maintainers
- Ubisys Elektronik GmbH for excellent Zigbee devices

---

## 📞 Support

- 🐛 **Issues:** [GitHub Issues](https://github.com/jihlenburg/homeassistant-ubisys/issues)
- 💬 **Discussions:** [GitHub Discussions](https://github.com/jihlenburg/homeassistant-ubisys/discussions)
- 🏠 **Community:** [Home Assistant Forum](https://community.home-assistant.io/)

---

<div align="center">

**Made with ❤️ for the Home Assistant community**

[⬆ Back to top](#ubisys-zigbee-devices-for-home-assistant)

</div>
