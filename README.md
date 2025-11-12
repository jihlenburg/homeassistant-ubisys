# Ubisys Zigbee Devices for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)
[![Version](https://img.shields.io/badge/version-1.2.0-blue.svg)](https://github.com/jihlenburg/homeassistant-ubisys)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

A complete Home Assistant integration for Ubisys Zigbee devices, providing enhanced support for window covering controllers (J1) and universal dimmers (D1) with custom ZHA quirks, auto-discovery, smart feature filtering, automated calibration, and manufacturer-specific configuration services.

---

## 🎯 At a Glance

### The Problem

Home Assistant's default ZHA integration shows **all** window covering controls for every blind, regardless of type:
- **Roller shades** get confusing tilt controls (they don't tilt!)
- **Venetian blinds** show tilt controls, but you have to know they exist
- **No guidance** on which controls work for your specific shade type

### The Solution

This integration **filters controls** based on your actual shade type:

| Shade Type | Position Control | Tilt Control | What You See |
|------------|------------------|--------------|--------------|
| Roller / Cellular / Vertical | ✅ | ❌ | Open, Close, Stop, Position slider |
| Venetian (interior/exterior) | ✅ | ✅ | Position slider + Tilt slider |

**Plus**: One-click calibration button, auto-discovery, and smart feature filtering.

### Quick Comparison

**Without this integration** (plain ZHA):
```
🔹 Roller Shade Entity
   Controls: Open, Close, Stop, Position, Tilt ← Confusing!
   Calibration: Manual YAML configuration required
```

**With this integration**:
```
🟢 Roller Shade Entity
   Controls: Open, Close, Stop, Position ← Only relevant controls!
   Calibration: Click "Calibrate" button ← Easy!
   Shade Type: Visible in entity attributes
```

---

## ✨ Features

- 🔍 **Auto-Discovery** - Automatically detects J1 devices when paired with ZHA (v1.1+)
- 🔌 **Custom ZHA Quirks** - Access manufacturer-specific attributes (total steps, tilt transition steps, configured mode)
- 🎯 **Smart Feature Filtering** - Only show controls that match your shade type configuration
- 🎚️ **Shade Type Support** - Roller, cellular, vertical blinds, venetian blinds, and exterior venetian blinds
- 🔧 **Automated Calibration** - One-click calibration button on device page
- 🏗️ **Config Flow** - Easy setup through the Home Assistant UI with guided shade type selection
- 📦 **HACS Compatible** - Simple installation and automatic updates
- 🔄 **State Synchronization** - Real-time updates from the underlying ZHA entity
- 🎛️ **Single Entity UX** - See one cover entity per device (ZHA entity auto-hidden)
 - 🪪 **Logbook & Diagnostics** - Friendly logbook entries; diagnostics expose redacted device + endpoint/cluster info
 - 🛠️ **Repairs** - Actionable issues when clusters/quirks are missing
 - 🔇 **Quiet by Default** - Options to enable verbose INFO logs and per-event input logging

## 🎛️ Supported Devices

### Currently Supported

| Device | Type | HA Platform | Status | Features |
|--------|------|-------------|--------|----------|
| **J1** | Window Covering Controller | `cover` | ✅ **Fully Supported** | Position, Tilt, Calibration |
| **J1-R** | Window Covering (DIN Rail) | `cover` | ✅ **Fully Supported** | Position, Tilt, Calibration |
| **D1** | Universal Dimmer | `light` | ✅ **Supported** | Phase Control, Ballast Config |
| **D1-R** | Universal Dimmer (DIN Rail) | `light` | ✅ **Supported** | Phase Control, Ballast Config |

### Roadmap (Planned)

| Device | Type | HA Platform | Status | Notes |
|--------|------|-------------|--------|-------|
| **S1** | Power Switch (16A) | `switch` | 📋 **Planned** | Config Flow UI exists, quirk/platform pending |
| **S1-R** | Power Switch (DIN Rail) | `switch` | 📋 **Planned** | Config Flow UI exists, quirk/platform pending |
| **S2** | Dual Power Switch (500W×2) | `switch` | 📋 **Planned** | Not yet started |
| **S2-R** | Dual Power Switch (DIN Rail) | `switch` | 📋 **Planned** | Not yet started |

> **Note:** This integration fully supports Ubisys window covering devices (J1/J1-R) and universal dimmers (D1/D1-R). Switch support (S1/S2) is partially implemented (config flow UI ready) but requires quirk and platform completion. See [Known Limitations](#️-known-limitations--open-items) for details.

### J1/J1-R Shade Types

| Type | Features | WindowCoveringType |
|------|----------|-------------------|
| Roller Shade | Open, Close, Stop, Set Position | 0x00 |
| Cellular Shade | Open, Close, Stop, Set Position | 0x00 |
| Vertical Blind | Open, Close, Stop, Set Position | 0x04 |
| Venetian Blind | Position + Tilt controls | 0x08 |
| Exterior Venetian | Position + Tilt controls | 0x08 |

## ⚠️ Known Limitations & Open Items

### 🚧 Device Support Gaps

- **S1/S1-R Power Switch** - Wrapper platform exists; advanced features and quirks are still evolving
- **S2/S2-R Dual Power Switch** - Planned but not implemented
  - Not included in `SWITCH_MODELS` constant
  - No platform or quirk support
  
  - Reason: Requires real D1 hardware testing to understand DeviceSetup cluster format
  - Workaround: Default input configuration works for most users
  - Status: Phase 3 feature blocked pending hardware testing

### 🔬 Hardware Validation Needed

The following features exist but **require real hardware testing** for validation:

- **D1 Phase Mode Configuration** - Service works but needs validation with real device
- **D1 Ballast Manufacturer Attributes** - May have undocumented manufacturer-specific attributes
- **J1 Calibration** - Full 5-phase stall detection tested but needs more real-world validation

### 📋 Planned Features (Roadmap)

**Input Monitoring Enhancements:**
- Event entities for button presses (show last press in dashboard)
- Binary sensors for stationary rocker switches
- Scene-only mode (buttons trigger automations without controlling device)

**J1 Window Covering:**
- Scene support for preset positions (save/recall specific positions)
- Position offset configuration (adjust reporting to match physical reality)
- Speed control configuration (adjust motor speed)
- Web-based calibration wizard (interactive step-by-step guide)

**Energy Monitoring:**
- Energy metering dashboard for S1/D1 devices (leverage 0.5% accuracy power monitoring)
- Integration with Home Assistant Energy dashboard

**Developer Experience:**
- Unit test suite (config flow, feature filtering, service validation)
- Integration test suite (auto-discovery, entity creation, state sync)
- Manual testing documentation (`docs/testing.md`)

**Localization:**
- Multi-language support (currently English only)

### 📝 Documentation Gaps

- **S2/S2-R Configuration Guide** - Blocked until device support implemented
- **Manual Testing Procedures** - No structured testing checklist for contributors
- **Translations** - No translation files for non-English languages

### 💡 Architectural Notes

- **J1 Unused Attributes** - Technical reference documents attributes `0x1003` (LiftToTiltTransitionSteps2) and `0x1004` (TotalSteps2) which are not currently used by integration (existing calibration approach works well)
- **Button→Service Pattern** - Calibration button delegates to service for flexibility (both UI and automation access)
- **Wrapper Entity Architecture** - Entities delegate to ZHA rather than talking directly to Zigbee (leverages ZHA's excellent communication layer)

### 🔧 How You Can Help

- **Hardware Testing**: If you have D1/D1-R devices, help validate phase mode and input configuration
- **S1/S1-R/S2/S2-R Implementation**: Contribute switch platform support
- **Test Suite**: Add unit and integration tests
- **Documentation**: Translate to other languages, add testing guides
- **Bug Reports**: File issues at https://github.com/jihlenburg/homeassistant-ubisys/issues

---

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
- Create all required directories (`custom_components`, `custom_zha_quirks`)
- Download all integration files from GitHub
- Install ZHA quirk for manufacturer-specific attributes
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
4. Add to `configuration.yaml`:

```yaml
zha:
  custom_quirks_path: custom_zha_quirks
```

5. Restart Home Assistant

## 🚀 Quick Start

Prefer a concise, click‑by‑click guide? See docs/getting_started.md.
Device trigger examples: docs/device_triggers_examples.md.

For logging controls and best practices, see docs/logging.md.

### 1. Pair Your Device with ZHA

Pair your Ubisys J1 with ZHA:

1. Go to **Settings** → **Devices & Services** → **ZHA**
2. Click **Add Device**
3. Put your J1 into pairing mode (hold the pairing button)
4. Wait for ZHA to discover the device

### 2. Configure via Auto-Discovery (v1.1+)

**The integration will automatically detect your J1!**

After pairing with ZHA, a configuration notification will appear:

1. Click the notification or go to **Settings** → **Devices & Services**
2. Look for "Ubisys J1" in discovered integrations
3. Click **Configure**
4. Select your shade type:
   - **Roller Shade** - Standard roller blinds (position only)
   - **Cellular Shade** - Honeycomb/cellular blinds (position only)
   - **Vertical Blind** - Vertical slat blinds (position only)
   - **Venetian Blind** - Indoor horizontal slat blinds (position + tilt)
   - **Exterior Venetian Blind** - Outdoor horizontal slat blinds (position + tilt)
5. Click **Submit**

**Result:** You'll see one cover entity with the correct features. The original ZHA entity is automatically hidden to prevent duplicates.

### 3. Calibrate Your Device

Run the calibration service to set up accurate position tracking.

**Via Calibration Button (Easiest):**

After adding the integration, you'll see a **Calibrate** button entity attached to your device:

1. Go to the device page (Configuration → Devices → Your Ubisys J1)
2. Click the **Calibrate** button
3. The shade will automatically run through the calibration sequence

**Or via Services:**

```yaml
service: ubisys.calibrate_j1
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
      - service: ubisys.calibrate_j1
        data:
          entity_id: cover.bedroom_shade
```

## 🔧 Calibration Process

The enhanced calibration service uses **motor stall detection** to automatically find the physical limits of your blind. No matter where the blind starts, calibration will work correctly.

### Calibration Steps

1. **Enter Calibration Mode** - Device enters special calibration mode
2. **Find Top Limit** - Moves UP until motor stalls at fully open position
3. **Find Bottom Limit** - Moves DOWN until motor stalls at fully closed position
4. **Measure Total Steps** - Device auto-calculates travel distance
5. **Verification** - Returns to top to confirm calibration
6. **Configure Device** - Writes tilt settings based on shade type
7. **Exit Calibration Mode** - Returns to normal operation

### What You'll See

During calibration (60-120 seconds):
- The blind moves to fully open (motor stalls at top)
- Brief pause
- The blind moves to fully closed (motor stalls at bottom)
- Brief pause
- The blind returns to fully open (verification)
- Calibration complete!

**Important**: The blind will automatically find its limits regardless of starting position. Motor stall detection ensures precise calibration.

### Expected Duration
- **Roller/Cellular/Vertical**: 60-90 seconds
- **Venetian Blinds**: 90-120 seconds

Check logs for detailed calibration progress and results.

## 💡 D1 Universal Dimmer Configuration

The D1/D1-R universal dimmers require configuration to work optimally with different load types (incandescent, halogen, LED). This integration provides three configuration services:

### Phase Control Mode Configuration

Configure how the dimmer reduces voltage to the load (critical for LED compatibility):

**Available Modes:**
- `automatic` - Auto-detect load type (default, recommended starting point)
- `forward` - Leading edge dimming (for incandescent, halogen)
- `reverse` - Trailing edge dimming (for LED lamps)

**Important:** The dimmer output MUST be OFF to change the phase mode.

**Example:**
```yaml
# Turn off light first
service: light.turn_off
target:
  entity_id: light.kitchen_dimmer

# Configure phase mode
service: ubisys.configure_d1_phase_mode
data:
  entity_id: light.kitchen_dimmer
  phase_mode: reverse  # For LED lamps
```

### Ballast Configuration

Fine-tune the minimum and maximum brightness levels to prevent LED flickering:

**Example:**
```yaml
# Set minimum level to prevent flickering at low brightness
service: ubisys.configure_d1_ballast
data:
  entity_id: light.kitchen_dimmer
  min_level: 15      # Range: 1-254 (typical: 10-20 for LEDs)
  max_level: 254     # Range: 1-254 (default: 254)
```

### When to Configure

- **LEDs flickering at low brightness?** Try `phase_mode: reverse` and increase `min_level`
- **Buzzing from dimmer/transformer?** Try switching between `forward` and `reverse` phase modes
- **Limited dimming range?** Adjust `min_level` and try different phase modes
- **New LED installation?** Start with `automatic` mode, adjust only if needed

### Complete D1 Setup Example

```yaml
# 1. Turn off the light
service: light.turn_off
target:
  entity_id: light.living_room_dimmer

# 2. Configure phase mode for LED compatibility
service: ubisys.configure_d1_phase_mode
data:
  entity_id: light.living_room_dimmer
  phase_mode: reverse

# 3. Set ballast levels to prevent flickering
service: ubisys.configure_d1_ballast
data:
  entity_id: light.living_room_dimmer
  min_level: 15
  max_level: 254
```

For detailed configuration instructions, troubleshooting, and load type reference, see the [D1 Configuration Guide](docs/d1_configuration.md).

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
      service: ubisys.calibrate_j1
      service_data:
        entity_id: cover.bedroom_shade
```

## 🔄 Viewing and Changing Shade Type

### View Current Configuration

The cover entity displays the configured shade type as an attribute:

1. Go to **Developer Tools** → **States**
2. Find your Ubisys cover entity (e.g., `cover.bedroom_shade`)
3. Check the **Attributes** section for `shade_type`

You can also see it in the device info or by clicking on the entity card.

### Change Shade Type

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

1. Run the calibration service: `ubisys.calibrate_j1` or click the Calibrate button
2. Make sure the shade can move freely (no obstructions)
3. **No need to position the blind** - calibration automatically finds limits via motor stall detection

### Tilt controls don't appear

1. Check that you selected a venetian blind shade type
2. Reconfigure the integration and select the correct type
3. Restart Home Assistant

### Calibration fails

1. Ensure the shade has power and is responsive to basic commands
2. Check Home Assistant logs for error details
3. Manually test open/close commands through ZHA first
4. Verify the device is properly paired and accessible

### Integration not showing in UI

1. Verify files are in `custom_components/ubisys/`
2. Check `configuration.yaml` for the ZHA quirks path
3. Restart Home Assistant
4. Check logs: `grep -i ubisys home-assistant.log`

## 📚 Advanced Configuration

See docs/advanced_zha_access.md for direct ZHA cluster access examples and cautions.

## 🏗️ Development

### Project Structure

```
homeassistant-ubisys/
├── custom_components/ubisys/     # Main integration
│   ├── __init__.py              # Setup, discovery, and service registration
│   ├── button.py                # Calibration button platform
│   ├── j1_calibration.py        # J1 calibration module
│   ├── config_flow.py           # Configuration UI with auto-discovery
│   ├── const.py                 # Constants and mappings
│   ├── cover.py                 # Wrapper cover platform
│   ├── manifest.json            # Integration metadata
│   ├── services.yaml            # Service definitions
│   ├── strings.json             # UI strings
│   └── translations/
│       └── en.json              # English translations
├── custom_zha_quirks/
│   └── ubisys_j1.py             # ZHA quirk for J1
├── docs/                        # Documentation
├── install.sh                   # Installation script
└── README.md                    # This file
```

### Testing & Local CI

Use our local CI runner (creates .venv, installs deps, runs lint/type/tests):

```bash
# Full local CI
make ci

# Auto-fix formatting
make fmt

# After bootstrapping
make lint
make typecheck
make test
```

GitHub Actions runs hassfest/HACS + lint/type/tests (HA 2024.1.*).

Device trigger examples: see docs/device_triggers_examples.md.

### Logging Controls

Options → Configure includes:
- Verbose info logging (lifecycle/setup at INFO)
- Verbose input event logging (each event at INFO)

See docs/logging.md for patterns (kv/info_banner) and HA logger config.

### Diagnostics & Logbook

- Diagnostics: redacted config, device info, ZHA endpoints/clusters, last calibration results
- Logbook: user-friendly entries for input events and calibration completion

### Options “About” Page

Options now starts with a menu: “About” (links to docs/issues) or “Configure”.

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

### Device Support
- [x] **J1** - Window covering controller ✅ v1.1.1
- [x] **J1-R** - DIN rail variant ✅ v1.1.1
- [x] **D1** - Universal dimmer ✅ v2.0.0
- [x] **D1-R** - Universal dimmer (DIN rail) ✅ v2.0.0
- [ ] **S1/S1-R** - Power switch (16A with energy metering)
- [ ] **S2/S2-R** - Dual power switch (500W×2)

### Features
- [x] Phase control mode configuration (D1) ✅ v2.0.0
- [x] Ballast configuration (D1) ✅ v2.0.0
- [ ] Input configuration (D1) - Planned Phase 3
- [ ] Energy metering dashboard (S1/D1 devices)
- [ ] Scene support for preset positions (J1)
- [ ] Position offset configuration (J1)
- [ ] Speed control configuration (J1)
- [ ] Web-based calibration wizard (J1)
- [ ] Multi-language support

### Documentation
- [x] Architecture overview ✅ v1.1.1
- [x] Window covering architecture ✅ v1.1.1
- [x] D1 dimmer configuration guide ✅ v2.0.0
- [ ] S1/S2 switch integration guide

See [Architecture Overview](docs/architecture_overview.md) for detailed integration design and extensibility.

---

**Made with ❤️ for the Home Assistant community**
## ℹ️ S1/S1‑R Support

- The integration provides a wrapper switch entity for S1/S1‑R and exposes input presets via the Options Flow.
- Metering is handled by ZHA (standard sensors). Advanced physical input behaviors are configured via presets.

See Options → “Configure Physical Inputs”.
## 🧪 Diagnostics & Tuning

- Last Input Event Sensor: Each device now exposes a “Last Input Event” sensor that updates on every physical button press and keeps a small rolling history in attributes.
- J1 Advanced Tuning: Configure guard time, inactive power threshold, startup steps, and additional steps via Options (Shade + Tuning) or the `ubisys.tune_j1_advanced` service. See docs/advanced_j1_tuning.md.
- Test Mode: The calibration service `ubisys.calibrate_j1` accepts `test_mode: true` to perform a read‑only health check without entering calibration.
