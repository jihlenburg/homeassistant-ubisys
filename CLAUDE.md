# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Home Assistant custom integration for Ubisys Zigbee window covering controllers (J1 model). The integration has four main components:

1. **Custom Integration** (`custom_components/ubisys/`) - A wrapper integration that filters features based on shade type
   - Cover platform (`cover.py`) - Wrapper entity with feature filtering
   - Button platform (`button.py`) - Calibration button for easy UI access
2. **ZHA Quirk** (`custom_zha_quirks/ubisys_j1.py`) - Extends ZHA with Ubisys manufacturer-specific attributes
3. **Calibration Script** (`python_scripts/ubisys_j1_calibrate.py`) - Automated calibration sequence

**UI Enhancements:**
- Cover entity exposes `shade_type` as a state attribute for visibility in UI
- Calibration button entity provides one-click calibration from device page
- No need to navigate to Developer Tools → Services

## Architecture

### Three-Layer Design

```
User → Ubisys Cover Entity → ZHA Cover Entity → Zigbee Device
```

**Critical architectural pattern**: The Ubisys cover entity (`cover.py`) is a **wrapper**, not a replacement. It:
- Listens for state changes from the underlying ZHA entity via event listener
- Filters `supported_features` based on configured shade type
- Delegates all commands to the underlying ZHA entity (never talks to Zigbee directly)
- Must maintain state synchronization through `_async_update_from_zha()`

### Shade Type Feature Filtering

The core value proposition is filtering Home Assistant's cover features based on physical shade capabilities:

- **Position-only shades** (roller/cellular/vertical): OPEN, CLOSE, STOP, SET_POSITION
- **Position+tilt shades** (venetian): All position features + OPEN_TILT, CLOSE_TILT, STOP_TILT, SET_TILT_POSITION

Mapping defined in `const.py` as `SHADE_TYPE_TO_FEATURES` and `SHADE_TYPE_TO_WINDOW_COVERING_TYPE`.

### ZHA Quirk Auto-Injection Pattern

`custom_zha_quirks/ubisys_j1.py` overrides `read_attributes()` and `write_attributes()` to **automatically inject** the Ubisys manufacturer code (0x10F2) when accessing manufacturer-specific attributes:

- `0x1000` - configured_mode
- `0x1001` - lift_to_tilt_transition_steps
- `0x1002` - total_steps

This allows the rest of the integration to access these attributes without specifying the manufacturer code each time.

### Calibration Sequence

The calibration script (`python_scripts/ubisys_j1_calibrate.py`) executes a 7-step sequence:

1. Set `WindowCoveringType` based on shade type
2. Move to fully open (via Home Assistant cover service)
3. Write 0 to `current_position_lift` attribute (reset counter)
4. Move to fully closed (while device counts steps)
5. Read `total_steps` attribute (manufacturer-specific)
6. Read `lift_to_tilt_transition_steps` (venetian only)
7. Fire event and create notification

**Key insight**: Calibration uses Home Assistant services for movement (not direct Zigbee commands) because it needs the full async/await infrastructure and state polling.

## Development Commands

### Testing in Home Assistant

```bash
# Create symlinks for development (run from repo root)
ln -s $(pwd)/custom_components/ubisys ~/.homeassistant/custom_components/ubisys
ln -s $(pwd)/custom_zha_quirks/ubisys_j1.py ~/.homeassistant/custom_zha_quirks/ubisys_j1.py
ln -s $(pwd)/python_scripts/ubisys_j1_calibrate.py ~/.homeassistant/python_scripts/ubisys_j1_calibrate.py

# After code changes, reload the integration
# Via Home Assistant UI: Configuration → Integrations → Ubisys → ⋮ → Reload

# Or restart Home Assistant
ha core restart
```

### Required Home Assistant Configuration

```yaml
# configuration.yaml
zha:
  custom_quirks_path: custom_zha_quirks

python_script:

logger:
  logs:
    custom_components.ubisys: debug  # For development
```

### Checking Integration Status

```bash
# View integration logs
grep -i ubisys ~/.homeassistant/home-assistant.log | tail -50

# Check if quirk loaded (should show custom cluster)
# Navigate to: Configuration → Integrations → ZHA → Devices → J1 device → Signature

# Test calibration script exists
# Navigate to: Developer Tools → Services → Filter for "python_script.ubisys_j1_calibrate"

# Verify entity created
# Navigate to: Developer Tools → States → Filter for "ubisys"
```

