# Architecture Documentation

This document provides comprehensive architecture diagrams for the Ubisys Home Assistant integration.

## Table of Contents

1. [System Overview](#system-overview)
2. [Calibration Sequence Flow](#calibration-sequence-flow)
3. [Component Interaction](#component-interaction)
4. [State Synchronization](#state-synchronization)
5. [ZHA Quirk Architecture](#zha-quirk-architecture)

---

## System Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Home Assistant                              │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │                  Ubisys Integration                           │ │
│  ├───────────────────────────────────────────────────────────────┤ │
│  │                                                               │ │
│  │  ┌─────────────┐  ┌──────────────┐  ┌──────────────────┐    │ │
│  │  │ Config Flow │  │ Cover Entity │  │ Button Entity    │    │ │
│  │  │ (Setup UI)  │  │ (Wrapper)    │  │ (Calibration)    │    │ │
│  │  └─────────────┘  └──────────────┘  └──────────────────┘    │ │
│  │         │                 │                    │             │ │
│  │         └─────────────────┼────────────────────┘             │ │
│  │                           │                                  │ │
│  │                    ┌──────▼──────────┐                       │ │
│  │                    │  Calibration    │                       │ │
│  │                    │  Module         │                       │ │
│  │                    │  calibration.py │                       │ │
│  │                    └─────────────────┘                       │ │
│  │                           │                                  │ │
│  └───────────────────────────┼──────────────────────────────────┘ │
│                              │                                    │
│  ┌───────────────────────────▼──────────────────────────────────┐ │
│  │                    ZHA Integration                           │ │
│  ├──────────────────────────────────────────────────────────────┤ │
│  │                                                              │ │
│  │  ┌──────────────┐  ┌─────────────────┐  ┌────────────────┐ │ │
│  │  │ ZHA Gateway  │  │ ZHA Cover Entity│  │ Custom Quirk   │ │ │
│  │  │              │  │ (Real Entity)   │  │ (ubisys_j1.py) │ │ │
│  │  └──────────────┘  └─────────────────┘  └────────────────┘ │ │
│  │         │                  │                     │          │ │
│  └─────────┼──────────────────┼─────────────────────┼──────────┘ │
│            │                  │                     │            │
└────────────┼──────────────────┼─────────────────────┼────────────┘
             │                  │                     │
    ┌────────▼──────────────────▼─────────────────────▼────────┐
    │                    Zigbee Network                         │
    ├───────────────────────────────────────────────────────────┤
    │                                                           │
    │              ┌─────────────────────────┐                 │
    │              │   Ubisys J1 Device      │                 │
    │              │  (Physical Hardware)    │                 │
    │              │                         │                 │
    │              │  Endpoint 1: Config     │                 │
    │              │  Endpoint 2: WindowCover│                 │
    │              └─────────────────────────┘                 │
    │                                                           │
    └───────────────────────────────────────────────────────────┘
```

### Key Components

1. **Config Flow**: UI-based setup with auto-discovery and shade type selection
2. **Cover Entity (Wrapper)**: Ubisys-specific cover that filters features based on shade type
3. **Button Entity**: Provides one-click calibration from device page
4. **Calibration Module**: Automated 5-phase calibration with motor stall detection
5. **ZHA Integration**: Standard Home Assistant Zigbee integration
6. **ZHA Cover Entity**: Real entity that communicates with device
7. **Custom Quirk**: Exposes manufacturer-specific attributes (total_steps, tilt_steps, mode)

---

## Calibration Sequence Flow

```
╔═══════════════════════════════════════════════════════════════════╗
║              5-PHASE CALIBRATION SEQUENCE                         ║
╚═══════════════════════════════════════════════════════════════════╝

User Action:
   │
   │  Click "Calibrate" button OR
   │  Call ubisys.calibrate_j1 service
   │
   ▼
┌────────────────────────────────────────────────────────────────────┐
│ VALIDATION & SETUP                                                 │
├────────────────────────────────────────────────────────────────────┤
│ ✓ Validate entity_id parameter                                    │
│ ✓ Verify entity exists and is ubisys platform                     │
│ ✓ Extract device_ieee and shade_type from config                  │
│ ✓ Find ZHA cover entity for monitoring                            │
│ ✓ Acquire device-specific asyncio.Lock                            │
└────────────────────────────────────────────────────────────────────┘
   │
   ▼
┌────────────────────────────────────────────────────────────────────┐
│ PHASE 1: PREPARATION                                (2-3 seconds)  │
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│  Step 1: Write mode attribute = 0x02                              │
│          └─ Enter calibration mode                                │
│          └─ Wait 1s (SETTLE_TIME)                                 │
│                                                                    │
│  Step 2: Write configured_mode based on shade type                │
│          └─ 0x00: Roller/Cellular                                 │
│          └─ 0x04: Vertical blind                                  │
│          └─ 0x08: Venetian blind                                  │
│          └─ Wait 1s (SETTLE_TIME)                                 │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
   │
   ▼
┌────────────────────────────────────────────────────────────────────┐
│ PHASE 2: FIND TOP LIMIT                           (20-40 seconds) │
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│  Step 3: Send up_open command                                     │
│          └─ Motor starts moving upward continuously               │
│                                                                    │
│  Step 4: Monitor position every 0.5s                              │
│          └─ If position unchanged for 3s → STALL DETECTED         │
│          └─ Record final position (typically 100)                 │
│                                                                    │
│  Step 5: Send stop command                                        │
│          └─ Wait 1s (SETTLE_TIME)                                 │
│                                                                    │
│  Result: Top reference point established                          │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
   │
   ▼
┌────────────────────────────────────────────────────────────────────┐
│ PHASE 3: FIND BOTTOM + MEASURE                    (20-40 seconds) │
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│  Step 6: Send down_close command                                  │
│          └─ Motor starts moving downward continuously             │
│          └─ Device counts steps during movement!                  │
│                                                                    │
│  Step 7: Monitor position every 0.5s                              │
│          └─ If position unchanged for 3s → STALL DETECTED         │
│          └─ Record final position (typically 0)                   │
│                                                                    │
│  Step 8: Send stop command                                        │
│          └─ Wait 1s (SETTLE_TIME)                                 │
│                                                                    │
│  Step 9: Read total_steps attribute                               │
│          └─ Device has calculated this during Step 6-7            │
│          └─ Typical values: 1000-20000                            │
│          └─ Validate: must not be 0xFFFF or 0                     │
│                                                                    │
│  Result: Bottom limit found, total_steps measured                 │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
   │
   ▼
┌────────────────────────────────────────────────────────────────────┐
│ PHASE 4: VERIFICATION                             (20-40 seconds) │
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│  Step 10: Send up_open command                                    │
│           └─ Return to top position                               │
│                                                                    │
│  Step 11: Monitor position every 0.5s                             │
│           └─ Should stall at same position as Phase 2             │
│           └─ Confirms calibration was successful                  │
│                                                                    │
│  Step 12: Send stop command                                       │
│           └─ Wait 1s (SETTLE_TIME)                                │
│                                                                    │
│  Result: Calibration verified, blind at fully open position       │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
   │
   ▼
┌────────────────────────────────────────────────────────────────────┐
│ PHASE 5: FINALIZATION                              (2-3 seconds)  │
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│  Step 13: Write lift_to_tilt_transition_steps                     │
│           └─ 0 for roller/cellular/vertical                       │
│           └─ 100 for venetian blinds                              │
│           └─ Wait 1s (SETTLE_TIME)                                │
│                                                                    │
│  Step 14: Write mode attribute = 0x00                             │
│           └─ Exit calibration mode                                │
│           └─ Device returns to normal operation                   │
│                                                                    │
│  Result: Device fully calibrated and ready for use                │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
   │
   ▼
┌────────────────────────────────────────────────────────────────────┐
│ SUCCESS                                                            │
├────────────────────────────────────────────────────────────────────┤
│ ✅ Calibration complete                                           │
│ ✅ Total steps: {value} (e.g., 5000)                              │
│ ✅ Device ready for position/tilt commands                        │
│ ✅ Lock released                                                   │
└────────────────────────────────────────────────────────────────────┘

Total Duration: 60-120 seconds
  - Roller/Cellular: ~60-90s
  - Venetian: ~90-120s

Error Handling:
  - Any phase fails → Attempt to exit calibration mode
  - Lock always released via context manager
  - Clear error messages identify which phase failed
```

---

## Component Interaction

### User Opens Shade

```
User clicks "Open"
     │
     ▼
┌──────────────────────┐
│ Ubisys Cover Entity  │  (cover.bedroom_shade)
│ (Wrapper)            │
└──────────────────────┘
     │
     │ async_open_cover()
     │
     ▼
┌──────────────────────┐
│ ZHA Cover Entity     │  (cover.bedroom_shade_2)
│ (Real Entity)        │
└──────────────────────┘
     │
     │ Zigbee Command
     ▼
┌──────────────────────┐
│ Ubisys J1 Device     │
│ (Hardware)           │
└──────────────────────┘
```

### User Calibrates Device

```
User clicks "Calibrate" button
     │
     ▼
┌──────────────────────────────┐
│ UbisysCalibrationButton      │
│ (button.bedroom_shade_...)   │
└──────────────────────────────┘
     │
     │ Press event
     │
     ▼
┌──────────────────────────────┐
│ hass.services.async_call()   │
│ ubisys.calibrate_j1          │
└──────────────────────────────┘
     │
     ▼
┌──────────────────────────────┐
│ async_calibrate_j1()         │
│ (Service Handler)            │
└──────────────────────────────┘
     │
     ├─ Validate parameters
     ├─ Find ZHA entity
     ├─ Acquire asyncio.Lock
     │
     ▼
┌──────────────────────────────┐
│ _perform_calibration()       │
│ (Orchestrator)               │
└──────────────────────────────┘
     │
     ├─ Get WindowCovering cluster
     ├─ Phase 1: Enter mode
     ├─ Phase 2: Find top
     ├─ Phase 3: Find bottom
     ├─ Phase 4: Verify
     └─ Phase 5: Finalize
     │
     ▼
┌──────────────────────────────┐
│ Direct Zigbee Commands       │
│ via Cluster                  │
└──────────────────────────────┘
     │
     ▼
┌──────────────────────────────┐
│ Ubisys J1 Device             │
└──────────────────────────────┘
```

---

## State Synchronization

The Ubisys cover wrapper delegates all state to the underlying ZHA entity:

```
┌───────────────────────────────────────────────────────────────────┐
│                    State Synchronization                          │
└───────────────────────────────────────────────────────────────────┘

Ubisys J1 Device
     │
     │ Reports state via Zigbee
     ▼
ZHA Cover Entity (cover.bedroom_shade_2)
     │
     │ State: open/closed/opening/closing
     │ Attributes:
     │   - current_position: 0-100
     │   - current_tilt_position: 0-100 (venetian only)
     │   - total_steps: 5000 (from quirk)
     │   - tilt_steps: 100 (from quirk)
     │
     ▼
Ubisys Cover Entity (cover.bedroom_shade)
     │
     │ Reads ZHA entity state
     │ Filters supported_features based on shade_type
     │
     │ If roller/cellular/vertical:
     │   - SUPPORT_OPEN
     │   - SUPPORT_CLOSE
     │   - SUPPORT_STOP
     │   - SUPPORT_SET_POSITION
     │
     │ If venetian:
     │   - SUPPORT_OPEN
     │   - SUPPORT_CLOSE
     │   - SUPPORT_STOP
     │   - SUPPORT_SET_POSITION
     │   - SUPPORT_OPEN_TILT
     │   - SUPPORT_CLOSE_TILT
     │   - SUPPORT_STOP_TILT
     │   - SUPPORT_SET_TILT_POSITION
     │
     ▼
Home Assistant UI
     │
     └─ Shows only relevant controls
```

### Real-time Updates

1. **Device → ZHA**: Zigbee attribute reports (position changes)
2. **ZHA → Ubisys**: State change callback via `async_added_to_hass()`
3. **Ubisys → UI**: `async_write_ha_state()` triggers UI update

---

## ZHA Quirk Architecture

The custom ZHA quirk extends the standard WindowCovering cluster to expose manufacturer-specific attributes:

```
┌───────────────────────────────────────────────────────────────────┐
│                   Custom ZHA Quirk                                │
│              custom_zha_quirks/ubisys_j1.py                       │
└───────────────────────────────────────────────────────────────────┘

Standard Zigbee WindowCovering Cluster (0x0102)
     │
     ├─ Standard Attributes:
     │    - current_position_lift_percentage (0x0008)
     │    - current_position_tilt_percentage (0x0009)
     │
     └─ Standard Commands:
          - up_open
          - down_close
          - stop

          ┌──────────────────────────────────────────┐
          │ UbisysWindowCoveringCluster (Custom)     │
          ├──────────────────────────────────────────┤
          │ Manufacturer: 0x10F2 (Ubisys)            │
          ├──────────────────────────────────────────┤
          │ Additional Attributes:                   │
          │   - 0x0017: mode (calibration mode)      │
          │   - 0x1000: configured_mode (shade type) │
          │   - 0x1001: lift_to_tilt_transition_steps│
          │   - 0x1002: total_steps                  │
          └──────────────────────────────────────────┘
                           │
                           ▼
                   ┌────────────────┐
                   │ Ubisys J1      │
                   │ Quirk          │
                   ├────────────────┤
                   │ signature:     │
                   │  - model: J1   │
                   │  - mfg: ubisys │
                   │                │
                   │ replacement:   │
                   │  - Endpoint 2  │
                   │    └─ Custom   │
                   │       Cluster  │
                   └────────────────┘

Usage in Calibration:

  await cluster.write_attributes(
      {0x0017: 0x02},  # Enter calibration mode
      manufacturer=0x10F2
  )

  result = await cluster.read_attributes(
      ["total_steps"],  # Read 0x1002
      manufacturer=0x10F2
  )
```

### Attribute Details

| Attribute ID | Name | Type | Description |
|--------------|------|------|-------------|
| 0x0017 | mode | uint8 | 0x00=normal, 0x02=calibration |
| 0x1000 | configured_mode | uint8 | Window covering type (0x00/0x04/0x08) |
| 0x1001 | lift_to_tilt_transition_steps | uint16 | Steps for full tilt (0 or 100) |
| 0x1002 | total_steps | uint16 | Total steps from open to closed |

---

## Concurrency Control

The integration uses asyncio.Lock to prevent race conditions during calibration:

```
┌──────────────────────────────────────────────────────────────────┐
│              Concurrency Control Architecture                    │
└──────────────────────────────────────────────────────────────────┘

hass.data[DOMAIN]["calibration_locks"] = {
    "00:12:4b:00:1c:a1:b2:c3": <asyncio.Lock object>,  # Device 1
    "00:12:4b:00:1c:d4:e5:f6": <asyncio.Lock object>,  # Device 2
}

Per-Device Locking:
  - Each device has its own lock
  - Multiple devices can calibrate simultaneously
  - Same device cannot calibrate twice concurrently

Flow:

  Service Call 1 (Device A)              Service Call 2 (Device A)
         │                                        │
         ▼                                        ▼
    Check lock.locked()                      Check lock.locked()
         │                                        │
         ▼                                        ▼
    Lock available                           Lock already held!
         │                                        │
         ▼                                        ▼
    async with lock:                        Raise error:
      └─ Calibrate                          "Already in progress"
      └─ Auto-release

Benefits:
  ✓ Prevents multiple calibrations on same device
  ✓ Prevents TOCTOU race conditions
  ✓ Automatic cleanup via context manager
  ✓ Clear error messages to user
```

---

## Feature Filtering

How the integration shows only relevant controls:

```
┌──────────────────────────────────────────────────────────────────┐
│              Feature Filtering Logic                             │
└──────────────────────────────────────────────────────────────────┘

Config Entry Data:
  shade_type: "roller" | "cellular" | "vertical" | "venetian" | "exterior_venetian"

Feature Determination:

  if shade_type in ["roller", "cellular", "vertical"]:
      supported_features = (
          SUPPORT_OPEN |
          SUPPORT_CLOSE |
          SUPPORT_STOP |
          SUPPORT_SET_POSITION
      )
      # User sees: Position slider only

  elif shade_type in ["venetian", "exterior_venetian"]:
      supported_features = (
          SUPPORT_OPEN |
          SUPPORT_CLOSE |
          SUPPORT_STOP |
          SUPPORT_SET_POSITION |
          SUPPORT_OPEN_TILT |
          SUPPORT_CLOSE_TILT |
          SUPPORT_STOP_TILT |
          SUPPORT_SET_TILT_POSITION
      )
      # User sees: Position slider + Tilt slider

Result in UI:

  Roller Shade               Venetian Blind
  ┌──────────────┐          ┌──────────────┐
  │ ▲ Open       │          │ ▲ Open       │
  │ ▼ Close      │          │ ▼ Close      │
  │ ■ Stop       │          │ ■ Stop       │
  │              │          │              │
  │ Position: ▬▬ │          │ Position: ▬▬ │
  │              │          │ Tilt: ▬▬     │  ← Only on venetian!
  └──────────────┘          └──────────────┘
```

---

## Data Flow Summary

```
User Action → Ubisys Entity → ZHA Entity → Zigbee → Device
                    ↓              ↓          ↓        ↓
                 Filter        Translate   Cluster  Physical
                Features       to Zigbee   Command   Motor

Device State → Zigbee → ZHA Entity → Ubisys Entity → UI
                  ↓         ↓            ↓             ↓
              Attribute   Parse &      Filter &     Display
              Report      Update       Delegate     to User
```
