# Ubisys Zigbee Devices Integration

**Compatibility:** Home Assistant 2024.1+ (Python 3.11+)

**Documentation:** [Index](index.md) · [Troubleshooting](troubleshooting.md)

This integration brings advanced control and configuration capabilities to Ubisys Zigbee devices in Home Assistant through the ZHA integration.

## Introduction

The Ubisys integration enhances ZHA's support for Ubisys devices by:

- **Smart Feature Filtering**: J1 window covering entities show only relevant controls based on configured shade type (position-only vs. position+tilt)
- **One-Click Calibration**: Automated J1 calibration with motor stall detection
- **Advanced Configuration**: D1 dimmer phase control and ballast configuration for optimal LED compatibility
- **Physical Input Monitoring**: Track button presses and rocker switches for device triggers and automations
- **Preset-Based Setup**: UI-driven configuration with automatic verification and rollback

### Use Cases

- **Window Coverings (J1/J1-R)**: Control roller shades, cellular shades, vertical blinds, and venetian blinds with accurate position tracking
- **Dimming (D1/D1-R)**: Universal dimmer for LEDs, incandescent, and halogen lights with flicker-free operation
- **Switching (S1/S1-R)**: Power switches with physical input configuration and metering support
- **Automation**: Device triggers for physical button presses (short, long, double-press patterns)

## Supported Devices

| Model  | Type | Platform | Features | Status |
|--------|------|----------|----------|--------|
| **J1** | Window Covering (flush) | `cover` | Position, Tilt, Calibration, Inputs | ✅ Fully supported |
| **J1-R** | Window Covering (DIN) | `cover` | Position, Tilt, Calibration, Inputs | ✅ Fully supported |
| **D1** | Universal Dimmer (flush) | `light` | Dimming, Phase/Ballast Config, Inputs | ✅ Supported |
| **D1-R** | Universal Dimmer (DIN) | `light` | Dimming, Phase/Ballast Config, Inputs | ✅ Supported |
| **S1** | Power Switch (flush) | `switch` | Switching, Input Config, Metering | ⚙️ Evolving |
| **S1-R** | Power Switch (DIN) | `switch` | Switching, Input Config, Metering | ⚙️ Evolving |

### Shade Type Support (J1)

The J1 integration filters cover features based on your configured shade type:

- **Roller Shade**: Position control only
- **Cellular Shade**: Position control only
- **Vertical Blind**: Position control only
- **Venetian Blind**: Position + tilt control
- **Exterior Venetian Blind**: Position + tilt control

### Controller Endpoints (Physical Inputs)

Physical button/rocker inputs are available for automations:

- **J1/J1-R**: 1 input (EP2)
- **D1/D1-R**: 2 inputs (EP2, EP3)
- **S1**: 1 input (EP2)
- **S1-R**: 2 inputs (EP2, EP3)

## Prerequisites

Before installing this integration, ensure you have:

1. ✅ **Home Assistant 2024.1.0 or newer**
2. ✅ **ZHA integration** installed and configured
3. ✅ **Zigbee coordinator** paired and operational
4. ✅ **Ubisys device(s)** paired with ZHA

> **Note**: This integration works alongside ZHA. Your Ubisys devices must first be paired with ZHA before configuring this integration.

## Installation

### Method 1: HACS (Recommended)

1. **Open HACS** in Home Assistant
   - Navigate to **HACS** in the sidebar

2. **Add Custom Repository**
   - Click **⋮** menu (top right)
   - Select **Custom repositories**
   - Add repository URL: `https://github.com/jihlenburg/homeassistant-ubisys`
   - Category: **Integration**
   - Click **Add**

3. **Install Integration**
   - Search for "Ubisys Zigbee Devices"
   - Click **Download**
   - Select the latest version

4. **Restart Home Assistant**
   - Go to **Settings** → **System** → **Restart**

### Method 2: One-Line Installer

For advanced users, use the automated installer:

```bash
curl -sSL https://raw.githubusercontent.com/jihlenburg/homeassistant-ubisys/main/install.sh | bash
```

This script:
- Creates required directories
- Downloads integration files
- Installs ZHA quirks
- Updates `configuration.yaml`
- Validates configuration

### Method 3: Manual Installation

1. **Download** the latest release from GitHub
2. **Copy files** to your Home Assistant config directory:
   ```bash
   cp -r custom_components/ubisys /config/custom_components/
   cp custom_zha_quirks/*.py /config/custom_zha_quirks/
   ```

