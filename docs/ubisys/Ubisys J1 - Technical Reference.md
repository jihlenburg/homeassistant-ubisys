# Ubisys J1/J1-R ZigBee Shutter Control - Technical Reference

## Overview

The Ubisys Shutter Control J1 is a **ZigBee 3.0 Certified** window covering adapter for bidirectional, single-phase AC motors with integrated smart meter functionality.

### Product Variants
- **J1**: In-wall flush-mounting (Order Code: 1076)
- **J1-R**: DIN rail mounting for fuse cabinets (Order Code: 1144)

### Manufacturer Information
- **Company**: ubisys technologies GmbH, Düsseldorf, Germany
- **Manufacturer ID**: 0x10F2
- **Website**: www.ubisys.de

---

## Key Features

### Core Functionality
- **ZigBee 3.0 Certified** AC shutter control with integrated smart meter
- Controls single-phase, bidirectional AC motors at **230V~, up to 500VA**
- **ubisys WaveStep™ technology** for advanced positioning (e.g., "go to 50% lift, 45° tilt angle")
- ZigBee router functionality for network meshing

### Inputs & Outputs
- Two configurable **230V~ inputs** (pre-configured for local motor operation)
- Individually reconfigurable as:
  - Window covering controller
  - Scene selector switches
  - Works with momentary or stationary switches
- **Local control works even when not joined to a network**

### Advanced Features
- Solid state switching for highest efficiency and durability
- Supports groups, scenes, bindings, and reporting
- Standard ZigBee Window Covering Cluster with manufacturer-specific extensions
- **Integrated smart meter** capable of measuring:
  - Active power
  - Reactive power
  - Apparent power
  - Voltage
  - Current
  - Frequency

### Supported Window Covering Types
- Roller shades
- Lift & tilt blinds
- Shutters
- Windows
- Flaps
- Projector screens
- Awnings
- Drapery

### Network Capabilities
- **Extended neighbor table**: up to 78 entries (vs. 25 standard)
- **Extended routing table**: up to 96 entries (vs. 10 standard)
- **Extended buffering**: up to 24 buffers for sleeping end-devices (vs. 1 standard)
- **Extended APS duplicate rejection**: 64 slots (vs. 1 standard)
- Reliable network-wide broadcasts with passive acknowledgments
- Sophisticated routing algorithm avoiding loops

### Hardware Specifications
- **Power dissipation**: 0.3W
- **MCU**: 32-bit ARM at 48MHz with 64KB SRAM
- **PHY**: Texas Instruments CC2520
  - 5dBm transmit power
  - -98dBm receiver sensitivity
- **Antenna**: On-board inverted-F antenna
- **Channels**: All 2.4 GHz band channels (11-26)
  - Primary: {11, 15, 20, 25}
  - Secondary: {12, 13, 14, 16, 17, 18, 19, 21, 22, 23, 24, 26}

### Build Quality
- **Made in Germany** with high-quality, enduring parts
- Flame retardant housing (V-0), Black, RAL 9005
- Many years of life expectancy

### Firmware & Updates
- Firmware upgradable **over-the-air** (OTA) during normal operation
- OTA image type: **0x7B04** (J1), **0x7B07** (J1-R)

---

## Installation

### Mains Powered Operation
Refer to the hardware installation guide included in the product package for detailed installation instructions.

### Low-Voltage Operation (Maintenance/Testing Only)
For testing or maintenance, you can power the device with low-voltage DC (12V, 24V, or 48V):
- Connect DC ground (0V, negative) to phase input (L, brown wire)
- Connect DC supply voltage (12-48VDC, positive) to neutral input (N, blue wire)

**Note**: In DC mode, ZigBee interface is operational, but inputs/outputs are non-operational.

---

## Initial Device Start-Up

### First Power-On Behavior
1. Device searches for open ZigBee network
2. **Quick blinking**: Search in progress
3. **5 slow blinks**: Successfully joined network
4. **3 quick blinks**: Joining failure (continues searching)

### Power-Cycle Behavior
- **5 slow blinks**: Operating as router
- **10 slow blinks**: Operating as coordinator/trust center
- **Quick blinking**: Searching for network

### Position Awareness
⚠️ **Important**: After power-cycle, the device doesn't know the shutter's current position.

- Device must reach top or bottom limit once to learn position
- Device won't auto-move after power-cycle for safety
- Waits for move command, then finds upper bound as reference before moving to target

### Calibration Requirement
For positioning using lift/tilt values, the device **must be calibrated** during commissioning. Otherwise, only move up/down and stop commands are available.

