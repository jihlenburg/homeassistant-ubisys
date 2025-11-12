# ubisys ZigBee Power Switch S1/S1-R - Technical Reference Manual

## 1. Overview

The ubisys power switch S1 is a ZigBee load switch with integrated smart meter, also known as Smart Power Outlet.

**Product Information:**
- **Manufacturer:** ubisys technologies GmbH, Düsseldorf, Germany
- **Manufacturer ID:** 0x10F2
- **Models:**
  - S1 (5501): In-wall flush-mount version with one input
  - S1-R (5601): DIN rail mount version with two inputs
- **Copyright:** 2014-2021 ubisys technologies GmbH

## 2. Key Features

### Hardware Features
- **ZigBee 3.0 Certified** Load Switch with Integrated Smart Meter and Router functionality
- **Power Rating:** 230V~, 16A, 3,680VA
- **Inputs:**
  - S1: One configurable 230V~ input (pre-configured for local output control)
  - S1-R: Two configurable 230V~ inputs (one pre-configured for local output control)
- **Relay:** Latching relay with mains-synchronized switching
- **Power Dissipation:** 0.3W
- **Housing:** Flame retardant (V-0), Black, RAL 9005
- **Made in Germany**

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
2. ZigBee 3.0 Global Distributed Security Link-Key
3. Device-individual link-key derived from installation code (printed as text and QR barcode)

### Input Configuration
Inputs can be individually reconfigured as:
- On/off switches
- Level control switches
- Scene selector switches
- Compatible with momentary or stationary switches

### Additional Features
- Local control works even when not joined to a network
- Supports groups, scenes, bindings, and reporting
- Maintains output switching state during reboot
- Firmware upgradable over-the-air (OTA)
- Man-Machine-Interface: Push-button and LED

## 3. Installation

### 3.1 Mains Powered Operation
Refer to the hardware installation guide included in the product package for detailed installation instructions.

### 3.2 Low-Voltage Operation (Maintenance/Testing)
For testing or maintenance purposes, the S1 can operate from a low-voltage DC source (12V=, 24V=, or 48V=):
- Connect DC ground (0V, negative) to phase input (marked "L", brown)
- Connect DC supply voltage to neutral input (marked "N", blue)
- **Note:** In DC mode, ZigBee interface is operational but inputs/outputs are non-operational

## 4. Initial Device Start-up

**Startup Behavior:**
1. Device searches for an open ZigBee network when first powered
2. LED blinks quickly during search
3. **Success:** Blinks five times slowly (joined as router) or ten times slowly (operating as coordinator)
4. **Failure:** Blinks three times quickly, continues searching

**After Power-Cycle:**
- Router: Blinks five times slowly, then LED remains off during normal operation
- Coordinator: Blinks ten times slowly
- Searching: Blinks quickly
- LED turns on when network is open for joining

**Network Behavior:**
- Performs "silent rejoin" after reboot (no device announcement)
- After joining, extends joining window by 3 minutes via ZDO permit joining request

## 5. Man-Machine Interface (MMI)

### 5.1 Physical Interface
- **Button:** Push-button behind small hole in front face
- **LED:** Located next to button