3. **Update** `configuration.yaml`:
   ```yaml
   zha:
     custom_quirks_path: custom_zha_quirks
   ```

4. **Restart** Home Assistant

### Verification

Check that the integration loaded successfully:

1. **Via UI**: Settings → Devices & Services → Add Integration → Search "Ubisys"
2. **Via Logs**:
   ```bash
   grep -i "ubisys" /config/home-assistant.log
   ```

You should see:
```
Successfully imported custom quirk ubisys_j1
Successfully imported custom quirk ubisys_d1
Successfully imported custom quirk ubisys_s1
Setup of domain ubisys took X seconds
```

## Configuration

This integration uses **UI-based configuration** (Config Flow). No YAML configuration required.

### Initial Setup

1. **Pair Device with ZHA** (if not already done)
   - Go to **Settings** → **Devices & Services** → **ZHA** → **Add Device**
   - Put your Ubisys device into pairing mode
   - Wait for discovery to complete

2. **Configure Ubisys Integration**
   - Navigate to **Settings** → **Devices & Services** → **Ubisys** → [Your Device] → **Configure**
   - Follow the device-specific setup:

#### J1/J1-R Window Covering Setup

1. Select your **shade type** from the dropdown:
   - Roller Shade
   - Cellular Shade
   - Vertical Blind
   - Venetian Blind
   - Exterior Venetian Blind

