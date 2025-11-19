# ubisys ZigBee Universal Dimmer D1/D1-R - Technical Reference Manual

## 1. Overview

The ubisys dimmer D1 is a universal ZigBee AC dimmer with integrated smart meter.

**Product Information:**
- **Manufacturer:** ubisys technologies GmbH, Düsseldorf, Germany
- **Manufacturer ID:** 0x10F2
- **Models:**
  - D1 (5503): In-wall flush-mount version
  - D1-R (5603): DIN rail mount version
- **Copyright:** 2014-2021 ubisys technologies GmbH

## 2. Key Features

### Hardware Features
- **ZigBee 3.0 Certified** Universal AC dimmer with integrated smart meter and router functionality
- **Power Rating:** 230V~, up to 500VA
- **Soft On/Off:** Fading for extended bulb life
- **Inputs:** Two configurable 230V~ inputs (one pre-configured for local output control)
- **Switching:** Solid state switching for efficiency and durability
- **Protection:** Overload and overcurrent protected (not short circuit protected)
- **Dimming Modes:** Configurable for leading edge and trailing edge (forward and reverse phase control) with automatic selection
- **Power Dissipation:** 0.3W
- **Housing:** Flame retardant (V-0), Black, RAL 9005
- **Made in Germany**

### Supported Load Types
- Incandescent bulbs
- High-voltage halogen
- Dimmable LED
- Dimmable CFL
- Low-voltage halogen with wire-wound transformer
- Low-voltage halogen with electronic transformer

### Radio Specifications
- **PHY:** Texas Instruments CC2520
- **Transmit Power:** 5dBm
- **Receiver Sensitivity:** -98dBm
- **Antenna:** On-board inverted-F antenna
- **Channels:** Supports all 2.4 GHz channels (11-26)
  - Primary: {11, 15, 20, 25}
  - Secondary: {12, 13, 14, 16, 17, 18, 19, 21, 22, 23, 24, 26}

### Processor
- **MCU:** Advanced 32-bit ARM microcontroller
- **Clock Speed:** 48MHz
- **RAM:** 64KB SRAM

### Network Features
- Supports joining centralized and distributed security networks as router
- Supports forming simple centralized security networks as Coordinator and Trust Center
- Supports forming distributed security networks as router
- **Extended neighbor table:** Up to 78 entries (3x standard requirement)
- **Extended routing table:** Up to 96 entries (10x standard requirement)
- **Extended buffering for sleeping end-devices:** Up to 24 buffers (24x standard requirement)
- **Extended APS duplicate rejection table:** Up to 64 slots (64x standard requirement)

### Security
Three pre-configured Trust Center Link-Keys:
1. Global Default Trust Center Link-Key ("ZigBeeAlliance09")
2. ZigBee 3.0 Global Distributed Security Link-Key (since firmware 1.10)
3. Device-individual link-key derived from installation code (printed as text and QR barcode)

### Input Configuration
Inputs can be individually reconfigured as:
- On/off switches
- Level control switches
- Scene selector switches
- Compatible with momentary or stationary switches

### Green Power Features
- ZigBee Green Power 2015 Combined Device (Proxy and Sink functionality)
- Supports On/off, Level Control, and Generic Switches

### Additional Features
- Local control works even when not joined to a network
- Supports groups, scenes, bindings, and reporting
- Firmware upgradable over-the-air (OTA)
- Man-Machine-Interface: Push-button and LED

## 3. Installation

### 3.1 Mains Powered Operation
Refer to the hardware installation guide included in the product package for detailed installation instructions.

### 3.2 Low-Voltage Operation (Maintenance/Testing)
For testing or maintenance purposes, the D1 can operate from a low-voltage DC source (12V=, 24V=, or 48V=):
- Connect DC ground (0V, negative) to phase input (marked "L", brown)
- Connect DC supply voltage to neutral input (marked "N", blue)
- **Note:** In DC mode, ZigBee interface is operational but inputs/outputs are non-operational

## 4. Initial Device Start-up

**Startup Behavior:**
1. Device searches for an open ZigBee network when first powered
2. LED blinks quickly during search
3. **Success:** Blinks five times slowly (joined as router) or ten times slowly (operating as coordinator)
4. **Failure:** Blinks three times quickly, continues searching
5. **On Join:** Blinks once (turns output on to 100% for 0.5s, then off for 0.5s) (firmware 1.12+)