---

## Man-Machine Interface (MMI)

### Hardware
- **Push-button**: Behind tiny hole in front face
- **LED**: Right next to button

### Factory Reset Shortcuts
1. **10-second press**: Keep button pressed for ~10 seconds until LED flashes
2. **Power-cycle sequence**:
   - Power on for ≥4 seconds
   - Power off for ≥1 second
   - Power on for 0.5-2 seconds
   - Power off for ≥1 second
   - Repeat short cycle 2 more times (3 total)
   - Power on and leave powered

### Menu System

**Entering Menu**: Press and hold button for >1 second until 3 short flashes, then see blinking pattern.

**Navigating Menu**: Short press (<1 second) advances to next item.

**Executing Item**: Press and hold for >1 second to execute.

#### Menu Items

| Item | Operation | Description |
|------|-----------|-------------|
| **1** | Network Steering | Single press instigates ZigBee Network Steering (EZ-mode). Toggles network open/closed. LED on = network open. |
| **2** | Finding & Binding | Initiates F&B on selected endpoint. Select endpoint, wait for LED confirmation, press to accept. |
| **3** | Clear Bindings | Clears bindings on selected initiator endpoint. Select endpoint, confirm. |
| **4** | Set Device Role & Factory Reset | Select role: (1) Router, (2) Distributed network router, (3) Coordinator/trust center. Resets to factory defaults. |
| **5** | Factory Reset | Complete factory reset, then reboot. Broadcasts network leave indication. |
| **6** | Advanced Commands | (1) Simple reset (silent rejoin), (2) Reset and rejoin, (3) Full factory reset including security counters |
| **7** | Reserved | Do not use |

---

## ZigBee Interface

### Device Endpoints

| Endpoint | Profile | Device Type | Description |
|----------|---------|-------------|-------------|
| **0** | 0x0000: ZigBee Device Profile | ZDO | Standard management features |
| **1** | 0x0104: Common Profile (HA) | Window Covering Device (0x0202) | Controls motor via window covering cluster. Supports groups, scenes, reporting. F&B target. |
| **2** | 0x0104: Common Profile (HA) | Window Covering Controller (0x0203) | Transmits commands triggered by local inputs. F&B initiator. |
| **3** | 0x0104: Common Profile (HA) | Metering (0x0702) | Provides metering and electrical measurement |
| **232** | 0x0104: Common Profile (HA) | Device Management (0x0507) | Device configuration and setup |
| **242** | 0xA1E0: Green Power Profile | Combined Proxy and Sink | ZigBee Green Power support |

### Security

#### Pre-configured Trust Center Link-Keys
1. Global Default ("ZigBeeAlliance09")
2. ZigBee 3.0 Global Distributed Security Link-Key
3. Device-individual key derived from **installation code**

#### Installation Code
- Printed on device back in text format and QR code
- Format: 128-bit installation code + 16-bit CRC
- QR code format: `ubisys2/MODEL/EUI-64/INSTALL_CODE/CHECKSUM`

Example:
```
ubisys2/J1/001FEE00000000FF/0F7C1CD805F91649EBA84580AA1CB432F51A/21
```

---

## Endpoint #1: Window Covering Device

### Clusters

| Cluster ID | Direction | Description |
|------------|-----------|-------------|
| 0x0000 | Server | Basic |
| 0x0003 | Server | Identify |
| 0x0004 | Server | Groups |
| 0x0005 | Server | Scenes |
| 0x0102 | Server | Window Covering |

### Identify Behavior
In identify mode, up and down directions activate alternately once per second.
⚠️ **Caution**: Ensure motor/mechanics can handle this switching rate or disconnect load.

### Window Covering Cluster - Standard Attributes

| Attribute ID | Type | Access | Description |
|--------------|------|--------|-------------|
| 0x0000 | enum8 | R | WindowCoveringType |
| 0x0001 | uint16 | R | PhysicalClosedLimitLift (cm) |
| 0x0002 | uint16 | R | PhysicalClosedLimitTilt (0.1°) |
| 0x0003 | uint16 | R, Reportable | CurrentPositionLift (cm) |
| 0x0004 | uint16 | R, Reportable | CurrentPositionTilt (0.1°) |
| 0x0007 | bitmap8 | R | ConfigurationAndStatus |
| 0x0008 | uint8 | R, Reportable | **CurrentPositionLiftPercentage** (0-100%) |
| 0x0009 | uint8 | R, Reportable | **CurrentPositionTiltPercentage** (0-100%) |
| 0x000A | bitmap8 | R, Reportable | **OperationalStatus** (motor active bits) |
| 0x0010 | uint16 | R | InstalledOpenLimitLift (cm) |
| 0x0011 | uint16 | R | InstalledClosedLimitLift (cm) |
| 0x0012 | uint16 | R | InstalledOpenLimitTilt (0.1°) |
| 0x0013 | uint16 | R | InstalledClosedLimitTilt (0.1°) |
| 0x0017 | bitmap8 | R/W, Persistent | Mode (reverse, calibration, maintenance, feedback) |