2. The integration creates a wrapper entity with appropriate features
3. Run calibration (see [Calibration](#j1-calibration) section)

#### D1/D1-R Universal Dimmer Setup

1. Configure **phase control mode**:
   - Automatic (default, recommended)
   - Forward (for incandescent/halogen)
   - Reverse (for LEDs)

2. Set **ballast levels** if needed:
   - Min level (1-254): Prevents LED flickering at low brightness
   - Max level (1-254): Limits maximum brightness

3. Configure **physical inputs** (optional):
   - Choose preset behavior for wall switches

See [D1 Configuration](devices/d1_universal_dimmer.md) for detailed guidance.

#### S1/S1-R Power Switch Setup

1. Configure **physical inputs** via preset options:
   - Toggle
   - On only / Off only
   - Rocker (On/Off pair)

See [S1 Configuration](devices/s1_power_switch.md) for details.

## Configuration Options

Access configuration options via:
**Settings** → **Devices & Services** → **Ubisys** → [Your Device] → **Configure**

### Options Menu

- **About**: Links to documentation and issue tracker
- **Configure**: Device-specific settings and logging controls

### Common Options (All Devices)

- **Verbose Info Logging**: Enable INFO-level logs for lifecycle events
- **Verbose Input Event Logging**: Enable per-event logging for physical inputs

### J1-Specific Options

- **Shade Type**: Change configured shade type (requires recalibration)
- **J1 Advanced**: Tune manufacturer-specific attributes
  - Turnaround guard time
  - Inactive power threshold
  - Startup steps
  - Additional steps (overtravel)

### D1-Specific Options

- **Phase Control Mode**: automatic | forward | reverse
- **Ballast Configuration**: Min/max brightness levels
- **Input Configuration**: Physical switch presets

### S1-Specific Options

- **Input Configuration**: Physical switch presets

## Supported Functionality

### Entities Created

This integration creates the following entities:

#### J1 Window Covering

- **Cover Entity**: `cover.<device_name>`
  - Features filtered based on shade type
  - State: open, closed, opening, closing
  - Attributes: current_position, current_tilt_position (if applicable)

- **Calibration Button**: `button.<device_name>_calibrate`
  - One-click calibration trigger

- **Last Input Event Sensor**: `sensor.<device_name>_last_input_event`
  - Shows last physical button press

#### D1 Universal Dimmer

- **Light Entity**: `light.<device_name>`
  - Standard dimming controls
  - Brightness 0-255

- **Last Input Event Sensor**: `sensor.<device_name>_last_input_event`

#### S1 Power Switch

- **Switch Entity**: `switch.<device_name>`
  - Standard on/off controls

- **Last Input Event Sensor**: `sensor.<device_name>_last_input_event`

### Services

The integration provides these services:

#### `ubisys.calibrate_j1`

Run automated calibration for J1 window coverings. You can target a single cover
or select multiple Ubisys covers; the integration calibrates them sequentially
so each device has exclusive access to the Zigbee radio.

**Fields:**
- `entity_id` (required): One **or more** Ubisys cover entities
- `test_mode` (optional): Read-only health check (no movement)

**Example:**
```yaml
service: ubisys.calibrate_j1
data:
  entity_id:
    - cover.bedroom_shade
    - cover.office_shade
```

#### `ubisys.tune_j1_advanced`

Configure advanced J1 manufacturer attributes.

**Fields:**
- `entity_id` (required): Ubisys cover entity
- `turnaround_guard_time` (optional): 0-65535 (50ms units)
- `inactive_power_threshold` (optional): 0-65535 (mW)
- `startup_steps` (optional): 0-65535
- `additional_steps` (optional): 0-100 (%)

**Example:**
```yaml
service: ubisys.tune_j1_advanced
data:
  entity_id: cover.bedroom_shade
  turnaround_guard_time: 10  # 500ms
  inactive_power_threshold: 4096  # 4.1W
```

#### `ubisys.configure_d1_phase_mode`

Set D1 dimmer phase control mode. Multiple Ubisys lights can be configured in a
single call; the integration handles them sequentially and applies per-device
locks to prevent overlapping writes.

**Fields:**
- `entity_id` (required): One or more Ubisys light entities
- `phase_mode` (required): `automatic` | `forward` | `reverse`

**Important**: Light must be OFF before changing phase mode.

**Example:**
```yaml
service: ubisys.configure_d1_phase_mode
data:
  entity_id:
    - light.kitchen_dimmer
    - light.office_dimmer
  phase_mode: reverse  # For LEDs
```

#### `ubisys.configure_d1_ballast`

Set D1 dimmer ballast min/max levels. Multiple lights can be provided; they are
processed sequentially to maintain Zigbee stability.

**Fields:**
- `entity_id` (required): One or more Ubisys light entities
- `min_level` (optional): 1-254
- `max_level` (optional): 1-254

**Example:**
```yaml
service: ubisys.configure_d1_ballast
data:
  entity_id:
    - light.kitchen_dimmer
  min_level: 15  # Prevent flickering
  max_level: 254
```

### Events

#### `ubisys_input_event`

Fired when physical input (button/rocker) is activated.

**Data:**
- `device_ieee`: Device IEEE address
- `device_id`: Home Assistant device ID
- `model`: Device model (J1, D1, S1)
- `input_number`: Input number (0-based)
- `press_type`: `pressed` | `released` | `short_press` | `long_press` | `double_press`
- `command`: Command details (endpoint, cluster, command)

**Example Automation:**
```yaml
automation:
  - alias: "Toggle light on short press"
    trigger:
      - platform: event
        event_type: ubisys_input_event
        event_data:
          device_ieee: "00:12:4b:00:xx:xx:xx:xx"
          input_number: 0
          press_type: short_press
    action:
      - service: light.toggle
        target:
          entity_id: light.living_room
```

#### Calibration Events

- `ubisys_calibration_complete`: Fired on successful J1 calibration
- `ubisys_calibration_failed`: Fired on calibration failure

### Device Triggers

Device triggers are available in the automation UI for all Ubisys devices with physical inputs.

**Available Triggers:**
- Button N pressed
- Button N released
- Button N short press
- Button N long press
- Button N double press

**Example:**
1. Automation → Add Trigger → Device
2. Select your Ubisys device
3. Choose trigger type (e.g., "Button 1 short press")

See the [Examples](#examples) section for detailed automation examples.

## J1 Calibration

Calibration is required for accurate position tracking on J1 window coverings.

### When to Calibrate

- ✅ After initial installation
- ✅ After changing shade type
- ✅ After mechanical changes (mounting, tension, fabric)
- ✅ If positions become inaccurate
- ✅ After power loss (rare cases)

### Calibration Methods

**Method 1: Via Button Entity**

Click the calibration button entity in Home Assistant UI:
`button.<device_name>_calibrate`

**Method 2: Via Service Call**

```yaml
service: ubisys.calibrate_j1
data:
  entity_id: cover.bedroom_shade
```

**Method 3: Via Automation**

```yaml
automation:
  - alias: "Calibrate on Restart"
    trigger:
      - platform: homeassistant
        event: start
    action:
      - delay: "00:00:30"  # Wait for ZHA
      - service: ubisys.calibrate_j1
        data:
          entity_id: cover.bedroom_shade
```

### How Calibration Works

The integration uses a 5-phase automated calibration process with motor stall detection:

1. **Set Window Covering Type**: Configures shade type attribute
2. **Move to Fully Open**: Detects top limit via stall detection
3. **Reset Position Counter**: Zeros position at top
4. **Move to Fully Closed**: Counts steps while moving down
5. **Read Total Steps**: Retrieves and stores step count

**Duration**: 30-90 seconds depending on shade size

### Typical Step Counts

| Shade Size | Expected Range |
|------------|----------------|
| Small (< 3 ft) | 2000-3500 steps |
| Medium (3-6 ft) | 3500-5000 steps |
| Large (6-9 ft) | 5000-7500 steps |
| Extra Large (> 9 ft) | 7500-12000 steps |

For complete calibration documentation, see [J1 Window Covering Guide](devices/j1_window_covering.md).

## Examples

### Basic Window Covering Control

```yaml
# Open completely
service: cover.open_cover
target:
  entity_id: cover.bedroom_shade

# Set to 50% open
service: cover.set_cover_position
target:
  entity_id: cover.bedroom_shade
data:
  position: 50

# Set tilt (venetian blinds only)
service: cover.set_cover_tilt_position
target:
  entity_id: cover.south_window_venetian
data:
  tilt_position: 75
```

### Basic Dimmer Control

```yaml
# Turn on at 50% brightness
service: light.turn_on
target:
  entity_id: light.living_room_dimmer
data:
  brightness_pct: 50

# Dim to 25% over 3 seconds
service: light.turn_on
target:
  entity_id: light.living_room_dimmer
data:
  brightness_pct: 25
  transition: 3
```

### Morning Routine Automation

```yaml
automation:
  - alias: "Morning - Open Shades at Sunrise"
    trigger:
      - platform: sun
        event: sunrise
        offset: "00:30:00"
    condition:
      - condition: state
        entity_id: binary_sensor.workday
        state: "on"
    action:
      - service: cover.open_cover
        target:
          entity_id: cover.bedroom_shade
```

### Sun Protection

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
      - service: cover.set_cover_position
        target:
          entity_id: cover.south_window
        data:
          position: 10  # Nearly closed
```

### Device Trigger Example

```yaml
automation:
  - alias: "Button 1 Short Press - Set 50%"
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

### D1 LED Configuration

```yaml
# Configure for LED compatibility
script:
  setup_led_dimmer:
    sequence:
      # Turn off first (required for phase mode)
      - service: light.turn_off
        target:
          entity_id: light.kitchen_dimmer
      - delay: "00:00:05"

      # Set reverse phase for LEDs
      - service: ubisys.configure_d1_phase_mode
        data:
          entity_id: light.kitchen_dimmer
          phase_mode: reverse

      # Set min level to prevent flickering
      - service: ubisys.configure_d1_ballast
        data:
          entity_id: light.kitchen_dimmer
          min_level: 15
          max_level: 254
```

For more examples, see the device-specific guides:
- [J1 Window Covering](devices/j1_window_covering.md)
- [D1 Universal Dimmer](devices/d1_universal_dimmer.md)
- [S1 Power Switch](devices/s1_power_switch.md)

## Data Updates

### State Synchronization

This integration creates **wrapper entities** that synchronize with underlying ZHA entities:

- State changes are monitored via event listeners
- Updates are immediate (event-driven, not polled)
- All commands are delegated to ZHA entities
- `should_poll = False` (no polling overhead)

### Refresh Behavior

- **Cover Position**: Updated in real-time as device reports changes
- **Light Brightness**: Updated immediately on state changes
- **Switch State**: Updated immediately on state changes
- **Input Events**: Fired in real-time as buttons are pressed

### Calibration Persistence

J1 calibration data is stored in device non-volatile memory and persists across:
- ✅ Home Assistant restarts
- ✅ ZHA integration reloads
- ✅ Power outages
- ✅ Zigbee network resets

D1 phase and ballast configuration is also persistent.

## Known Limitations

### General

- **Requires ZHA**: This integration enhances ZHA. Zigbee2MQTT users should use Z2M's native Ubisys support
- **No Direct Zigbee Access**: Integration delegates all commands to ZHA (by design)
- **Config Flow Only**: No YAML configuration support (follows HA standards)

### J1 Window Covering

- **Calibration Required**: Position tracking requires one-time calibration
- **Stall Detection**: Relies on 3-second position stability to detect limits
- **Shade Type Change**: Requires recalibration when shade type is changed
- **No Auto-Calibration**: Calibration must be manually triggered

### D1 Universal Dimmer

- **Phase Mode Constraint**: Light must be OFF to change phase control mode
- **LED Compatibility**: Not all LEDs support dimming; results vary by brand
- **No Load Detection**: Cannot automatically detect incompatible loads
- **Ballast Range**: Min level cannot be lower than LED driver threshold

### S1 Power Switch

- **Evolving Support**: Input configuration and advanced features still in development
- **Metering**: Power/energy sensors provided by ZHA, not this integration

### Physical Input Monitoring

- **Observation Only**: Integration observes commands, doesn't replace device behavior
- **Command Correlation**: Relies on InputActions micro-code parsing
- **Configuration Persistence**: InputActions configuration stored in device (survives restarts)

## Troubleshooting

For troubleshooting help, see the comprehensive [Troubleshooting Guide](troubleshooting.md).

### Quick Troubleshooting

**Integration Not Loading**
```bash
# Check logs
grep -i "ubisys\|error" /config/home-assistant.log

# Verify file permissions
ls -la /config/custom_components/ubisys/
```

**ZHA Quirk Not Loading**
- Verify `custom_quirks_path: custom_zha_quirks` in `configuration.yaml`
- Restart ZHA integration: Settings → Devices & Services → ZHA → Reload

**J1 Cover Entity Missing Features**
- Check configured shade type in integration options
- Verify shade type matches your physical installation
- Reconfigure if needed

**D1 Phase Mode Configuration Fails**
- Ensure light is OFF before calling service
- Wait 5 seconds after turning off
- Check logs for detailed error messages

**Calibration Fails**
- Remove obstructions from shade path
- Check motor mounting and tension
- Verify Zigbee signal strength
- Review logs for specific error

**Physical Inputs Not Working**
- Enable "Verbose input event logging" to verify events
- Check that InputActions is configured (via Options)
- Verify controller endpoints are accessible

For detailed troubleshooting steps, see [troubleshooting.md](troubleshooting.md).

## Updating

### HACS Update

1. HACS will notify you when updates are available
2. Click **Update** → Select version → **Download**
3. Restart Home Assistant

### Manual Update

1. Download latest release from GitHub
2. Replace files in `/config/custom_components/ubisys/` and `/config/custom_zha_quirks/`
3. Restart Home Assistant

## Removing the Integration

### Step 1: Remove Config Entries

1. Go to **Settings** → **Devices & Services**
2. Find **Ubisys** integrations
3. Click **⋮** → **Delete**
4. Confirm deletion for each device

### Step 2: Remove Files

```bash
rm -rf /config/custom_components/ubisys
rm /config/custom_zha_quirks/ubisys*.py
```

### Step 3: Clean Configuration

Remove from `configuration.yaml` (if no other custom quirks):
```yaml
zha:
  custom_quirks_path: custom_zha_quirks  # Remove this line
```

### Step 4: Restart Home Assistant

```bash
ha core restart
```

## Related Documentation

- **Device Guides**:
  - [J1 Window Covering](devices/j1_window_covering.md)
  - [D1 Universal Dimmer](devices/d1_universal_dimmer.md)
  - [S1 Power Switch](devices/s1_power_switch.md)

- **Reference**:
  - [Troubleshooting](troubleshooting.md)
  - [Logging Controls](logging.md)

- **External Resources**:
  - [GitHub Repository](https://github.com/jihlenburg/homeassistant-ubisys)
  - [GitHub Issues](https://github.com/jihlenburg/homeassistant-ubisys/issues)
  - [Ubisys Technical Documentation](ubisys/)
  - [Home Assistant ZHA Documentation](https://www.home-assistant.io/integrations/zha/)

## Support

If you need help:

1. **Check Documentation**:
   - [Troubleshooting Guide](troubleshooting.md)
   - Device-specific guides (above)

2. **Review Logs**:
   ```bash
   tail -f /config/home-assistant.log | grep -i ubisys
   ```

3. **Get Help**:
   - [GitHub Issues](https://github.com/jihlenburg/homeassistant-ubisys/issues) - Bug reports
   - [GitHub Discussions](https://github.com/jihlenburg/homeassistant-ubisys/discussions) - Questions
   - [Home Assistant Community](https://community.home-assistant.io/) - General HA help

---

**Integration Version**: See `manifest.json`
**Home Assistant Requirement**: 2024.1.0+
**ZHA Requirement**: Latest stable version recommended