### 5.2 Factory Reset Shortcut
Press and hold button for approximately **10 seconds** until LED starts flashing (equivalent to menu item #5).

### 5.3 Menu System

**Entering Menu:**
1. Press and hold button for >1 second
2. Three short flashes followed by one blink, pause, one blink... indicates menu entry
3. Short presses (<1 second) advance through menu items
4. LED blinks show current menu item number
5. Press and hold >1 second to execute selected item

**Menu Items (Firmware 1.04+):**

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

Alternative method to factory reset without physical button access:

1. Power device for at least 4 seconds
2. Interrupt power for at least 1 second
3. Reapply power for 0.5-2 seconds
4. Repeat step 3 two more times (total of 3 short power cycles)
5. Apply power and leave powered on
6. Device will factory reset and reboot

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

#### S1 Endpoints

| Endpoint | Profile | Application | Description |
|----------|---------|-------------|-------------|
| 0 (0x00) | 0x0000: ZigBee Device Profile | ZigBee Device Object (ZDO) | Standard management features |
| 1 (0x01) | 0x0104: Common Profile (HA) | On/off Plug-in Unit (0x010A) | Controls output via on/off cluster. Supports groups, scenes, reporting. |
| 2 (0x02) | 0x0104: Common Profile (HA) | Level Control Switch (0x0001) | Transmits on/off, level control, or scene commands from local input |
| 3 (0x03) | 0x0104: Common Profile (HA) | Metering (0x0702) | Provides metering and electrical measurement |
| 200 (0xC8) | Private | Private | Legacy private application (deprecated) |
| 232 (0xE8) | 0x0104: Common Profile (HA) | Device Management (0x0507) | Device management and configuration |
| 242 (0xF2) | 0xA1E0: Green Power Profile | ZigBee Green Power | Combined Proxy and Sink |

#### S1-R Endpoints

| Endpoint | Profile | Application | Description |
|----------|---------|-------------|-------------|
| 0 (0x00) | 0x0000: ZigBee Device Profile | ZigBee Device Object (ZDO) | Standard management features |
| 1 (0x01) | 0x0104: Common Profile (HA) | Mains Power Outlet (0x0009) | Controls output via on/off cluster |
| 2 (0x02) | 0x0104: Common Profile (HA) | Level Control Switch (0x0001) | Primary input control |
| 3 (0x03) | 0x0104: Common Profile (HA) | Level Control Switch (0x0001) | Secondary input control |
| 4 (0x04) | 0x0104: Common Profile (HA) | Metering (0x0702) | Provides metering and electrical measurement |
| 200 (0xC8) | Private | Private | Legacy private application (deprecated) |
| 232 (0xE8) | 0x0104: Common Profile (HA) | Device Management (0x0502) | Device management and configuration |

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

Supported ZDO Services:

| Service | Description |
|---------|-------------|
| nwk_addr_req/rsp | Network address translation (64-bit to 16-bit) |
| ieee_addr_req/rsp | IEEE address translation (16-bit to 64-bit) |
| node_desc_req/rsp | Node descriptor (manufacturer ID, power supply, etc.) |
| power_desc_req/rsp | Power descriptor |
| active_ep_req/rsp | Active endpoints list |
| simple_desc_req/rsp | Simple descriptor for endpoint |
| match_desc_req/rsp | Search for clusters |
| device_annce | Device announcement |
| parent_annce/rsp | Parent announcement (ZigBee 2015 child management) |
| system_server_discovery_req/rsp | Discover system servers |
| bind_req/rsp | Create application binding |
| unbind_req/rsp | Remove application binding |
| mgmt_nwk_disc_req/rsp | Network discovery |
| mgmt_lqi_req/rsp | Neighbor table information |
| mgmt_rtg_req/rsp | Routing table information |
| mgmt_bind_req/rsp | Binding table information |
| mgmt_leave_req/rsp | Leave network |
| mgmt_permit_joining_req/rsp | Open network for joining |
| mgmt_nwk_update_req/notify | Energy scans, channel change, network manager |

### 7.2 Endpoint #1 - Mains Power Outlet

**Purpose:** Controls the load output (relay)

**Finding & Binding:** Target endpoint

#### Clusters

| Cluster | Direction | Description |
|---------|-----------|-------------|
| 0x0000 | Server | Basic - Device information |
| 0x0003 | Server | Identify - Identify mode control |
| 0x0004 | Server | Groups - Group management |
| 0x0005 | Server | Scenes - Scene management |
| 0x0006 | Server | On/off - Relay control |

#### 7.2.1 Identify Cluster

**Identify Mode:** Toggles output relay once per second

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
| 0x40 | Trigger Effect - Initiate visual effect |

#### 7.2.2 Groups Cluster

**Attributes:**

| Attribute | Type | Description |
|-----------|------|-------------|
| 0x0000 | bitmap8, read-only | NameSupport - Always 0 (names not supported) |

**Commands:**

| Command | Description |
|---------|-------------|
| 0x00 | Add Group |
| 0x01 | View Group |
| 0x02 | Get Group Membership |
| 0x03 | Remove Group |
| 0x04 | Remove All Groups |
| 0x05 | Add Group if Identifying |

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

**Note:** Uses binding table for reporting targets. No default reporting configuration - must be configured manually.

**Attributes:**

| Attribute | Type | Description |
|-----------|------|-------------|
| 0x0000 | bool, read-only, reportable | OnOff - Current relay state |
| 0x4000 | bool, read-only | GlobalSceneControl - Next "Off with Effect" stores global scene |
| 0x4001 | unsigned16, read-only | OnTime - Auto-off countdown (0.1s units) |
| 0x4002 | unsigned16, read-only | OffWaitTime - Command ignore countdown (0.1s units) |
| 0x4003 | enum8, persistent | StartupOnOff - Startup behavior: 0x00=off, 0x01=on, 0xFF=restore, 0x02=invert |

**Commands:**

| Command | Description |
|---------|-------------|
| 0x00 | Turn off |
| 0x01 | Turn on |
| 0x02 | Toggle |
| 0x40 | Off with effect |
| 0x41 | On with recall global scene |
| 0x42 | On with timed off |

### 7.3 Endpoint #2 (S1/S1-R) - Primary Level Control Switch

**Purpose:** Controls remote devices via local input

**Finding & Binding:** Initiator endpoint

**Default Binding (S1):** Bound to Endpoint #1 (enables local control even when not commissioned)

#### Clusters

| Cluster | Direction | Description |
|---------|-----------|-------------|
| 0x0000 | Server | Basic |
| 0x0003 | Server | Identify (no visual feedback) |
| 0x0005 | Client | Scenes (firmware 1.04+) |
| 0x0006 | Client | On/off |
| 0x0008 | Client | Level Control (firmware 1.04+) |

#### 7.3.1 Scenes Cluster (Client)

**Note:** Does not use binding table. Uses Device Setup cluster to configure behavior.

**Commands Transmitted:**

| Command | Description |
|---------|-------------|
| 0x05 | Recall Scene - Group address used as target |

#### 7.3.2 On/off Cluster (Client)

**Note:** Uses binding table for command targets.

**Configuration:** Use Device Setup cluster to configure behavior (push-button vs. rocker switch)

**Commands Transmitted:**

| Command | Description |
|---------|-------------|
| 0x00 | Turn off |
| 0x01 | Turn on |
| 0x02 | Toggle (avoid for groups) |

#### 7.3.3 Level Control Cluster (Client)

**Note:** Uses binding table. Not bound by default. Configure via Device Setup cluster.

**Commands Transmitted:**

| Command | Description |
|---------|-------------|
| 0x05 | Move with on/off |
| 0x07 | Stop with on/off |

### 7.4 Endpoint #3 (S1-R) - Secondary Level Control Switch

Same as Endpoint #2 but for the second input on S1-R.

### 7.5 Endpoint #3 (S1) / #4 (S1-R) - Metering

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
| 0x0510 | signed8, read-only | PowerFactor (L1) - Phase L1 power factor (0.01 units)<br>Positive = inductive (L), Negative = capacitive (C), ~0 = resistive (R) |

### 7.6 Endpoint #232 - Device Management

**Purpose:** Device configuration and management

#### Clusters

| Cluster | Direction | Description |
|---------|-----------|-------------|
| 0x0000 | Server | Basic |
| 0x0003 | Client | Identify |
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
| 0x0005 | string, read-only | ModelIdentifier - "S1 (5501)" or "S1-R (5601)" |
| 0x0006 | string, read-only | DateCode - Format: "YYYYMMDD-XX-FBV" |
| 0x0007 | enum8, read-only | PowerSource - Mains-powered, single phase |
| 0x0010 | string, persistent | LocationDescription - Empty by default |
| 0x0011 | unsigned8, persistent | PhysicalEnvironment - "Unspecified" by default |

**Commands:**

| Command | Description |
|---------|-------------|
| 0x00 | Reset to factory defaults (deprecated in firmware 1.06+) |

#### 7.6.2 OTA Upgrade Cluster

**Image Types:**
- S1: 0x7B02
- S1-R: 0x7B05

#### 7.6.3 Device Setup Cluster (0xFC00)

**Purpose:** Configure advanced device options not covered by standard clusters

**Attributes:**

| Attribute | Type | Description |
|-----------|------|-------------|
| 0x0000 | array of data8, persistent | InputConfigurations - One entry per physical input |
| 0x0001 | array of raw data, persistent | InputActions - Maps inputs to endpoints and commands |

##### InputConfigurations Attribute

**Data Type:** Array of 8-bit data (0x48 containing 0x08 elements)

**S1 Elements:**

| Element | Description | Factory Default |
|---------|-------------|-----------------|
| 0x0000 | High-voltage physical input (white cable) | 0x00 |

**S1-R Elements:**

| Element | Description | Factory Default |
|---------|-------------|-----------------|
| 0x0000 | High-voltage physical input #1 | 0x00 |
| 0x0001 | High-voltage physical input #2 | 0x00 |

**Bit Flags:**

| Bit | Flag | Description |
|-----|------|-------------|
| 7 | Disable | When set, input is disabled |
| 6 | Invert | Active-high (cleared) vs. active-low (set)<br>Normally open: clear; Normally closed: set |
| 5-0 | RFU | Reserved for future use (write as 0) |

##### InputActions Attribute

**Data Type:** Array of raw binary data (0x48 containing 0x41 elements)

**Purpose:** Flexible reconfiguration of commands sent in response to input activity

**Element Structure:**

| Field | Type | Description |
|-------|------|-------------|
| InputAndOptions | unsigned8 | 4-bit input index (LSBs) + 4 option flags (MSBs) |
| Transition | unsigned8 | Level transition specification |
| Endpoint | unsigned8 | Source endpoint (S1: #2; S1-R: #2 or #3) |
| ClusterID | unsigned16 | Cluster ID for ZCL command |
| CommandTemplate | raw data | Variable-length ZCL command payload |

**InputAndOptions:**
- Bits 3-0: Physical input number (S1: 0; S1-R: 0 or 1)
- Bits 7-4: Reserved (write as 0)

**Transition Bits:**

| Bit(s) | Field | Description |
|--------|-------|-------------|
| 7 | HasAlternate | Another instruction executes in alternating order |
| 6 | Alternate | This is the alternate instruction |
| 5-4 | RFU | Reserved (write as 0) |
| 3-2 | Initial State | 00=Ignore, 01=Pressed, 10=Kept pressed, 11=Released |
| 1-0 | Final State | 00=Ignore, 01=Pressed, 10=Kept pressed, 11=Released |

**Default Configuration Example (S1 - Rocker Switch):**

```
41          - Element type: 0x41 (raw data)
02 00       - Element count: 2 entries
06          - Element #1: 6 bytes
  00        - InputAndOptions: 0x00
  0D        - Transition: released -> pressed
  02        - Source: Endpoint #2
  06 00     - Cluster ID: 0x0006 (on/off)
  02        - Command: Toggle
06          - Element #2: 6 bytes
  00        - InputAndOptions: 0x00
  03        - Transition: any state -> released
  02        - Source: Endpoint #2
  06 00     - Cluster ID: 0x0006 (on/off)
  02        - Command: Toggle
```

**Default Configuration Example (S1-R - Push-buttons):**

```
41          - Element type: 0x41 (raw data)
02 00       - Element count: 2 entries
06          - Element #1: 6 bytes
  00        - InputAndOptions: 0x00
  0D        - Transition: released -> pressed
  02        - Source: Endpoint #2
  06 00     - Cluster ID: 0x0006 (on/off)
  02        - Command: Toggle
06          - Element #2: 6 bytes
  01        - InputAndOptions: 0x01
  0D        - Transition: released -> pressed
  03        - Source: Endpoint #3
  06 00     - Cluster ID: 0x0006 (on/off)
  02        - Command: Toggle
```

### 7.7 Endpoint #242 - ZigBee Green Power

**Purpose:** Green Power Proxy and Sink functionality

**Specification:** ZigBee 2015 edition with IEEE EUI-64 and bidirectional commissioning support

#### Clusters

| Cluster | Direction | Description |
|---------|-----------|-------------|
| 0x0021 | Server | Green Power Sink |
| 0x0021 | Client | Green Power Proxy |

#### 7.7.1 Green Power Cluster (Server) - Sink

**Functionality:** Process Green Power frames directly or via proxies

**Support:** Unidirectional and bidirectional GPDs

**Attributes:**

| Attribute | Type | Description |
|-----------|------|-------------|
| 0x0000 | unsigned8, read-only | gpsMaxSinkTableEntries |
| 0x0001 | extended raw binary, read-only, persistent | SinkTable |
| 0x0002 | bitmap8 | gpsCommunicationMode |
| 0x0003 | bitmap8 | gpsCommissioningExitMode |
| 0x0004 | unsigned16 | gpsCommissioningWindow - Timeout in seconds |
| 0x0005 | bitmap8, persistent | gpsSecurityLevel |
| 0x0006 | bitmap24, read-only | gpsFunctionality |
| 0x0007 | bitmap24, read-only | gpsActiveFunctionality |
| 0x0020 | bitmap8, persistent | gpSharedSecurityKeyType |
| 0x0021 | key128, persistent | gpSharedSecurityKey |
| 0x0022 | key128, persistent | gpLinkKey |

**Commands Supported:**

| Command | Description |
|---------|-------------|
| 0x00 | GP Notification - Tunnel GP frames to sinks |
| 0x04 | GP Commissioning Notification |
| 0x05 | GP Sink Commissioning Mode |
| 0x09 | GP Pairing Configuration |
| 0x0A | GP Sink Table Request |

**Commands Transmitted:**

| Command | Description |
|---------|-------------|
| 0x01 | GP Pairing |
| 0x02 | GP Proxy Commissioning Mode |
| 0x06 | GP Response |
| 0x0A | GP Sink Table Response |

**Supported Green Power Device Types:**

| Type | Description | Default Commands |
|------|-------------|------------------|
| 0x02 | On/off Switch | on, off, toggle |
| 0x07 | Generic Switch | press, release (up to 8 buttons) |

**Supported Green Power Commands:**

| Command | Description |
|---------|-------------|
| 0x10-0x17 | Recall scene #1-8 |
| 0x18-0x1F | Store scene #1-8 |
| 0x20 | Turn Off |
| 0x21 | Turn On |
| 0x22 | Toggle |
| 0x69 | Generic Press |
| 0x6A | Generic Release |

**Generic Switch Commissioning:**

Enhanced support for short (<1s) and long (>1s) presses. Behavior depends on number of commissioned contacts:

| Contacts | Behavior |
|----------|----------|
| 1 | Press: Toggle |
| 2 | Button A: On, Button B: Off |
| 3 | Button A: On, Button B: Off, Button C: Toggle |
| 4 | Button A: On, Button B: Off, Button C: Toggle, Button D: Toggle |

#### 7.7.2 Green Power Cluster (Client) - Proxy

**Functionality:** Acts as access point for Green Power Devices

**Attributes:**

| Attribute | Type | Description |
|-----------|------|-------------|
| 0x0010 | unsigned8, read-only | gppMaxProxyTableEntries |
| 0x0011 | extended raw binary, read-only, persistent | ProxyTable |
| 0x0016 | bitmap24, read-only | gppFunctionality |
| 0x0017 | bitmap24, read-only | gppActiveFunctionality |
| 0x0020 | bitmap8, persistent | gpSharedSecurityKeyType |
| 0x0021 | key128, persistent | gpSharedSecurityKey |
| 0x0022 | key128, persistent | gpLinkKey |

**Commands Supported:**

| Command | Description |
|---------|-------------|
| 0x01 | GP Pairing |
| 0x02 | GP Proxy Commissioning Mode |
| 0x06 | GP Response |
| 0x0B | GP Proxy Table Request |

**Commands Transmitted:**

| Command | Description |
|---------|-------------|
| 0x00 | GP Notification |
| 0x04 | GP Commissioning Notification |
| 0x0B | GP Proxy Table Response |

## 8. Physical Dimensions

### S1 (Flush-mount In-wall)

- Width: 47 mm
- Height: 143 mm
- Depth: 43 mm
- Mounting depth: 12 mm
- Cable exit: 17 mm

### S1-R (DIN Rail Mount)

- Width: 18 mm (1 TE/module)
- Height: 90 mm
- Depth: 60.5 mm

## 9. Ordering Information

| Order Code | Description |
|------------|-------------|
| 1052 | ZigBee Power Switch S1 (in-wall, flush-mount) |
| 1151 | ZigBee Power Switch S1-R (rail mount) |

**Housing:** Flame retardant (V-0), Black, RAL 9005

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

*Document Revision: 2.0 (September 16, 2021)*