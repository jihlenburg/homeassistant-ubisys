# Ubisys J1 Window Covering Guide

Compatibility: Home Assistant 2024.1+ (Python 3.11+)

Docs: [index](../index.md) · [common tasks](../common_tasks.md) · [troubleshooting](../troubleshooting.md) · [FAQ](../faq.md)

This guide explains calibration and advanced tuning for Ubisys J1/J1-R window covering controllers.

## Why Calibration is Needed

The Ubisys J1 controller uses stepper motor position counting to track the exact position of your window covering. To provide accurate position control (e.g., "move to 50% open"), the controller needs to know the total number of steps between fully open and fully closed positions.

Calibration determines this total step count and stores it in the device's non-volatile memory.

## When to Calibrate

You should run calibration:

- **After initial installation** - Always calibrate a new device
- **After changing shade type** - Different configurations may affect step counting
- **After mechanical changes** - If you adjust mounting, tension, or fabric
- **If positions become inaccurate** - Recalibration can fix drift issues
- **After power loss** - In rare cases, settings may be lost

## Before You Start

### Prerequisites

1. ✅ Ubisys J1 paired with ZHA
2. ✅ Ubisys integration installed and configured
3. ✅ Shade type correctly selected in configuration
4. ✅ Window covering can move freely without obstructions
5. ✅ `python_script:` enabled in `configuration.yaml`

### Safety Checks

- Ensure the shade can move fully in both directions without hitting obstacles
- Check that mounting brackets are secure
- Verify there are no objects in the path of the shade
- Make sure the motor is not overheating from previous operations

### Time Required

- **Position-only shades** (roller, cellular, vertical): 30-60 seconds
- **Position + tilt shades** (venetian): 60-90 seconds

## Calibration Methods

Note on terminology: User-facing docs describe calibration as "Steps". Developer logs and code reference internal "Phases" for clarity.

Shade type naming (Z2M parity):
- Roller Shade (aka roller_shade)
- Vertical Blind (aka vertical_blind)
- Venetian Blind (aka venetian_blind)
- Exterior Venetian Blind (aka venetian_blind)

### Method 1: Via Home Assistant UI

1. Navigate to **Developer Tools** → **Services**
2. Select service: `ubisys.calibrate_j1`
3. Choose your entity from the dropdown
4. Click **Call Service**

