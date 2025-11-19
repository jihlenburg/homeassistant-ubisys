# Ubisys D1 Universal Dimmer Configuration Guide

Compatibility: Home Assistant 2024.1+ (Python 3.11+)

Docs: [index](../index.md) · [user guide](../user_guide.md) · [troubleshooting](../troubleshooting.md)

This guide explains how to configure and optimize the Ubisys D1 universal dimmer for different load types.

## Overview

The Ubisys D1 is a universal dimmer that works with a wide variety of dimmable loads including:
- Incandescent bulbs (resistive loads)
- Halogen bulbs (resistive/inductive loads)
- LED lamps (capacitive loads)
- Low-voltage transformers (inductive loads)

To achieve optimal dimming performance and prevent flickering, buzzing, or damage, the D1 provides several configuration options that are not available through Home Assistant's standard light controls.

## Key Configuration Features

This integration exposes three manufacturer-specific configuration services:

1. **Phase Control Mode** - Critical for proper dimming behavior
2. **Ballast Configuration** - Fine-tune brightness range for LED compatibility
3. **Input Configuration** - Configure physical wall switches (planned Phase 3)

## Phase Control Mode Configuration

### What is Phase Control?

Phase control determines HOW the dimmer reduces voltage to the load:

- **Forward Phase Control (Leading Edge)**: Cuts power at the start of the AC waveform
  - Best for: Resistive and inductive loads
  - Compatible with: Incandescent, halogen, magnetic transformers
  - Also called: TRIAC dimming, "L" mode

- **Reverse Phase Control (Trailing Edge)**: Cuts power at the end of the AC waveform
  - Best for: Capacitive loads
  - Compatible with: LED lamps, electronic transformers
  - Also called: "C" or "R" mode

- **Automatic Mode**: The D1 automatically detects the load type
  - Default setting
  - Usually works well for most loads
  - Start with this unless you experience issues

### Why This Matters