### Manufacturer-Specific Attributes (Cluster 0x10F2)

| Attribute ID | Type | Access | Description |
|--------------|------|--------|-------------|
| 0x0000 | enum8 | R/W, Persistent, Preserved | WindowCoveringType* (writable version) |
| 0x0007 | bitmap8 | R/W, Persistent, Preserved | ConfigurationAndStatus* (disable closed-loop) |
| 0x0010 | uint16 | R/W, Persistent, Preserved | InstalledOpenLimitLift* |
| 0x0011 | uint16 | R/W, Persistent, Preserved | InstalledClosedLimitLift* |
| 0x0012 | uint16 | R/W, Persistent, Preserved | InstalledOpenLimitTilt* |
| 0x0013 | uint16 | R/W, Persistent, Preserved | InstalledClosedLimitTilt* |
| 0x1000 | uint8 | R/W, Persistent, Preserved | **TurnaroundGuardTime** (units of 50ms, default: 10 = 500ms) |
| 0x1001 | uint16 | R/W, Persistent, Preserved | **LiftToTiltTransitionSteps** (AC waves for lift→tilt) |
| 0x1002 | uint16 | R/W, Persistent, Preserved | **TotalSteps** (AC waves for open→closed) |
| 0x1003 | uint16 | R/W, Persistent, Preserved | **LiftToTiltTransitionSteps2** (AC waves for tilt→lift) |
| 0x1004 | uint16 | R/W, Persistent, Preserved | **TotalSteps2** (AC waves for closed→open) |
| 0x1005 | uint8 | R/W, Persistent, Preserved | **AdditionalSteps** (%, default: 10%) |
| 0x1006 | uint16 | R/W, Persistent, Preserved | **InactivePowerThreshold** (mW, default: 0x1000 ≈ 4.1W) |
| 0x1007 | uint16 | R/W, Persistent, Preserved | **StartupSteps** (AC waves, default: 0x0020 = 32) |

### Supported Commands

| Command ID | Description |
|------------|-------------|
| 0x00 | Move up/open |
| 0x01 | Move down/close |
| 0x02 | Stop |
| 0x04 | Go to Lift Value |
| 0x05 | Go to Lift Percentage |
| 0x07 | Go to Tilt Value |
| 0x08 | Go to Tilt Percentage |

---

## Calibration Procedure

### Step 1: Choose Device Type

| Value | Type | Capabilities |
|-------|------|--------------|
| 0 | Roller Shade | Lift only |
| 1 | Roller Shade (2 motors) | Lift only |
| 2 | Roller Shade (exterior) | Lift only |
| 3 | Roller Shade (2 motors, exterior) | Lift only |
| 4 | Drapery | Lift only |
| 5 | Awning | Lift only |
| 6 | Shutter | Tilt only |
| 7 | Tilt Blind (tilt only) | Tilt only |
| 8 | **Tilt Blind (lift & tilt)** | **Lift & Tilt** |
| 9 | Projector Screen | Lift only |

Write attribute `0x10F2:0x0000` (WindowCoveringType) accordingly.

### Step 2: Prepare Calibration

Write these initial values:
```
0x10F2:0x0010 (InstalledOpenLimitLift) = 0x0000 (0 cm)
0x10F2:0x0011 (InstalledClosedLimitLift) = 0x00F0 (240 cm)
0x10F2:0x0012 (InstalledOpenLimitTilt) = 0x0000 (0°)
0x10F2:0x0013 (InstalledClosedLimitTilt) = 0x0384 (90.0°)
0x10F2:0x1001 (LiftToTiltTransitionSteps) = 0xFFFF (invalid)
0x10F2:0x1002 (TotalSteps) = 0xFFFF (invalid)
0x10F2:0x1003 (LiftToTiltTransitionSteps2) = 0xFFFF (invalid)
0x10F2:0x1004 (TotalSteps2) = 0xFFFF (invalid)
```

