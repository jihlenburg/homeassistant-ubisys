# Ubisys Integration Architecture Overview

This document provides a high-level overview of the Ubisys Home Assistant integration architecture, designed to support multiple Ubisys device types.

## Integration Philosophy

This integration enhances Home Assistant's Zigbee Home Automation (ZHA) support for Ubisys devices by:

1. **Auto-Discovery**: Automatically detects Ubisys devices when paired with ZHA
2. **Device-Specific Features**: Exposes manufacturer-specific capabilities via custom ZHA quirks
3. **Enhanced UX**: Provides improved user interfaces tailored to each device type
4. **Calibration Services**: Offers automated calibration for devices that require it
5. **Feature Filtering**: Shows only relevant controls based on device type and configuration

---

## Supported Device Types

### Window Covering Devices

**Models:** J1, J1-R (DIN rail variant)

**Platforms:** `cover`, `button`

**Special Features:**
- Automated 5-phase calibration with motor stall detection
- Shade type configuration (roller, cellular, vertical, venetian)
- Smart feature filtering (position-only vs position+tilt)
- One-click calibration button

**Documentation:** See [Window Covering Architecture](window_covering_architecture.md)

### Power Switches (Planned)

**Models:** S1, S1-R, S2, S2-R

**Platforms:** `switch`

**Special Features:**
- Energy metering (S1: 0.5% accuracy)
- Dual-channel control (S2)
- High-current switching (S1: 16A, 3680VA)

**Status:** Not yet implemented

### Dimmers (Planned)

**Models:** D1, D1-R

**Platforms:** `light`

**Special Features:**
- Configurable dimming modes (automatic, forward phase, reverse phase)
- Wide compatibility with different load types

**Status:** Not yet implemented

---

## Integration Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      Home Assistant                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌────────────────────────────────────────────────────────────┐│
│  │              Ubisys Integration (DOMAIN)                   ││
│  ├────────────────────────────────────────────────────────────┤│
│  │                                                            ││
│  │  Core Components:                                          ││
│  │  ├─ Auto-Discovery (ZHA device listener)                  ││
│  │  ├─ Config Flow (device setup UI)                         ││
│  │  ├─ Service Registration (calibration, etc.)              ││
│  │  └─ Platform Coordination                                 ││
│  │                                                            ││
│  │  Device-Specific Platforms:                               ││
│  │  ├─ cover.py        (J1 wrapper with feature filtering)   ││
│  │  ├─ button.py       (J1 calibration button)               ││
│  │  ├─ switch.py       (S1/S2 - planned)                     ││
│  │  └─ light.py        (D1 - planned)                        ││
│  │                                                            ││
│  │  Services:                                                 ││
│  │  └─ calibration.py  (Window covering calibration)         ││
│  │                                                            ││
│  └────────────────────────────────────────────────────────────┘│
│                              │                                  │
│  ┌───────────────────────────▼────────────────────────────────┐│
│  │                    ZHA Integration                         ││
│  ├────────────────────────────────────────────────────────────┤│
│  │  - Device Pairing                                          ││
│  │  - Zigbee Communication                                    ││
│  │  - Cluster Management                                      ││
│  │  - Entity Creation (ZHA entities)                          ││
│  │  - Custom Quirk Loading                                    ││
│  └────────────────────────────────────────────────────────────┘│
│                              │                                  │
└──────────────────────────────┼──────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────┐
│                  Custom ZHA Quirks                              │
├─────────────────────────────────────────────────────────────────┤
│  custom_zha_quirks/                                             │
│  ├─ ubisys_j1.py     (WindowCovering cluster extensions)       │
│  ├─ ubisys_s1.py     (Planned: Switch cluster extensions)      │
│  ├─ ubisys_s2.py     (Planned: Dual switch extensions)         │
│  └─ ubisys_d1.py     (Planned: Dimmer cluster extensions)      │
│                                                                 │
│  Quirks expose manufacturer-specific attributes:                │
│  - 0x10F2 (Ubisys manufacturer code)                            │
│  - Device-specific attributes (calibration, metering, etc.)     │
└─────────────────────────────────────────────────────────────────┘
                               │
                               ▼
                    ┌──────────────────┐
                    │  Zigbee Network  │
                    │  Ubisys Devices  │
                    └──────────────────┘
```

---

## Data Flow

### Device Discovery Flow

```
1. User pairs Ubisys device with ZHA
         │
         ▼