## Code Modification Guidelines

### Changing Shade Types or Features

1. Update `const.py`:
   - Add to `SHADE_TYPES` list
   - Add to `ShadeType` enum
   - Add mapping in `SHADE_TYPE_TO_WINDOW_COVERING_TYPE`
   - Add mapping in `SHADE_TYPE_TO_FEATURES`

2. Update `config_flow.py`:
   - Add option to both `async_step_user` and `UbisysOptionsFlow.async_step_init`

3. Update `strings.json` and `translations/en.json` with new shade type label

4. Update calibration script if new WindowCoveringType requires different sequence

### Adding New Manufacturer Attributes

1. In `custom_zha_quirks/ubisys_j1.py`:
   - Define attribute constant (e.g., `UBISYS_ATTR_NEW = 0x1003`)
   - Add to `manufacturer_attributes` dict with `ZCLAttributeDef`
   - The auto-injection in `read_attributes`/`write_attributes` will handle it

2. Use anywhere in integration via ZHA cluster access (manufacturer code injected automatically)

### Modifying Calibration Sequence

The calibration script is a **python_script** (not standard Python module), with limitations:
- No imports beyond Home Assistant builtins
- Uses `hass`, `data`, `logger` as globals
- Must use `hass.async_create_task()` for async execution
- Access to `hass.services.async_call()`, `hass.states.get()`, `hass.bus.async_fire()`

To modify:
1. Edit `python_scripts/ubisys_j1_calibrate.py`
2. Reload python_script integration or restart Home Assistant
3. Test via `ubisys.calibrate` service call

### State Synchronization Pattern

The wrapper entity must stay synchronized with ZHA entity. Critical implementation:

```python
# In UbisysCover.__init__():
self._zha_entity_id = zha_entity_id

# In UbisysCover.async_added_to_hass():
self._unsubscribe_state_listener = async_track_state_change_event(
    self.hass, [self._zha_entity_id], self._async_state_changed_listener
)

# Callback triggers update:
@callback
def _async_state_changed_listener(self, event) -> None:
    self.hass.async_create_task(self._async_update_from_zha())

# Update pulls all state from ZHA entity:
async def _async_update_from_zha(self) -> None:
    zha_state = self.hass.states.get(self._zha_entity_id)
    # Copy all attributes...
    self.async_write_ha_state()
```

**Do not** poll or directly access the Zigbee device from the wrapper entity.

## Version Updates

To release a new version:

1. Update version in `custom_components/ubisys/manifest.json`
2. Update badges in `README.md` if needed
3. Commit with message: `chore: bump version to X.Y.Z`
4. Tag: `git tag -a vX.Y.Z -m "Release version X.Y.Z"`
5. Push tag: `git push origin vX.Y.Z`
6. HACS will auto-detect the new release

## Home Assistant Integration Requirements

This integration follows Home Assistant's integration quality checklist:

- Config flow (UI-based setup) - no YAML configuration required
- Type hints on all functions
- Uses `from __future__ import annotations`
- Logger per module: `_LOGGER = logging.getLogger(__name__)`
- No polling (`_attr_should_poll = False`)
- Proper unload/reload support in `__init__.py`
- Unique IDs for entities based on underlying device
- Device linkage via `device_info`
- Service definitions in `services.yaml`
- Translations in `strings.json` and `translations/en.json`

## Testing Without Hardware

To test without a physical J1 device:

1. Create a mock ZHA cover entity (requires ZHA integration with any Zigbee cover device)
2. Configure the Ubisys integration pointing to the mock entity
3. Test feature filtering (should only show features for selected shade type)
4. Calibration will fail without real device, but you can test service registration

Note: Full calibration testing requires actual Ubisys J1 hardware.

## Zigbee Technical Details

- **Manufacturer Code**: 0x10F2
- **Cluster**: 0x0102 (Window Covering)
- **Endpoint**: 2 (J1 uses endpoint 2 for window covering control)
- **Device Type**: 0x0202 (Window covering device)
- **Profile**: 0x0104 (Zigbee Home Automation)

The quirk matches device signature `("ubisys", "J1")` and replaces endpoint 2's WindowCovering cluster with the extended `UbisysWindowCovering` cluster.