### Step 3: Enter Calibration Mode
Write attribute `0x0017` (Mode) = `0x02`

### Step 4: Start Position
Send "move down" command, then "stop" after a few centimeters to reach starting position.

### Step 5: Find Upper Bound
Send "move up" command. Device recognizes upper bound when reached.

### Step 6: Find Lower Bound
After motor stops, send "move down" command. Device finds and recognizes lower bound.

### Step 7: Complete Calibration
After motor stops, send "move up" command. Device returns to top, completing calibration of both directions.

✅ Attributes `0x10F2:0x1002` and `0x10F2:0x1004` now contain measured values (≠ 0xFFFF).

### Step 8: Tilt Blind Configuration (if applicable)
For tilt blinds, set `0x10F2:0x1001` and `0x10F2:0x1003` to lift-to-tilt transition times.

### Step 9: Exit Calibration Mode
Clear bit #1 in Mode attribute: Write `0x0017` = `0x00`

### Verification
1. Move blind down slightly, then move up
2. At top position, lift & tilt attributes should read 0
3. Test "move to %" commands (e.g., 25% lift, 50% tilt)
4. Scene support now operational

### Post Power-Cycle
Move down slightly, then up to regain position awareness.

---

## Endpoint #2: Window Covering Controller

This endpoint transmits commands triggered by local high-voltage inputs.

### Default Configuration (Dual Push-Button)

Factory default for **momentary switches** (one stable position):

**Input #1 (white wire, J1):**
- **Press**: Move up/open
- **Release**: Stop

**Input #2 (grey wire, J1):**
- **Press**: Move down/close
- **Release**: Stop

**Behavior:**
- **Short press**: Moves and stops when released
- **Long press**: Moves to fully open/closed position without stopping

### Alternative: Stationary Switches

For **rocker switches** (two stable positions):
- **Switch ON**: Motor moves
- **Switch OFF**: Motor stops immediately

---

## Endpoint #3: Metering

### Metering Cluster Attributes

| Attribute ID | Type | Description |
|--------------|------|-------------|
| 0x0000 | uint48 | CurrentSummationDelivered (energy to load) |
| 0x0001 | uint48 | CurrentSummationReceived (energy generated) |
| 0x0002 | uint48 | CurrentMaxDemandDelivered (peak power to load) |
| 0x0003 | uint48 | CurrentMaxDemandReceived (peak power generated) |
| 0x0200 | bitmap8 | Status |
| 0x0300 | enum8 | UnitOfMeasure (always kW) |
| 0x0400 | int24, Reportable | **InstantaneousDemand** (W, negative = generated) |

### Electrical Measurement Cluster Attributes

| Attribute ID | Type | Description |
|--------------|------|-------------|
| 0x0000 | bitmap32 | MeasurementType |
| 0x0300 | uint16 | **Frequency** (0.001 Hz) |
| 0x0304 | int32 | **TotalActivePower** (W) |
| 0x0305 | int32 | **TotalReactivePower** (VAr) |
| 0x0306 | uint32 | **TotalApparentPower** (VA) |
| 0x0505 | uint16 | **RMSVoltage** (L1) |
| 0x0508 | uint16 | **RMSCurrent** (L1) |
| 0x050B | int16 | **ActivePower** (L1, W) |
| 0x050E | int16 | **ReactivePower** (L1, VAr) |
| 0x050F | uint16 | **ApparentPower** (L1, VA) |
| 0x0510 | int8 | **PowerFactor** (L1, 0.01 units) |

---

## Endpoint #232: Device Management

### Device Setup Cluster (0xFC00) - Manufacturer-Specific

#### InputConfigurations Attribute (0x0000)

Array of 8-bit data, one per physical input:

**J1/J1-R Elements:**
- **0x0000**: Input #1 (white wire on J1) - default: 0x00
- **0x0001**: Input #2 (grey wire on J1) - default: 0x00

**Flag Bits:**
- **Bit 7 (0x80)**: Disable input
- **Bit 6 (0x40)**: Invert (active-low for normally closed circuits)
- **Bits 5-0**: Reserved

#### InputActions Attribute (0x0001)

Array of raw binary data containing instructions for input behavior.

**Field Structure:**
- **InputAndOptions** (uint8): Input index (lower 4 bits) + options (upper 4 bits)
- **Transition** (uint8): When to execute (see transition flags)
- **Endpoint** (uint8): Source endpoint (use 2 for J1/J1-R)
- **ClusterID** (uint16): Cluster ID (e.g., 0x0102 for window covering)
- **CommandTemplate** (raw data): ZCL command payload