2. ZHA creates device and emits ZHA_DEVICE_ADDED signal
         │
         ▼
3. Ubisys integration listener receives signal
         │
         ▼
4. Check manufacturer == "ubisys" && model in SUPPORTED_MODELS
         │
         ▼
5. Trigger config flow (async_init with source="zha")
         │
         ▼
6. Config flow shows device-specific setup:
    - J1: Shade type selection
    - S1/S2: No configuration needed (future)
    - D1: Dimming mode selection (future)
         │
         ▼
7. Create config entry
         │
         ▼
8. Setup platforms based on device type
         │
         ▼
9. Hide original ZHA entity (if creating wrapper)
         │
         ▼
10. Device ready to use
```

### Command Flow (Cover Example)

```
User clicks "Open" on J1 cover
         │
         ▼
UbisysCover.async_open_cover()
         │
         ▼
Delegate to ZHA cover entity
         │
         ▼
ZHA sends Zigbee command
         │
         ▼
Device executes command
         │
         ▼
Device reports new state
         │
         ▼
ZHA updates entity state
         │
         ▼
Ubisys wrapper syncs state
         │
         ▼
UI updates
```

### State Synchronization

```
Ubisys Device
    ↓ (Zigbee attribute reports)
ZHA Entity (real entity)
    ↓ (state change callback)
Ubisys Wrapper Entity (filtered features)
    ↓ (async_write_ha_state)
Home Assistant UI
```

---

## Device Type Handling

The integration uses a device model mapping to determine capabilities:

```python
# Device categorization
WINDOW_COVERING_MODELS = ["J1", "J1-R"]
SWITCH_MODELS = ["S1", "S1-R", "S2", "S2-R"]
DIMMER_MODELS = ["D1", "D1-R"]

# Platform mapping
DEVICE_PLATFORMS = {
    "J1": [Platform.COVER, Platform.BUTTON],
    "J1-R": [Platform.COVER, Platform.BUTTON],
    "S1": [Platform.SWITCH],        # Planned
    "S1-R": [Platform.SWITCH],      # Planned
    "S2": [Platform.SWITCH],        # Planned
    "S2-R": [Platform.SWITCH],      # Planned
    "D1": [Platform.LIGHT],         # Planned
    "D1-R": [Platform.LIGHT],       # Planned
}

# Capability detection
def supports_calibration(model: str) -> bool:
    return model in WINDOW_COVERING_MODELS
```

---

## Key Design Decisions

### 1. Wrapper Pattern for Covers

**Why:** ZHA creates generic cover entities that show all WindowCovering features (position + tilt) regardless of actual device capabilities. Our wrapper filters features based on shade type.

**How:**
- ZHA entity remains (hidden from UI)
- Ubisys wrapper delegates all commands to ZHA entity
- Wrapper overrides `supported_features` based on shade type
- State synced via callback in `async_added_to_hass()`

**Benefit:** Users see only controls relevant to their shade type

### 2. Direct Cluster Access for Calibration

**Why:** Calibration requires:
- Manufacturer-specific attribute access (mode, total_steps)
- Precise command timing (up_open → wait → stop)
- Low-level control not available via cover entity

**How:**
- Get WindowCovering cluster directly from ZHA gateway
- Send commands via `cluster.command()`
- Read/write attributes via `cluster.read_attributes()` / `cluster.write_attributes()`

**Benefit:** Full control over calibration sequence

### 3. Per-Device Locking

**Why:** Prevent concurrent calibrations on same device (motor damage risk)

**How:**
- asyncio.Lock per device IEEE address
- Non-blocking check before acquiring lock
- Automatic release via context manager

**Benefit:** Safe concurrent calibrations on different devices

### 4. Auto-Discovery

**Why:** Simplify setup - no manual configuration needed

**How:**
- Listen for ZHA_DEVICE_ADDED signal
- Check manufacturer + model
- Auto-trigger config flow with pre-populated data

**Benefit:** Seamless user experience

---

## File Organization

```
custom_components/ubisys/
├── __init__.py              # Integration setup, discovery, service registration
├── const.py                 # Constants, device mappings, feature definitions
├── config_flow.py           # UI-based configuration flow
├── cover.py                 # Window covering wrapper entity (J1)
├── button.py                # Calibration button entity (J1)
├── calibration.py           # Window covering calibration service
├── manifest.json            # Integration metadata
├── services.yaml            # Service definitions
├── strings.json             # UI strings
└── translations/
    └── en.json              # English translations