![Calibration Service Screenshot](https://via.placeholder.com/600x300?text=Service+Call+Screenshot)

### Method 2: Via YAML Service Call

```yaml
service: ubisys.calibrate_j1
data:
  entity_id: cover.bedroom_shade
```

### Method 3: Via Automation

Add to your `automations.yaml`:

```yaml
automation:
  - alias: "Calibrate Ubisys on Restart"
    trigger:
      - platform: homeassistant
        event: start
    action:
      - delay: 00:00:30  # Wait for ZHA to be ready
      - service: ubisys.calibrate_j1
        data:
          entity_id: cover.bedroom_shade
```

### Method 4: Via Script

Create a script in `scripts.yaml`:

```yaml
calibrate_bedroom_shade:
  alias: "Calibrate Bedroom Shade"
  sequence:
    - service: ubisys.calibrate_j1
      data:
        entity_id: cover.bedroom_shade
    - service: notify.mobile_app
      data:
        message: "Calibration started for bedroom shade"
```

Then call it: `script.calibrate_bedroom_shade`

## The Calibration Process

### Step-by-Step Breakdown

#### 1. Set Window Covering Type

The script first configures the Zigbee `WindowCoveringType` attribute based on your shade configuration:

| Shade Type | WindowCoveringType |
|------------|-------------------|
| Roller | 0x00 (Rollershade) |
| Cellular | 0x00 (Rollershade) |
| Vertical | 0x04 (Vertical Blind) |
| Venetian | 0x08 (Venetian Blind) |
| Exterior Venetian | 0x08 (Venetian Blind) |

**What you'll see:** No visible movement

**Duration:** ~1 second

Tip: Tilt steps default
- For venetian blinds, a tilt range of ~100 steps works well on most setups. The integration writes and verifies this in the final step; you can fine‑tune later via the advanced tuning service.

#### 2. Move to Fully Open

The script commands the shade to open completely.

**What you'll see:** Shade moves to fully open position

**Duration:** 10-30 seconds (depending on shade size)

**Technical details:**
- Service call: `cover.open_cover`
- Script polls `is_opening` attribute until false
- Maximum wait: 60 seconds

#### 3. Reset Position Counter

The controller's internal position counter is reset to zero at the open position.

**What you'll see:** No visible movement, brief pause

**Duration:** ~1 second

**Technical details:**
- Writes `0` to attribute `current_position_lift` (0x0008)
- Uses manufacturer code 0x10F2

#### 4. Move to Fully Closed

The script commands the shade to close completely while the controller counts steps.

**What you'll see:** Shade moves to fully closed position

**Duration:** 10-30 seconds (depending on shade size)

**Technical details:**
- Service call: `cover.close_cover`
- Script polls `is_closing` attribute until false
- Controller increments step counter during movement

#### 5. Read Total Steps

The script reads the manufacturer-specific `total_steps` attribute.

**What you'll see:** No visible movement, brief pause

**Duration:** ~1-2 seconds

**Technical details:**
- Reads attribute 0x1002 (total_steps)
- Uses manufacturer code 0x10F2
- Value stored in device non-volatile memory

#### 6. Read Tilt Steps (Venetian Only)

For venetian blinds, the script also reads the tilt transition step count.

**What you'll see:** No visible movement

**Duration:** ~1-2 seconds

**Technical details:**
- Reads attribute 0x1001 (lift_to_tilt_transition_steps)
- Uses manufacturer code 0x10F2
- Only performed for venetian shade types

#### 7. Completion Notification

A persistent notification is created with the calibration results.

**What you'll see:** Home Assistant notification

**Example notification:**
```
Calibration Complete

Ubisys device cover.bedroom_shade has been calibrated successfully.

Shade type: venetian
Total steps: 4523
Tilt transition steps: 267
```

## Understanding Calibration Results

### Total Steps

The `total_steps` value represents the number of motor steps between fully open and fully closed.

**Typical ranges:**

| Shade Size | Expected Range |
|------------|----------------|
| Small (< 3 ft) | 2000-3500 steps |
| Medium (3-6 ft) | 3500-5000 steps |
| Large (6-9 ft) | 5000-7500 steps |
| Extra Large (> 9 ft) | 7500-12000 steps |

**What affects step count:**
- Physical size of the shade
- Gear ratio of the motor mounting
- Fabric weight and thickness
- Number of fabric layers

### Tilt Transition Steps

For venetian blinds, this value indicates how many steps are needed to fully rotate the slats.

**Typical range:** 150-400 steps

**What affects tilt steps:**
- Slat size and spacing
- Ladder tape configuration
- Slat rotation mechanism

### Validating Results

✅ **Good calibration indicators:**
- Total steps within expected range for your shade size
- Positions are accurate when commanded (test 25%, 50%, 75%)
- Tilt positions are accurate (venetian blinds)
- Repeated calibrations yield similar values (±5%)

⚠️ **Warning signs:**
- Total steps unusually low (< 1000) or high (> 15000)
- Position commands don't match physical position
- Large variance between calibration runs (> 10%)

## Troubleshooting

### Calibration Fails to Start

**Symptom:** No movement, error notification

**Possible causes:**
1. ZHA device unavailable
2. python_script integration not enabled
3. Entity ID incorrect

**Solutions:**
1. Check ZHA integration status
2. Add `python_script:` to `configuration.yaml`
3. Verify entity ID in Developer Tools → States

### Calibration Times Out

**Symptom:** Shade moves but calibration fails with timeout error

**Possible causes:**
1. Shade obstructed
2. Motor stalling
3. Zigbee communication issues

**Solutions:**
1. Remove obstructions and retry
2. Check motor mounting and tension
3. Move Zigbee coordinator closer or add router

### Inaccurate Position After Calibration

**Symptom:** Shade position doesn't match commanded position

**Possible causes:**
1. Slipping fabric or mechanism
2. Inconsistent motor operation
3. Calibration performed with obstruction

**Solutions:**
1. Check mechanical installation
2. Recalibrate from known good state
3. Adjust motor mounting tension

### Total Steps Value Seems Wrong

**Symptom:** Unexpected total_steps value

**Possible causes:**
1. Shade didn't fully open/close during calibration
2. Motor slippage during movement
3. Mechanical issues

**Solutions:**
1. Manually verify shade reaches end positions
2. Recalibrate with slower speed settings
3. Inspect mounting hardware

### Tilt Not Working (Venetian)

**Symptom:** Tilt commands have no effect

**Possible causes:**
1. Wrong shade type selected
2. Tilt mechanism not connected
3. Calibration incomplete

**Solutions:**
1. Reconfigure integration with correct shade type
2. Check mechanical tilt connection
3. Rerun calibration

## Advanced Tuning

This section explains how to tune advanced manufacturer-specific attributes on Ubisys J1/J1-R using the integration's service and options flow.

### What You Can Set

- **Turnaround Guard Time (0x1000)**: Delay between reversing direction, in 50ms units (e.g., 10 = 500ms)
- **Inactive Power Threshold (0x1006)**: Motor inactive threshold in milliwatts (e.g., 4096 ≈ 4.1W)
- **Startup Steps (0x1007)**: Number of AC waves to run on startup
- **Additional Steps (0x1005)**: Overtravel percentage (0–100) to improve limit contact

### How to Apply

**Via Options Flow:**
1. Navigate to **Settings** → **Devices & Services** → **Ubisys**
2. Select your J1 device
3. Click **Configure**
4. Select **"J1 Advanced"**
5. Adjust settings as needed

**Via Service:**
```yaml
service: ubisys.tune_j1_advanced
data:
  entity_id: cover.bedroom_shade
  turnaround_guard_time: 10  # 500ms delay
  inactive_power_threshold: 4096  # 4.1W
  startup_steps: 5
  additional_steps: 10  # 10% overtravel
```

### Verification

- Writes are verified by reading back the attributes; a mismatch raises an error
- Values persist across reboots

### Tips

- Make small, incremental changes and test in between
- Avoid setting guard time too low for safety and mechanical longevity
- If unsure about a value, use the options flow which provides helpful defaults

## Manual Zigbee Commands

### Manual Step Counter Reset

If you need to manually reset the position counter:

```yaml
service: zha.issue_zigbee_cluster_command
data:
  ieee: "00:12:4b:00:1c:a1:b2:c3"  # Your device IEEE
  endpoint_id: 2
  cluster_id: 0x0102
  cluster_type: in
  command: write_attributes
  command_type: client
  args:
    attribute: 0x0008
    value: 0
  manufacturer: 0x10F2
```

### Reading Manufacturer Attributes Directly

To check calibration values without running full calibration:

```yaml
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

### Custom Calibration Speed

The J1 controller allows configuring lift speed. Slower speeds may improve calibration accuracy:

```yaml
service: zha.issue_zigbee_cluster_command
data:
  ieee: "00:12:4b:00:1c:a1:b2:c3"
  endpoint_id: 2
  cluster_id: 0x0102
  cluster_type: in
  command: write_attributes
  command_type: client
  args:
    attribute: 0x0014  # config_status
    value: 0x03  # Reduced speed
  manufacturer: 0x10F2
```

## Best Practices

### Regular Calibration Schedule

Consider calibrating:

- **After installation:** Always
- **Seasonal:** Every 6 months for frequently used shades
- **After mechanical work:** Whenever mounting or fabric is adjusted
- **When needed:** If position accuracy degrades

### Pre-Calibration Checklist

Before each calibration:

- [ ] Shade is unobstructed
- [ ] Mounting is secure
- [ ] Motor is not overheated
- [ ] ZHA shows device available
- [ ] No pending firmware updates

### Post-Calibration Testing

After calibration, test:

1. **Full range:** Open and close completely
2. **Intermediate positions:** 25%, 50%, 75%
3. **Tilt (venetian):** Full range of tilt angles
4. **Repeatability:** Command same position multiple times

### Automation Integration

Create a calibration reminder automation:

```yaml
automation:
  - alias: "Remind to Calibrate Shades"
    trigger:
      - platform: time
        at: "09:00:00"
    condition:
      - condition: template
        value_template: >
          {{ (now() - state_attr('automation.calibrate_bedroom_shade', 'last_triggered')).days > 180 }}
    action:
      - service: notify.mobile_app
        data:
          title: "Maintenance Reminder"
          message: "It's been 6 months since shade calibration"
```

## Calibration Events

The calibration script fires Home Assistant events that you can use in automations:

### Success Event

**Event:** `ubisys_calibration_complete`

**Data:**
```yaml
entity_id: cover.bedroom_shade
shade_type: venetian
total_steps: 4523
tilt_steps: 267
```

**Automation example:**
```yaml
automation:
  - alias: "Log Calibration Success"
    trigger:
      - platform: event
        event_type: ubisys_calibration_complete
    action:
      - service: logbook.log
        data:
          name: "Ubisys Calibration"
          message: "{{ trigger.event.data.entity_id }} calibrated with {{ trigger.event.data.total_steps }} steps"
```

### Failure Event

**Event:** `ubisys_calibration_failed`

**Data:**
```yaml
entity_id: cover.bedroom_shade
error: "Timeout waiting for open position"
```

**Automation example:**
```yaml
automation:
  - alias: "Alert on Calibration Failure"
    trigger:
      - platform: event
        event_type: ubisys_calibration_failed
    action:
      - service: notify.mobile_app
        data:
          title: "Calibration Failed"
          message: "{{ trigger.event.data.entity_id }}: {{ trigger.event.data.error }}"
```

## FAQ

**Q: How often should I calibrate?**
A: After installation, then as needed. Most users calibrate once and never need to again.

**Q: Will calibration wear out my motor?**
A: No. Calibration is two full movements, which is minimal compared to daily use.

**Q: Can I calibrate multiple devices at once?**
A: Yes, but it's better to calibrate sequentially to avoid Zigbee network congestion.

**Q: Does calibration require internet access?**
A: No, everything is local.

**Q: What if my shade doesn't have clear "fully open" or "fully closed" positions?**
A: Use the positions where you want the shade to stop as the endpoints.

**Q: Can I cancel calibration mid-process?**
A: Yes, use the stop command. You'll need to recalibrate to get accurate positions.

**Q: Does changing the shade type require recalibration?**
A: Yes, always recalibrate after changing shade type in the configuration.

---

For additional help, see [Troubleshooting](../troubleshooting.md) or open an [issue](https://github.com/jihlenburg/homeassistant-ubisys/issues).