**Transition Flags:**
- **Bit 7 (0x80)**: HasAlternate
- **Bit 6 (0x40)**: Alternate
- **Bits 3-2**: Initial state (00=ignore, 01=pressed <1s, 10=kept pressed >1s, 11=released)
- **Bits 1-0**: Final state (same as initial state)

---

## Endpoint #242: ZigBee Green Power

### Supported Green Power Device Types

| Device Type | Description | Commands |
|-------------|-------------|----------|
| 0x03 | Level Control Switch | Move, step, stop (with/without on/off) |
| 0x07 | Generic Switch | Press and release (up to 8 buttons) |

### Supported Green Power Commands

| Command | Description |
|---------|-------------|
| 0x10-0x17 | Recall scene #1-8 |
| 0x18-0x1F | Store scene #1-8 |
| 0x30 | Move up |
| 0x31 | Move down |
| 0x34 | Stop |
| 0x35 | Move up with on/off |
| 0x36 | Move down with on/off |
| 0x69 | Generic Press |
| 0x6A | Generic Release |

### Generic Switch Commissioning Behavior

**1 Contact Commissioned:**
- Short press: Stop
- Long press: Move up/down (alternates)

**2 Contacts Commissioned:**
- Button A short: Move up while pressed, stop when released
- Button A long: Move up to fully open
- Button B short: Move down while pressed, stop when released
- Button B long: Move down to fully closed

**3 Contacts Commissioned:**
- Button A: Move up
- Button B: Move down
- Button C: Stop

**4 Contacts Commissioned:**
- Buttons A/B: Same as 2-contact mode
- Button C: Move up to fully open
- Button D: Move down to fully closed

---

## Physical Dimensions

### J1 (Flush-mount, In-wall)
- **Width**: 47 mm
- **Depth**: 43 mm  
- **Height**: 12 mm

### J1-R (DIN Rail)
- **Width**: 18 mm (1 TE)
- **Height**: 90 mm
- **Depth**: 60.5 mm

### Housing
- Flame retardant (V-0)
- Color: Black, RAL 9005

---

## Compliance & Standards

### Directives
- 2014/53/EU - Radio Equipment Directive (RED)
- 2014/30/EU - Electromagnetic Compatibility (EMC)
- 2014/35/EU - Low Voltage Directive (LVD)
- 2012/19/EU - WEEE
- 2011/65/EU - RoHS

### Standards
- EN 300 328 V2.2.2
- EN 300 440 V2.2.1
- EN 301 489-1 V2.1.1
- IEEE 802.15.4:2020
- ZigBee 3.0 (ZigBee 2017 with Green Power)

---

## Best Practices & Tips

### Positioning
✅ **Use lift & tilt percentage** in your UI for consistent user experience

### After Power-Cycle
1. Move blind down slightly
2. Move up to reach top position
3. Position awareness restored

### Electronic Motors with Shut-Off
For motors with significant quiescence current:
- Set `InactivePowerThreshold` (0x1006) above standby consumption, below active power
- Default 0x1000 (~4.1W) works for most motors
- Default `StartupSteps` (0x0020 = 32 waves) suitable for most installations

### Disabling Positioning
If setup incompatible with positioning logic:
- Clear bits #3 and #4 in `ConfigurationAndStatus*` attribute

### Activity Visualization
Use `OperationalStatus` attribute (0x000A) - reportable - to visualize motor running up/down

### Scene Support
⚠️ **Requires calibration** to be operational
- Non-calibrated: 0% lift = fully open, non-zero = fully closed
- Device considers last move direction when storing scenes

---

## Contact Information

**ubisys technologies GmbH**  
Neumannstraße 10  
40235 Düsseldorf  
Germany

**Phone**: +49 (211) 54 21 55 - 00  
**Fax**: +49 (211) 54 21 55 - 99  
**Web**: www.ubisys.de  
**Email**: info@ubisys.de

### Support
- **Consumers/Installers**: http://www.ubisys.de/en/smarthome/support.html
- **Commercial Customers**: http://www.ubisys.de/en/engineering/support.html

---

## Document Information

**Document**: Reference Manual  
**Products**: J1 (5502), J1-R (5602)  
**Copyright**: © 2014-2021 ubisys technologies GmbH  
**Latest Revision**: 2.5 (September 16, 2021)

---

*This document is primarily intended for system integrators. End-users should refer to the installation guide included with the product.*