custom_zha_quirks/
├── ubisys_j1.py             # J1 WindowCovering cluster extensions
├── ubisys_s1.py             # Planned: S1 quirk
├── ubisys_s2.py             # Planned: S2 quirk
└── ubisys_d1.py             # Planned: D1 quirk

docs/
├── architecture_overview.md          # This file (integration-level)
├── window_covering_architecture.md   # J1-specific architecture
├── j1_calibration.md                 # J1 calibration guide
├── development.md                    # Development guide
└── troubleshooting.md                # Troubleshooting guide
```

---

## Extension Points

### Adding New Device Types

1. **Add model to constants:**
   ```python
   # const.py
   SWITCH_MODELS = ["S1", "S1-R", "S2", "S2-R"]
   DEVICE_PLATFORMS["S1"] = [Platform.SWITCH]
   ```

2. **Create platform file:**
   ```python
   # switch.py
   class UbisysSwitch(SwitchEntity):
       """Ubisys switch entity."""
   ```

3. **Create ZHA quirk:**
   ```python
   # custom_zha_quirks/ubisys_s1.py
   class UbisysS1(CustomDevice):
       """Ubisys S1 quirk."""
   ```

4. **Update config flow:**
   ```python
   # config_flow.py
   if device_type == "switch":
       # No extra config needed for switches
       return self.async_create_entry(...)
   ```

### Adding New Services

1. **Define service constant:**
   ```python
   # const.py
   SERVICE_RESET_ENERGY = "reset_energy_meter"  # Example for S1
   ```

2. **Create service handler:**
   ```python
   # energy.py (new file)
   async def async_reset_energy_meter(hass, call):
       """Reset energy meter for S1 device."""
   ```

3. **Register service:**
   ```python
   # __init__.py
   hass.services.async_register(
       DOMAIN,
       SERVICE_RESET_ENERGY,
       async_reset_energy_meter
   )
   ```

4. **Document service:**
   ```yaml
   # services.yaml
   reset_energy_meter:
     name: Reset Energy Meter
     description: Reset the energy meter on S1 devices
   ```

---

## Testing Strategy

### Unit Tests (Planned)

- Config flow for different device types
- Feature filtering logic
- Service parameter validation
- Platform setup logic

### Integration Tests (Planned)

- Auto-discovery flow
- Entity creation
- State synchronization
- Service calls

### Manual Testing

- Real device pairing (J1, J1-R, S1, S2, D1 when available)
- Calibration sequences
- UI appearance
- Error handling

---

## Performance Considerations

### Memory

- One asyncio.Lock per device (lightweight)
- Config entry data cached in `hass.data[DOMAIN]`
- No persistent storage except config entries

### Network

- Commands sent directly via Zigbee (local, fast)
- State updates pushed by devices (efficient)
- No cloud dependencies

### CPU

- Event listeners run asynchronously (non-blocking)
- Calibration polling uses asyncio.sleep (cooperative multitasking)
- No CPU-intensive operations

---

## Security Considerations

### Input Validation

- Entity ID type checking (must be string)
- Platform verification (must be ubisys entity)
- IEEE address format validation
- Parameter bounds checking

### Concurrency Control

- Per-device locking prevents race conditions
- Atomic check-and-lock operation (no TOCTOU)
- Automatic lock release (no deadlocks)

### Access Control

- Services respect Home Assistant user permissions
- Config flow requires admin access
- No external network access

---

## Future Enhancements

### Planned

- S1/S2 power switch support
- D1 dimmer support
- Energy metering dashboard (S1)
- Multi-language support

### Under Consideration

- J1-R rail-mount variant
- Scene support for preset positions
- Position offset configuration
- Speed control configuration
- Web-based calibration wizard

---

## Version History

### v1.1.1 (Current)
- J1 window covering support
- Auto-discovery
- Automated calibration with motor stall detection
- Smart feature filtering

### v1.0.0
- Initial release
- J1 basic support

---

## Related Documentation

- [Window Covering Architecture](window_covering_architecture.md) - J1-specific details
- [J1 Calibration Guide](j1_calibration.md) - Calibration process
- [Development Guide](development.md) - Contributing to the integration
- [Troubleshooting](troubleshooting.md) - Common issues and solutions
