# Troubleshooting J1 Cover "Unavailable" Issues

This guide helps you diagnose and fix issues where your J1 cover entity shows as "Unavailable" in Home Assistant.

## Understanding the Two-Entity Architecture

When you configure a J1 device in Ubisys, you get **TWO** cover entities:

| Entity | Platform | Visible | Enabled | Purpose |
|--------|----------|---------|---------|---------|
| `cover.ubisys_j1_5502` | ZHA | ❌ Hidden | ✅ Enabled | Internal state source |
| `cover.jalousie_none` | Ubisys | ✅ Visible | ✅ Enabled | User-facing entity |

**Why two entities?**

- **ZHA entity**: Handles Zigbee communication and maintains device state
- **Ubisys entity**: Filters features based on shade type and provides user interface

You should only see **one** entity in the UI (the Ubisys wrapper). The ZHA entity works in the background but remains hidden.

## How It Works (Quick Overview)

```
User clicks "Open" in UI
    ↓
Ubisys wrapper entity receives command
    ↓
Checks supported_features (filtered by shade type)
    ↓
Delegates command to ZHA entity
    ↓
ZHA entity sends Zigbee command to device
    ↓
Device executes movement
    ↓
ZHA entity receives state update from device
    ↓
Ubisys wrapper syncs state from ZHA entity
    ↓
User sees updated position in UI
```

**Key points:**
- Ubisys wrapper **never talks to Zigbee directly**
- All communication goes through ZHA entity
- Wrapper only filters features and provides UI

## Auto-Recovery Features (v1.3.0+)

The Ubisys integration includes two automatic recovery features:

### 1. Graceful Degradation (v1.3.0)

**Problem:** During Home Assistant startup, integrations load in parallel. Ubisys might load before ZHA has created its cover entity.

**Solution:** The wrapper entity:
1. Predicts the ZHA entity ID if not found yet
2. Creates itself anyway (shows in UI)
3. Marks itself as "Unavailable" with clear reason
4. Listens for state changes
5. **Automatically becomes available** when ZHA entity appears

**User experience:**
- Wrapper entity always shows in UI (never missing)
- Shows as "Unavailable" with reason: "ZHA entity not found or unavailable"
- Automatically recovers when ready (no reload needed)

### 2. Auto-Enable Logic (v1.3.1)

**Problem:** When the Ubisys integration creates its wrapper entity, ZHA detects this and automatically **disables** its own cover entity to prevent duplicate UI elements. However, the Ubisys wrapper **depends** on the ZHA entity having a state to delegate to.

This created a chicken-and-egg problem:
- Wrapper exists → ZHA disables its entity
- ZHA entity disabled → Has no state
- Wrapper has no state to sync from → Shows as "Unavailable"

**Solution:** Starting in v1.3.1, the Ubisys integration **automatically re-enables** the ZHA entity during setup, but keeps it **hidden**. This creates:

- **ZHA entity**: `hidden=true` + `enabled=true` = "internal state source"
- **Wrapper entity**: `visible=true` + `enabled=true` = "user-facing entity"

**Result:** Users see ONE entity in the UI (the wrapper), while the ZHA entity provides state in the background.

### Respecting User Intent

The auto-enable logic **only** enables if the entity was disabled by the integration:

| Scenario | Action | Reason |
|----------|--------|--------|
| Disabled by integration | ✅ Auto-enable | ZHA auto-disabled to prevent duplicates |
| Disabled by user | ❌ Leave disabled | Respect user's explicit choice |
| Already enabled | ✅ No action | Already in desired state |

**Logs you'll see:**

```
INFO: Enabling ZHA entity cover.ubisys_j1_5502 (disabled by integration).
      Entity remains hidden; wrapper provides user interface.
```

or if user disabled it:

```
INFO: ZHA entity cover.ubisys_j1_5502 is disabled by user (not enabling).
      Wrapper will be unavailable until ZHA entity is manually enabled.
```

## Troubleshooting Steps

### Wrapper Shows as "Unavailable"

**Possible causes:**

#### 1. ZHA entity disabled by user

**Check:**
1. Go to Settings → Devices & Services → Entities
2. Search for "ubisys_j1"
3. Find the ZHA cover entity (will show as disabled)

**Fix:**
1. Enable it manually
2. Wrapper will become available automatically

#### 2. Device not paired with ZHA

**Check:**
1. Go to Settings → Devices & Services → ZHA
2. Verify device is listed

**Fix:**
1. If not listed, pair device with ZHA first
2. Then configure Ubisys integration

#### 3. Startup timing issue (rare after v1.3.0)

**Check:**
- Wait 30-60 seconds for all integrations to finish loading

**Fix:**
- Wrapper should auto-recover
- If not, reload Ubisys integration:
  1. Settings → Devices & Services → Ubisys
  2. Click three dots (⋮) → Reload

#### 4. ZHA entity deleted

**Check:**
- Go to Settings → Devices & Services → Entities
- Search for `cover.ubisys_j1_*`

**Fix:**
1. If missing, remove and re-add device in ZHA
2. Reconfigure Ubisys integration

### Wrapper Exists But No Controls Showing

**Cause:** Wrapper is disabled or hidden in Home Assistant

**Fix:**
1. Settings → Devices & Services → Entities
2. Search for "jalousie" or your device name
3. Find the Ubisys cover entity
4. Enable it if disabled
5. Unhide it if hidden

### Commands Not Working

**Cause:** ZHA entity is unavailable or offline

**Fix:**
1. Check if ZHA device is online (Settings → Devices & Services → ZHA)
2. Verify Zigbee coordinator is working
3. Check device battery/power
4. Try reloading ZHA integration

## Quick Fix Checklist

When wrapper shows as unavailable, try these steps in order:

1. ✅ **Wait 60 seconds** - Auto-recovery might be in progress
2. ✅ **Check ZHA entity status** - Ensure it's enabled (not by user)
3. ✅ **Reload Ubisys integration** - This re-runs the auto-enable logic
4. ✅ **Check ZHA device** - Ensure device is paired and online
5. ✅ **Check logs** - Look for specific error messages

## Understanding Entity States

| State | Meaning | Has State | Shows in UI | Can Be Controlled |
|-------|---------|-----------|-------------|-------------------|
| Visible + Enabled | Normal entity | ✅ | ✅ | ✅ |
| Hidden + Enabled | Internal use | ✅ | ❌ | ✅ (via code) |
| Visible + Disabled | User disabled | ❌ | ✅ (as disabled) | ❌ |
| Hidden + Disabled | Integration disabled | ❌ | ❌ | ❌ |

**Our pattern:** ZHA entity is **Hidden + Enabled** = invisible to users but provides state for wrapper.

## Version History

### v1.3.1 (Current)
- ✅ Auto-enables ZHA entity if disabled by integration
- ✅ Respects user's choice if manually disabled
- ✅ Comprehensive logging for troubleshooting
- ✅ Idempotent and safe for multiple reloads

### v1.3.0
- ✅ Graceful degradation for startup race conditions
- ✅ Automatic recovery when ZHA entity appears
- ✅ Clear unavailability reasons
- ⚠️ Issue: ZHA entity auto-disabled causing wrapper unavailable (fixed in v1.3.1)

### v1.2.x and earlier
- ⚠️ Hard failure if ZHA entity not found
- ⚠️ No automatic recovery
- ⚠️ Required manual intervention

## See Also

- [J1 Calibration Guide](j1_calibration.md)
- [Migration Guide](migration_v2.0.md)
- [Main Troubleshooting Guide](troubleshooting.md)
- [Window Covering Architecture](window_covering_architecture.md) (Developer reference)