⚠️ **CRITICAL**: Using the wrong phase control mode can cause:
- Visible flickering or strobing
- Audible buzzing or humming
- Reduced dimming range (can't dim below 30%)
- Premature LED failure
- Dimmer overheating or failure

### When to Configure Phase Mode

Configure phase control mode when:

- ✅ You experience flickering with LED lamps (try reverse phase)
- ✅ You hear buzzing from the dimmer or transformer (try switching modes)
- ✅ Dimming range is limited (can't go below 30-40%)
- ✅ LED manufacturer specifies a required dimming mode
- ✅ You're using low-voltage halogen with electronic transformers (try reverse phase)

**Always start with automatic mode first!** Only change if you experience issues.

### Configuration Service: configure_d1_phase_mode

You can target one or more Ubisys D1 lights in a single call. The service
processes them sequentially and applies per-device locks to prevent concurrent
cluster writes.

#### Important Constraint

⚠️ **The dimmer output MUST be OFF to change the phase mode.**

Turn off the light before calling this service. If the light is on, the configuration will fail with an error.

#### Service Parameters

| Parameter | Required | Type | Description |
|-----------|----------|------|-------------|
| `entity_id` | Yes | string or list | One or more D1 light entities (e.g., `light.kitchen_dimmer`) |
| `phase_mode` | Yes | string | One of: `automatic`, `forward`, `reverse` |

#### Examples

**Via Home Assistant UI:**

1. Navigate to **Developer Tools** → **Services**
2. Select service: `ubisys.configure_d1_phase_mode`
3. Choose your D1 entity from the dropdown
4. Select phase mode: `automatic`, `forward`, or `reverse`
5. **Ensure the light is OFF**
6. Click **Call Service**

**Via YAML Service Call:**

```yaml
# Try automatic mode first (default)
service: ubisys.configure_d1_phase_mode
data:
  entity_id: light.kitchen_dimmer
  phase_mode: automatic
```

```yaml
# Switch to reverse phase for LED lamps with flickering
service: ubisys.configure_d1_phase_mode
data:
  entity_id: light.kitchen_dimmer
  phase_mode: reverse
```

```yaml
# Use forward phase for incandescent/halogen
service: ubisys.configure_d1_phase_mode
data:
  entity_id: light.kitchen_dimmer
  phase_mode: forward
```

**Via Automation:**

```yaml
automation:
  - alias: "Configure D1 Phase Mode on Startup"
    trigger:
      - platform: homeassistant
        event: start
    action:
      # Wait for ZHA to be ready and ensure light is off
      - delay: 00:00:30
      - service: light.turn_off
        target:
          entity_id: light.kitchen_dimmer
      - delay: 00:00:05
      - service: ubisys.configure_d1_phase_mode
        data:
          entity_id: light.kitchen_dimmer
          phase_mode: reverse
```

**Via Script:**

```yaml
configure_kitchen_dimmer:
  alias: "Configure Kitchen Dimmer Phase Mode"
  sequence:
    - service: light.turn_off
      target:
        entity_id: light.kitchen_dimmer
    - delay: 00:00:05
    - service: ubisys.configure_d1_phase_mode
      data:
        entity_id: light.kitchen_dimmer
        phase_mode: reverse
    - service: notify.mobile_app
      data:
        message: "Kitchen dimmer configured for reverse phase (LED mode)"
```

### Troubleshooting Phase Control Issues

| Symptom | Likely Cause | Solution |
|---------|-------------|----------|
| Flickering at low brightness | Wrong phase mode or min level too low | Try reverse phase for LEDs, increase min level |
| Buzzing/humming sound | Wrong phase mode or transformer incompatibility | Try switching between forward/reverse |
| Can't dim below 30-40% | Min level too high or wrong phase mode | Try reverse phase, adjust ballast min level |
| Lights turn off at low brightness | Min level below LED driver threshold | Increase ballast min level |
| Configuration fails | Light is currently ON | Turn off light before configuring |
| "Attribute is read-only" error | Light is currently ON | Turn off light before configuring |

## Ballast Configuration

### What is Ballast Configuration?

The ballast configuration controls the minimum and maximum brightness levels that the dimmer will output. This is essential for LED compatibility, as LEDs have a narrow operating range compared to incandescent bulbs.

**Minimum Level (1-254)**:
- The lowest brightness the dimmer will output
- Prevents LED flickering at low brightness
- Set to the lowest value where your LEDs don't flicker
- Typical range: 10-20 for most LEDs
- Lower values = smoother dimming, but risk flickering

**Maximum Level (1-254)**:
- The highest brightness the dimmer will output
- Limits power consumption
- Useful for energy savings or to reduce LED lifespan degradation
- Typical range: 200-254 for most applications
- Default is 254 (100% brightness)

### When to Configure Ballast

Configure ballast levels when:

- ✅ LEDs flicker at low brightness (increase min level)
- ✅ LEDs turn off before reaching 0% (increase min level)
- ✅ You want to limit maximum brightness (decrease max level)
- ✅ You want to save energy (decrease max level)
- ✅ LED manufacturer specifies min/max values

### Configuration Service: configure_d1_ballast

Like phase mode, you can configure one or multiple D1 entities at once; the
integration queues them sequentially.

#### Service Parameters

| Parameter | Required | Type | Valid Range | Description |
|-----------|----------|------|-------------|-------------|
| `entity_id` | Yes | string or list | - | One or more D1 light entities |
| `min_level` | No | integer | 1-254 | Minimum brightness level |
| `max_level` | No | integer | 1-254 | Maximum brightness level |

Notes:
- At least one of `min_level` or `max_level` must be specified
- Both can be specified in a single call
- Configuration can be done while the light is ON or OFF
- Values are persistent across power cycles

#### Examples

**Via Home Assistant UI:**

1. Navigate to **Developer Tools** → **Services**
2. Select service: `ubisys.configure_d1_ballast`
3. Choose your D1 entity from the dropdown
4. Enter min_level and/or max_level values
5. Click **Call Service**

**Via YAML Service Call:**

```yaml
# Set minimum level to prevent flickering
service: ubisys.configure_d1_ballast
data:
  entity_id: light.kitchen_dimmer
  min_level: 15
```

```yaml
# Set both min and max levels
service: ubisys.configure_d1_ballast
data:
  entity_id: light.kitchen_dimmer
  min_level: 20
  max_level: 240
```

```yaml
# Limit maximum brightness to 80% for energy savings
service: ubisys.configure_d1_ballast
data:
  entity_id: light.kitchen_dimmer
  max_level: 203  # Approximately 80% of 254
```

**Via Automation:**

```yaml
automation:
  - alias: "Configure D1 Ballast on Startup"
    trigger:
      - platform: homeassistant
        event: start
    action:
      - delay: 00:00:30  # Wait for ZHA to be ready
      - service: ubisys.configure_d1_ballast
        data:
          entity_id: light.kitchen_dimmer
          min_level: 15
          max_level: 254
```

**Via Script:**

```yaml
optimize_led_dimming:
  alias: "Optimize LED Dimming"
  sequence:
    - service: ubisys.configure_d1_ballast
      data:
        entity_id: light.kitchen_dimmer
        min_level: 20
        max_level: 240
    - service: notify.mobile_app
      data:
        message: "LED dimming optimized: min=20, max=240"
```

### Finding the Right Min Level

Use this procedure to find the optimal minimum level for your LEDs:

1. Start with `min_level: 1` (lowest possible)
2. Dim the light to its lowest setting
3. If the LED flickers or turns off, increase min_level by 5
4. Repeat until the LED stays on steadily at lowest brightness
5. Add 2-3 to the found value for safety margin

Example script for testing:

```yaml
test_min_level:
  alias: "Test Min Level"
  sequence:
    - service: ubisys.configure_d1_ballast
      data:
        entity_id: light.kitchen_dimmer
        min_level: "{{ states('input_number.test_min_level') | int }}"
    - delay: 00:00:02
    - service: light.turn_on
      target:
        entity_id: light.kitchen_dimmer
      data:
        brightness: 1  # Lowest brightness

# Create an input_number helper to adjust the test value
# Configuration → Helpers → Create Helper → Number
# Name: test_min_level, Min: 1, Max: 100, Step: 5
```

## Common Configuration Scenarios

### Scenario 1: New LED Installation (Starting Point)

```yaml
# Step 1: Configure for automatic phase detection and factory defaults
service: ubisys.configure_d1_phase_mode
data:
  entity_id: light.new_led
  phase_mode: automatic

# Step 2: Test dimming behavior
# If flickering at low brightness, proceed to Step 3

# Step 3: Set minimum level to prevent flickering
service: ubisys.configure_d1_ballast
data:
  entity_id: light.new_led
  min_level: 15
```

### Scenario 2: LED Flickering at Low Brightness

```yaml
# Step 1: Try reverse phase control
service: ubisys.configure_d1_phase_mode
data:
  entity_id: light.flickering_led
  phase_mode: reverse

# Step 2: Increase minimum level
service: ubisys.configure_d1_ballast
data:
  entity_id: light.flickering_led
  min_level: 25
```

### Scenario 3: Buzzing Transformer

```yaml
# Try switching from automatic to forward phase
service: ubisys.configure_d1_phase_mode
data:
  entity_id: light.buzzing_halogen
  phase_mode: forward
```

### Scenario 4: Energy-Efficient Office Setup

```yaml
# Limit maximum brightness to 75% to save energy
service: ubisys.configure_d1_ballast
data:
  entity_id: light.office_overhead
  min_level: 10
  max_level: 190  # Approximately 75% of 254
```

### Scenario 5: Multiple D1 Dimmers with Same LED Type

```yaml
script:
  configure_all_bedroom_leds:
    alias: "Configure All Bedroom LEDs"
    sequence:
      # Turn off all lights first (required for phase mode)
      - service: light.turn_off
        target:
          entity_id:
            - light.bedroom_ceiling
            - light.bedroom_reading
            - light.bedroom_closet
      - delay: 00:00:05

      # Configure phase mode for all
      - service: ubisys.configure_d1_phase_mode
        target:
          entity_id:
            - light.bedroom_ceiling
            - light.bedroom_reading
            - light.bedroom_closet
        data:
          phase_mode: reverse

      # Configure ballast for all
      - service: ubisys.configure_d1_ballast
        target:
          entity_id:
            - light.bedroom_ceiling
            - light.bedroom_reading
            - light.bedroom_closet
        data:
          min_level: 15
          max_level: 254
```

## Advanced Topics

### Configuration Persistence

All D1 configuration is stored in the device's non-volatile memory and persists across:
- ✅ Home Assistant restarts
- ✅ ZHA integration reloads
- ✅ Power outages
- ✅ Zigbee network resets

However, a **factory reset** of the D1 will restore default values:
- Phase mode: automatic
- Min level: 1
- Max level: 254

### Load Type Reference

| Load Type | Phase Mode | Typical Min Level | Notes |
|-----------|-----------|-------------------|--------|
| Incandescent | forward or automatic | 1-5 | Very forgiving, works with any setting |
| Halogen (low-voltage, magnetic transformer) | forward | 5-10 | May buzz if wrong phase |
| Halogen (low-voltage, electronic transformer) | reverse | 10-20 | Often needs reverse phase |
| LED (dimmable, 230V) | reverse | 10-30 | Wide variation by brand |
| LED (dimmable, 12V with electronic transformer) | reverse | 15-35 | Most demanding load type |
| CFL (dimmable) | reverse | 20-40 | Not recommended, limited dimming range |

### Technical Details

**Phase Control Mode** (DimmerSetup Cluster):
- Cluster ID: 0xFC01 (manufacturer-specific)
- Attribute ID: 0x0002 (Mode)
- Endpoint: 1 (Dimmable Light endpoint)
- Values: 0x00 (automatic), 0x01 (forward), 0x02 (reverse)
- Constraint: Only writable when output is OFF

**Ballast Configuration** (Ballast Cluster):
- Cluster ID: 0x0301 (standard ZCL)
- Min Level Attribute: 0x0011
- Max Level Attribute: 0x0012
- Endpoint: 4 (Enhanced dimmer endpoint)
- Valid Range: 1-254 (0x01-0xFE)
- Default Values: min=1, max=254

## Safety and Best Practices

### Electrical Safety

⚠️ **WARNING**: Always follow electrical safety practices:
- Turn off power at the circuit breaker before installing or servicing the dimmer
- Only use with compatible dimmable loads (check manufacturer specifications)
- Do not exceed the D1's maximum load rating (200W resistive, 100W inductive)
- Use appropriate circuit protection (fuse or breaker)
- Installation should be performed by a qualified electrician

### Configuration Best Practices

1. **Start Conservative**: Begin with automatic phase mode and default ballast settings
2. **Change One Thing at a Time**: Don't adjust phase mode and ballast levels simultaneously
3. **Test Thoroughly**: Test all brightness levels after configuration changes
4. **Document Your Settings**: Keep a record of working configurations for each load type
5. **Allow Settle Time**: Wait a few seconds between configuration changes
6. **Monitor Temperature**: Ensure the dimmer doesn't overheat with the new settings

### Common Mistakes to Avoid

❌ **Don't**: Configure phase mode while the light is on
✅ **Do**: Turn off the light first, wait 5 seconds, then configure

❌ **Don't**: Set min_level too high (above 50) unless absolutely necessary
✅ **Do**: Find the lowest min_level that works for your LEDs

❌ **Don't**: Use non-dimmable LEDs with the D1
✅ **Do**: Always verify LED bulbs are marked as "dimmable"

❌ **Don't**: Mix different LED brands on one dimmer
✅ **Do**: Use the same LED model throughout for consistent behavior

❌ **Don't**: Ignore persistent buzzing or flickering
✅ **Do**: Try different phase modes or consult LED manufacturer specifications

## Troubleshooting

### Configuration Service Fails

**Error**: "Entity not found"
- Verify the entity_id is correct
- Check that the Ubisys integration is loaded
- Ensure the D1 is paired with ZHA

**Error**: "Attribute is read-only" or "ensure output is OFF"
- Turn off the light before configuring phase mode
- Wait at least 5 seconds after turning off before configuring

**Error**: "Could not access DimmerSetup cluster"
- Verify the D1 quirk is loaded (check ZHA device signature)
- Ensure the device is online and responding
- Try reloading the ZHA integration

**Error**: "Invalid value"
- Check that min_level and max_level are within 1-254 range
- Verify phase_mode is one of: automatic, forward, reverse

### Dimming Issues Persist After Configuration

If you've tried different phase modes and ballast settings but still have issues:

1. **Verify LED Compatibility**: Some "dimmable" LEDs have limited compatibility
2. **Check Load Type Mixing**: Don't mix LED and incandescent on same dimmer
3. **Test with Different Bulb**: Try a known-compatible dimmable LED
4. **Check Wiring**: Verify proper installation and grounding
5. **Update Firmware**: Check if D1 firmware update is available
6. **Consult Manufacturer**: Both LED and dimmer manufacturers may have compatibility lists

## Reference

### Related Documentation

- [Contributing Guide](../../CONTRIBUTING.md) - Developer documentation
- [Troubleshooting Guide](../troubleshooting.md) - General troubleshooting

### External Resources

- [Ubisys D1 Technical Reference](https://www.ubisys.de/wp-content/uploads/ubisys-d1-technical-reference.pdf) - Official device documentation
- [Zigbee2MQTT D1 Page](https://www.zigbee2mqtt.io/devices/D1.html) - Alternative integration reference
- [Home Assistant ZHA Documentation](https://www.home-assistant.io/integrations/zha/) - ZHA integration guide

### Service Definitions

For complete service definitions including field descriptions and validation rules, see:
- `custom_components/ubisys/services.yaml` - Service definitions
- `custom_components/ubisys/strings.json` - Service descriptions
- `custom_components/ubisys/d1_config.py` - Service implementation

## Support

If you encounter issues not covered in this guide:

1. Check the [Troubleshooting Guide](../troubleshooting.md)
2. Review Home Assistant logs for error messages
3. Search existing issues on [GitHub](https://github.com/imstevenxyz/homeassistant-ubisys)
4. Open a new issue with:
   - D1 firmware version
   - LED bulb brand and model
   - Complete error messages from logs
   - Configuration you tried
   - Description of the dimming issue