**After Power-Cycle:**
- Router: Blinks five times slowly, then LED remains off during normal operation
- Coordinator: Blinks ten times slowly
- Searching: Blinks quickly
- LED turns on when network is open for joining

**Network Behavior:**
- Performs "silent rejoin" after reboot (no device announcement)
- After joining, extends joining window by 3 minutes via ZDO permit joining request

**Load Type Detection:**
- Restarts load type detection the first time the load is turned on after power-cycle
- You won't see usual soft on/off fading during detection
- Setting an intermediate level results in "full on" until load type is detected
- No detection occurs if dimming mode is pre-set to leading or trailing edge

**Startup Behavior:**
- May turn on load to specific dimming level automatically after power is applied
- Based on `StartupOnOff` and `StartupLevel` attributes (firmware 1.07+)
- Default behavior: Return to state prior to cutting power

## 5. Man-Machine Interface (MMI)

### 5.1 Physical Interface
- **Button:** Push-button behind small hole in front face
- **LED:** Located next to button

### 5.2 Factory Reset Shortcut
Press and hold button for approximately **10 seconds** until LED starts flashing (equivalent to menu item #5, firmware 1.06+).

### 5.3 Menu System

**Entering Menu:**
1. Press and hold button for >1 second
2. Three short flashes followed by one blink, pause, one blink... indicates menu entry
3. Short presses (<1 second) advance through menu items
4. LED blinks show current menu item number
5. Press and hold >1 second to execute selected item

**Menu Items (Firmware 1.05+):**

| Menu # | Operation | Description |
|--------|-----------|-------------|
| 1 | Network Steering | Single press initiates "EZ-mode". Toggles network permit joining state. LED on when network is open. |
| 2 | Finding & Binding | Initiates "EZ-mode" on initiator/target endpoint. Select endpoint via button presses. |
| 3 | Clear Bindings | Clears bindings on initiator endpoint. Select endpoint via button presses. |
| 4 | Set Device Role & Factory Reset | Selects ZigBee device role, resets to factory defaults, and restarts.<br>Option 1: Join as router<br>Option 2: Form distributed security network as first router<br>Option 3: Form centralized security network as coordinator |
| 5 | Factory Reset | Complete factory reset (preserves outgoing network security frame counter). Broadcasts network leave. |
| 6 | Advanced Commands | Option 1: Simple reset (reboot) with silent re-join<br>Option 2: Simple reset with re-join<br>Option 3: Full factory reset including security frame counters |
| 7 | Reserved | Internal use only - do not use |

### 5.4 Power-Cycle Sequencing Factory Reset

Alternative method to factory reset without physical button access (firmware 1.11+):

1. Power device for at least 4 seconds
2. Interrupt power for at least 1 second
3. Reapply power for 0.5-2 seconds
4. Repeat step 3 two more times (total of 3 short power cycles)
5. Apply power and leave powered on
6. Device will factory reset and reboot

**Visual Feedback:** Dimmer will flash connected light three times to indicate factory reset sequence in progress (firmware 1.12+).

### 5.5 Preconfiguring Dimming Mode

The dimming mode can be preconfigured during factory reset using power-cycle sequences (firmware 1.14+). The mode attribute is preserved across normal factory resets (only full factory reset reverts it).

#### Autodetect Dimming Mode

Follow steps 1-3 from section 5.4, then:
- **Step 4:** Repeat step 3 **three** more times (total of **4 short power cycles**)
- Light will flash **4 times** to confirm
- Mode attribute set to "0" (automatic)

#### Force Leading Edge (Forward Phase Control)

Follow steps 1-3 from section 5.4, then:
- **Step 4:** Repeat step 3 **four** more times (total of **5 short power cycles**)
- Light will flash **5 times** to confirm
- Mode attribute set to "1" (leading edge / TRIAC-like / inductive load)

**Use for:** Inductive loads (L), TRIAC-compatible devices

#### Force Trailing Edge (Reverse Phase Control)

Follow steps 1-3 from section 5.4, then:
- **Step 4:** Repeat step 3 **five** more times (total of **6 short power cycles**)
- Light will flash **6 times** to confirm
- Mode attribute set to "2" (trailing edge / capacitive load)

**Use for:** Capacitive loads (C/R), most CFLs and LED bulbs

**⚠️ CAUTION:** Specifying inappropriate mode for a load can cause permanent damage. For example, dimming highly inductive loads with reverse phase control can generate voltage spikes exceeding 600V rated peak voltage.

## 6. ZigBee Interface

### 6.1 Reference Documents
- [R1] IEEE 802.15.4 - Low-Rate Wireless Personal Area Networks
- [R2] ZigBee Specification, Revision 21 (05-3474-21)
- [R3] ZigBee 2015 Layer PICS and Stack Profiles, Rev 6 (08-0006-06)
- [R4] ZigBee Cluster Library Specification, Rev 5 (07-5123-05)
- [R5] ZigBee Base Device Behavior Specification, Rev 13 (13-0402-13)
- [R6] ZigBee PRO Green Power Feature Specification, Rev 26 (09-5499-26)
- [R7] ZigBee Home Automation Public Application Profile 1.2, Rev 29 (05-3520-29)
- [R8] ZigBee Smart Energy Standard 1.1b, Rev 18 (07-5356-18)

### 6.2 Device Anatomy

Both D1 and D1-R have identical ZigBee interface with eight application endpoints:

| Endpoint | Profile | Application | Description |
|----------|---------|-------------|-------------|
| 0 (0x00) | 0x0000: ZigBee Device Profile | ZigBee Device Object (ZDO) | Standard management features |
| 1 (0x01) | 0x0104: Common Profile (HA) | Dimmable Light (0x0101) | Controls output via on/off and level control. Supports groups, scenes, reporting. |
| 2 (0x02) | 0x0104: Common Profile (HA) | Dimmer Switch (0x0104) | Transmits on/off and level control commands from local input |
| 3 (0x03) | 0x0104: Common Profile (HA) | Dimmer Switch (0x0104) | Transmits on/off and level control commands from local input |
| 4 (0x04) | 0x0104: Common Profile (HA) | Metering (0x0702) | Provides metering and electrical measurement |
| 200 (0xC8) | Private | Private | Legacy private application (deprecated) |
| 232 (0xE8) | 0x0104: Common Profile (HA) | Device Management (0x0507) | Device management and configuration |
| 242 (0xF2) | 0xA1E0: Green Power Profile | ZigBee Green Power | Combined Proxy and Sink (firmware 1.08+) |

### 6.3 Installation Code

Each device has a pre-configured link key derived from an installation code printed on the housing in both text and QR code format.

**Format:** 128-bit installation code + 16-bit CRC

**QR Code Example:**
```
ubisys2/R0/001FEE00000000FF/0F7C1CD805F91649EBA84580AA1CB432F51A/21
```

**Format:** `ubisys2/{MODEL}/{EUI-64}/{INSTALLATION_CODE}/{CHECKSUM}`

**Checksum Calculation:** XOR of ASCII characters of model string, binary EUI-64 (big endian), and binary installation code.

## 7. Endpoint Details

### 7.1 Endpoint #0 - ZigBee Device Object (ZDO)

Supported ZDO Services (same as S1 - see S1 documentation for full list):

- Network address translation
- IEEE address translation
- Node/power descriptors
- Active endpoints
- Simple descriptors
- Match descriptors
- Device announcements
- Parent announcements
- System server discovery
- Bind/unbind
- Management functions (network discovery, LQI, routing, bindings, leave, permit joining, network updates)

### 7.2 Endpoint #1 - Dimmable Light

**Purpose:** Controls the load output (dimmer)

**Finding & Binding:** Target endpoint

#### Clusters

| Cluster | Direction | Description |
|---------|-----------|-------------|
| 0x0000 | Server | Basic - Device information |
| 0x0003 | Server | Identify - Identify mode control |
| 0x0004 | Server | Groups - Group management |
| 0x0005 | Server | Scenes - Scene management |
| 0x0006 | Server | On/off - Dimmer on/off control |
| 0x0008 | Server | Level Control - Dimmer level control |
| 0x0301 | Server | Ballast Configuration - Min/max level configuration |
| 0xFC01 | Server | Dimmer Setup - Advanced AC dimmer configuration |

#### 7.2.1 Identify Cluster

**Identify Mode:** Toggles output once per second

**⚠️ Caution:** Ensure attached load can handle this switching rate or disconnect load!

**Attributes:**

| Attribute | Type | Description |
|-----------|------|-------------|
| 0x0000 | unsigned16 | IdentifyTime - Remaining identify time in seconds |

**Commands:**

| Command | Description |
|---------|-------------|
| 0x00 | Identify - Enter/exit identify mode |
| 0x01 | Query Identify - Check if identifying |
| 0x40 | Trigger Effect - Initiate visual effect (firmware 1.07+) |

#### 7.2.2 Groups Cluster

**Attributes:**

| Attribute | Type | Description |
|-----------|------|-------------|
| 0x0000 | bitmap8, read-only | NameSupport - Always 0 (names not supported) |

**Commands:** (Same as S1)

- Add Group, View Group, Get Group Membership
- Remove Group, Remove All Groups
- Add Group if Identifying

#### 7.2.3 Scenes Cluster

**Attributes:**

| Attribute | Type | Description |
|-----------|------|-------------|
| 0x0000 | unsigned8, read-only | SceneCount - Total scenes stored |
| 0x0001 | unsigned8, read-only | CurrentScene - Active scene ID |
| 0x0002 | unsigned8, read-only | CurrentGroup - Active scene group |
| 0x0003 | bool, read-only | SceneValid - Scene currently active |
| 0x0004 | bitmap8, read-only | NameSupport - Always 1 (names supported) |

**Commands:**

| Command | Description |
|---------|-------------|
| 0x00 | Add Scene |
| 0x01 | View Scene |
| 0x02 | Remove Scene |
| 0x03 | Remove All Scenes |
| 0x04 | Store Scene |
| 0x05 | Recall Scene |
| 0x06 | Get Scene Membership |
| 0x40 | Enhanced Add Scene |
| 0x41 | Enhanced View Scene |
| 0x42 | Copy Scene |

#### 7.2.4 On/off Cluster

**Note:** Uses binding table for reporting targets.

**Attributes:**

| Attribute | Type | Description |
|-----------|------|-------------|
| 0x0000 | bool, read-only, reportable | OnOff - Current state |
| 0x4000 | bool, read-only | GlobalSceneControl - Next "Off with Effect" stores global scene (firmware 1.07+) |
| 0x4001 | unsigned16, read-only | OnTime - Auto-off countdown in 0.1s units (firmware 1.07+) |
| 0x4002 | unsigned16, read-only | OffWaitTime - Command ignore countdown in 0.1s units (firmware 1.07+) |
| 0x4003 | enum8, persistent | StartupOnOff - Startup behavior: 0x00=off, 0x01=on, 0xFF=restore, 0x02=invert (firmware 1.07+) |

**Commands:**

| Command | Description |
|---------|-------------|
| 0x00 | Turn off |
| 0x01 | Turn on |
| 0x02 | Toggle |
| 0x40 | Off with effect (firmware 1.07+) |
| 0x41 | On with recall global scene (firmware 1.07+) |
| 0x42 | On with timed off (firmware 1.07+) |

#### 7.2.5 Level Control Cluster

**Note:** Uses binding table for reporting targets.

**Attributes:**

| Attribute | Type | Description |
|-----------|------|-------------|
| 0x0000 | unsigned8, read-only, reportable | CurrentLevel - Current level (0=off, 254=100%) |
| 0x0001 | unsigned16, read-only | RemainingTime - Time to reach target level (0.1s units) |
| 0x000F | bitmap8, persistent | Options - Default command options (firmware 1.07+) |
| 0x0010 | unsigned16, persistent | OnOffTransitionTime - Transition time for on/off commands (0.1s units) |
| 0x0011 | unsigned8, persistent | OnLevel - Level to apply when turned on (0xFF=restore previous) |
| 0x4000 | unsigned8, persistent | StartupLevel - Initial level after reboot (0xFF=restore previous) (firmware 1.07+) |

**Manufacturer-Specific Attributes:**

| Attribute | Type | Description |
|-----------|------|-------------|
| 0x0000 (Mfr) | unsigned8, persistent | MinimumOnLevel - Minimum level when turning on (0xFF=disabled) (firmware 1.147+) |

**Commands:**

| Command | Description |
|---------|-------------|
| 0x00 | Move To Level - Supports command options (firmware 1.07+) |
| 0x01 | Move - Supports command options (firmware 1.07+) |
| 0x02 | Step - Supports command options (firmware 1.07+) |
| 0x03 | Stop |
| 0x04 | Move To Level with on/off |
| 0x05 | Move with on/off |
| 0x06 | Step with on/off |
| 0x07 | Stop with on/off |

**Note:** Load type detection restarts on first power-on after reboot, so soft on/off fading won't occur until detection completes.

#### 7.2.6 Ballast Configuration Cluster

**Purpose:** Configure minimum and maximum dimming levels

**Attributes:**

| Attribute | Type | Description |
|-----------|------|-------------|
| 0x0000 | unsigned8, read-only | PhysicalMinLevel - Always 1 for D1/D1-R |
| 0x0001 | unsigned8, read-only | PhysicalMaxLevel - Always 254 for D1/D1-R |
| 0x0002 | bitmap8, read-only | BallastStatus - Present but not maintained |
| 0x0010 | unsigned8, persistent | MinLevel - Minimum dimming level (default: 1) |
| 0x0011 | unsigned8, persistent | MaxLevel - Maximum dimming level (default: 254) |

**Use Cases:**
- Set `MinLevel` higher for loads (e.g., CFLs) that cannot operate below certain level
- Ensure incandescent bulbs emit visible light at minimum
- Set `MaxLevel` lower to enforce power saving in commercial environments

#### 7.2.7 Dimmer Setup Cluster (0xFC01)

**Purpose:** Manufacturer-specific cluster for advanced AC dimmer configuration

**Attributes:**

| Attribute | Type | Description |
|-----------|------|-------------|
| 0x0000 | bitmap8, read-only | Capabilities - Dimmer capability flags |
| 0x0001 | bitmap8, read-only | Status - Operational status flags |
| 0x0002 | bitmap8, persistent, preserved | Mode - Mode of operation (auto/forward/reverse phase control) |

##### Capabilities Attribute

**Capability Flags:**

| Bit | Flag | Description |
|-----|------|-------------|
| 0 | Forward Phase Control | Supports AC forward phase control |
| 1 | Reverse Phase Control | Supports AC reverse phase control |
| 2-4 | RFU | Reserved (write as 0) |
| 5 | Reactance Discriminator | Can distinguish inductive/capacitive loads |
| 6 | Configurable Curve | Can replace default dimming curve |
| 7 | Overload Detection | Can detect and shut off on overload |

##### Status Attribute

**Status Flags:**

| Bit | Flag | Description |
|-----|------|-------------|
| 0 | Forward Phase Control | Currently operating in forward phase control |
| 1 | Reverse Phase Control | Currently operating in reverse phase control |
| 2 | Operational | Dimmer is operational (outputs phase-cut voltage) |
| 3 | Overload | Output turned off due to overload detection |
| 4-5 | RFU | Reserved (write as 0) |
| 6 | Capacitive Load | Reactance discriminator detected capacitive load |
| 7 | Inductive Load | Reactance discriminator detected inductive load |

##### Mode Attribute

**Mode Configuration:**

| Bits 1-0 | Mode | Description |
|----------|------|-------------|
| 00b | Automatic | Auto-select appropriate dimming technique |
| 01b | Leading Edge | Force forward phase control (TRIAC-like, inductive) |
| 10b | Trailing Edge | Force reverse phase control (capacitive) |
| 11b | Reserved | Do not use |

**Important Notes:**
- Attribute is writable only when output is off
- Preserved across normal factory resets (firmware 1.14+)
- Can also be set via power-cycle sequences

**Example Use Case:**
Some LED bulbs (e.g., Philips MASTERLED 4W/7W) require forward phase control despite appearing as capacitive loads to the reactance discriminator. Force mode to 0x01 (leading edge) for proper operation.

### 7.3 Endpoint #2 - Primary Dimmer Switch

**Purpose:** Controls remote devices via first local input

**Finding & Binding:** Initiator endpoint

**Default Binding:** Bound to Endpoint #1 (enables local control even when not commissioned)

#### Clusters

| Cluster | Direction | Description |
|---------|-----------|-------------|
| 0x0000 | Server | Basic |
| 0x0003 | Server | Identify (no visual feedback) |
| 0x0005 | Client | Scenes (firmware 1.04+) |
| 0x0006 | Client | On/off |
| 0x0008 | Client | Level Control |

**Configuration:** Use Device Setup cluster (Endpoint #232) to configure input behavior

#### Commands Transmitted

**Scenes:** Recall Scene (group address as target)

**On/off:** Turn off, Turn on, Toggle

**Level Control:** Move with on/off, Stop with on/off

### 7.4 Endpoint #3 - Secondary Dimmer Switch

Same as Endpoint #2 but for the second input. Not bound by default.

### 7.5 Endpoint #4 - Metering

**Purpose:** Energy consumption monitoring and electrical measurements

#### Clusters

| Cluster | Direction | Description |
|---------|-----------|-------------|
| 0x0000 | Server | Basic |
| 0x0702 | Server | Metering |
| 0x0B04 | Server | Electrical Measurement |

#### 7.5.1 Metering Cluster

**Note:** Uses binding table. No default reporting - must configure manually.

**Attributes:**

| Attribute | Type | Description |
|-----------|------|-------------|
| 0x0000 | unsigned48, read-only | CurrentSummationDelivered - Energy delivered to load |
| 0x0001 | unsigned48, read-only | CurrentSummationReceived - Energy generated by device |
| 0x0002 | unsigned48, read-only | CurrentMaxDemandDelivered - Peak power delivered |
| 0x0003 | unsigned48, read-only | CurrentMaxDemandReceived - Peak power generated |
| 0x0200 | bitmap8, read-only | Status - Device status flags |
| 0x0300 | enum8, read-only | UnitOfMeasure - Always kW |
| 0x0400 | signed24, read-only, reportable | InstantaneousDemand - Current power in Watts (negative = generating) |

#### 7.5.2 Electrical Measurement Cluster

**Attributes:**

| Attribute | Type | Description |
|-----------|------|-------------|
| 0x0000 | bitmap32, read-only | MeasurementType - Measurable physical entities |
| 0x0300 | unsigned16, read-only | Frequency - AC voltage frequency (0.001 Hz units) |
| 0x0304 | signed32, read-only | TotalActivePower - Total active power (W) |
| 0x0305 | signed32, read-only | TotalReactivePower - Total reactive power (VAr) |
| 0x0306 | unsigned32, read-only | TotalApparentPower - Total apparent power (VA) |
| 0x0505 | unsigned16, read-only | RMSVoltage (L1) - Phase L1 RMS voltage |
| 0x0508 | unsigned16, read-only | RMSCurrent (L1) - Phase L1 RMS current |
| 0x050B | signed16, read-only | ActivePower (L1) - Phase L1 active power (W) |
| 0x050E | signed16, read-only | ReactivePower (L1) - Phase L1 reactive power (VAr) |
| 0x050F | unsigned16, read-only | ApparentPower (L1) - Phase L1 apparent power (VA) |
| 0x0510 | signed8, read-only | PowerFactor (L1) - Phase L1 power factor (0.01 units) |

### 7.6 Endpoint #232 - Device Management

**Purpose:** Device configuration and management

#### Clusters

| Cluster | Direction | Description |
|---------|-----------|-------------|
| 0x0000 | Server | Basic |
| 0x0003 | Client | Identify (firmware 1.04+) |
| 0x0015 | Server | Commissioning |
| 0x0019 | Client | OTA Upgrade |
| 0xFC00 | Server | Device Setup (manufacturer-specific) |

#### 7.6.1 Basic Cluster

**Note:** Singleton attributes (shared across all endpoints)

**Attributes:**

| Attribute | Type | Description |
|-----------|------|-------------|
| 0x0000 | unsigned8, read-only | ZCLVersion |
| 0x0001 | unsigned8, read-only | ApplicationVersion |
| 0x0002 | unsigned8, read-only | StackVersion |
| 0x0003 | unsigned8, read-only | HWVersion |
| 0x0004 | string, read-only | ManufacturerName - "ubisys" |
| 0x0005 | string, read-only | ModelIdentifier - "D1 (5503)" or "D1-R (5603)" |
| 0x0006 | string, read-only | DateCode - Format: "YYYYMMDD-XX-FBV" |
| 0x0007 | enum8, read-only | PowerSource - Mains-powered, single phase |
| 0x0008 | enum8, read-only | GenericDeviceClass - Invalid (ZigBee Light Link compatibility) (firmware 1.07+) |
| 0x0009 | enum8, read-only | GenericDeviceType - Invalid (ZigBee Light Link compatibility) (firmware 1.07+) |
| 0x000A | raw binary, read-only | GenericProductCode - Empty (ZigBee Light Link compatibility) (firmware 1.07+) |
| 0x000B | string, read-only | GenericProductURL - Empty (ZigBee Light Link compatibility) (firmware 1.07+) |
| 0x0010 | string, persistent | LocationDescription - Empty by default |
| 0x0011 | unsigned8, persistent | PhysicalEnvironment - "Unspecified" by default |
| 0x4000 | string, read-only | SWBuildID - Empty (ZigBee Light Link compatibility) (firmware 1.07+) |

**Commands:**

| Command | Description |
|---------|-------------|
| 0x00 | Reset to factory defaults (deprecated in firmware 1.07+, use mgmt_leave_req instead) |

#### 7.6.2 OTA Upgrade Cluster

**Image Types:**
- D1: 0x7B01
- D1-R: 0x7B08

#### 7.6.3 Device Setup Cluster (0xFC00)

**Purpose:** Configure advanced device options not covered by standard clusters

**Attributes:**

| Attribute | Type | Description |
|-----------|------|-------------|
| 0x0000 | array of data8, persistent, preserved | InputConfigurations - One entry per physical input (firmware 1.16+) |
| 0x0001 | array of raw data, persistent, preserved | InputActions - Maps inputs to endpoints and commands (firmware 1.16+) |

**Note:** Both attributes preserved across normal factory resets since firmware 1.16.

##### InputConfigurations Attribute

**Data Type:** Array of 8-bit data (0x48 containing 0x08 elements)

**D1/D1-R Elements:**

| Element | Description | Factory Default |
|---------|-------------|-----------------|
| 0x0000 | High-voltage physical input #1 (D1: white wire) | 0x00 |
| 0x0001 | High-voltage physical input #2 (D1: grey wire) | 0x00 |

**Bit Flags:**

| Bit | Flag | Description |
|-----|------|-------------|
| 7 | Disable | When set, input is disabled |
| 6 | Invert | Active-high (cleared) vs. active-low (set) |
| 5-0 | RFU | Reserved (write as 0) |

##### InputActions Attribute

**Data Type:** Array of raw binary data (0x48 containing 0x41 elements)

**Element Structure:**

| Field | Type | Description |
|-------|------|-------------|
| InputAndOptions | unsigned8 | 4-bit input index (LSBs) + 4 option flags (MSBs) |
| Transition | unsigned8 | Level transition specification |
| Endpoint | unsigned8 | Source endpoint (D1/D1-R: #2 or #3) |
| ClusterID | unsigned16 | Cluster ID for ZCL command |
| CommandTemplate | raw data | Variable-length ZCL command payload |

**Transition Bits:**

| Bit(s) | Field | Description |
|--------|-------|-------------|
| 7 | HasAlternate | Another instruction executes in alternating order |
| 6 | Alternate | This is the alternate instruction |
| 5-4 | RFU | Reserved (write as 0) |
| 3-2 | Initial State | 00=Ignore, 01=Pressed, 10=Kept pressed, 11=Released |
| 1-0 | Final State | 00=Ignore, 01=Pressed, 10=Kept pressed, 11=Released |

**Default Configuration (Single Push-Button - 8 entries):**

Provides toggle on short press, alternating dimming up/down on long press for both inputs.

**Alternative Configuration (Two Push-Buttons Up/Down - 6 entries):**

One button for on/brighter, one for off/darker.

### 7.7 Endpoint #242 - ZigBee Green Power

**Purpose:** Green Power Proxy and Sink functionality (firmware 1.08+)

**Specification:** ZigBee 2015 edition with IEEE EUI-64 and bidirectional commissioning support

#### Clusters

| Cluster | Direction | Description |
|---------|-----------|-------------|
| 0x0021 | Server | Green Power Sink |
| 0x0021 | Client | Green Power Proxy |

#### 7.7.1 Green Power Cluster (Server) - Sink

**Functionality:** Process Green Power frames directly or via proxies

**Support:** Unidirectional and bidirectional GPDs (bidirectional limited to commissioning)

**Attributes:** (Similar to S1 - see S1 documentation)

**Supported Green Power Device Types:**

| Type | Description | Default Commands |
|------|-------------|------------------|
| 0x02 | On/off Switch | on, off, toggle |
| 0x03 | Level Control Switch | move, step, stop (with/without on/off) |
| 0x07 | Generic Switch | press, release (up to 8 buttons) |

**Supported Green Power Commands:**

| Command | Description |
|---------|-------------|
| 0x10-0x17 | Recall scene #1-8 |
| 0x18-0x1F | Store scene #1-8 |
| 0x20 | Turn Off |
| 0x21 | Turn On |
| 0x22 | Toggle |
| 0x30 | Move up |
| 0x31 | Move down |
| 0x32 | Step up |
| 0x33 | Step down |
| 0x34 | Stop |
| 0x35 | Move up with on/off |
| 0x36 | Move down with on/off |
| 0x37 | Step up with on/off |
| 0x38 | Step down with on/off |
| 0x69 | Generic Press |
| 0x6A | Generic Release |

**Generic Switch Commissioning:**

Enhanced support for short (<1s) and long (>1s) presses:

| Contacts | Behavior |
|----------|----------|
| 1 | Short Press: Toggle<br>Long Press: Dim up/down (alternating) |
| 2 | Button A Short: On, Long: Dim up<br>Button B Short: Off, Long: Dim down |
| 3 | Button A: On<br>Button B: Off<br>Button C: Dim up/down (alternating) |
| 4 | Button A: On<br>Button B: Off<br>Button C: Dim up<br>Button D: Dim down |

#### 7.7.2 Green Power Cluster (Client) - Proxy

**Functionality:** Acts as access point for Green Power Devices

**Attributes:** (Similar to S1 - see S1 documentation)

## 8. Physical Dimensions

### D1 (Flush-mount In-wall)

- Width: 47 mm
- Height: 143 mm
- Depth: 43 mm
- Mounting depth: 12 mm
- Cable exit: 12 mm

### D1-R (DIN Rail Mount)

- Width: 18 mm (1 TE/module)
- Height: 90 mm
- Depth: 60.5 mm

## 9. Ordering Information

| Vendor/Brand | Order Code | Description |
|--------------|------------|-------------|
| ubisys | 1045 | ZigBee Universal Dimmer D1 (in-wall, flush-mount) |
| ubisys | 1137 | ZigBee Universal Dimmer D1-R (rail mount) |
| Neonlite/MEGAMAN | ZBM01d | ingenium® ZB Wireless Dimming Module |

**Housing:** Flame retardant (V-0), Black, RAL 9005

**OEM Options:** Dimming mode can be pre-configured to "automatic", "leading edge", or "trailing edge"

## 10. Compliance

### Conformity Declaration

**Manufacturer:** ubisys technologies GmbH, Neumannstraße 10, 40235 Düsseldorf, Germany

**Directives/Standards:**

| Directive/Standard | Description |
|-------------------|-------------|
| 2014/53/EU | Radio Equipment Directive (RED) |
| 2014/30/EU | Electromagnetic Compatibility Directive (EMC) |
| 2014/35/EU | Low Voltage Directive (LVD) |
| 2012/19/EU | Waste Electrical and Electronic Equipment Directive (WEEE) |
| 2011/65/EU | Restriction of Hazardous Substances Directive (RoHS) |
| EN 300 328 V2.2.2 | ERM; Wideband transmission systems; 2.4 GHz ISM band |
| EN 300 440 V2.2.1 | ERM; Radio equipment 1 GHz to 40 GHz |
| EN 301 489-1 V2.1.1 | EMC |
| IEEE 802.15.4:2020 | Low-Rate Wireless Personal Area Networks |
| ZigBee 3.0 | ZigBee 2017 with Green Power |

**Date:** September 16, 2021

## 11. Contact Information

**ubisys technologies GmbH**  
Neumannstraße 10  
40235 Düsseldorf  
Germany

**Phone:** +49 (211) 54 21 55 - 00  
**Fax:** +49 (211) 54 21 55 - 99  
**Web:** www.ubisys.de  
**Email:** info@ubisys.de

### Support Resources

**Consumer/Installer Support:**  
http://www.ubisys.de/en/smarthome/support.html

**Commercial/Engineering Support:**  
http://www.ubisys.de/en/engineering/support.html

**General Terms & Conditions:**  
http://www.ubisys.de/en/smarthome/terms.html

---

*Document Revision: 2.3 (September 16, 2021)*