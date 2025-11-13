# Troubleshooting Auto-Discovery Issues

If ZHA shows your Ubisys device but the Ubisys integration doesn't auto-discover it, follow these steps:

## Step 1: Verify Integration is Loaded

1. Go to **Settings** → **Devices & Services** → **Integrations**
2. Look for "Ubisys Zigbee Devices" in the list
3. If NOT present, the integration isn't installed correctly

**If missing:**
- Check that files are in `config/custom_components/ubisys/`
- Restart Home Assistant
- Check logs for errors: `grep -i ubisys home-assistant.log`

## Step 2: Check Device Model Name

The integration looks for exact model names. Check what ZHA sees:

1. Go to **Settings** → **Devices & Services** → **ZHA**
2. Click on your Ubisys device
3. Look at the **Model** field
4. It should be one of: `J1`, `J1-R`, `D1`, `D1-R`, `S1`, `S1-R`

**Common Issues:**
- Model has extra text: e.g., "J1 (Router)" → Integration strips "(Router)" automatically
- Model is blank or different → Device might not be recognized by ZHA quirk

## Step 3: Enable Debug Logging

Add to `configuration.yaml`:

```yaml
logger:
  default: info
  logs:
    custom_components.ubisys: debug
    homeassistant.components.zha: debug
```

Restart Home Assistant and check logs:

```bash
grep -i "ubisys" home-assistant.log | tail -50
```

Look for:
- `Scanning device registry for Ubisys devices...`
- `Found Ubisys device: ubisys J1 (IEEE: ...)`
- `Auto-discovering Ubisys device: ubisys J1`
- `Device discovery complete: X Ubisys devices found, Y already configured, Z new config flows triggered`

## Step 4: Manual Discovery Trigger

If auto-discovery doesn't work, manually trigger discovery:

### Option A: Restart Home Assistant
Discovery runs on every startup, so a restart should trigger it.

### Option B: Developer Tools Service Call

1. Go to **Developer Tools** → **Services**
2. Call this service (requires custom script):

```yaml
service: python_script.trigger_ubisys_discovery
```

### Option C: Manual Configuration

If auto-discovery fails, you can manually add via UI:

1. **Settings** → **Devices & Services** → **Add Integration**
2. Search for "Ubisys"
3. Select your device from the dropdown
4. Configure shade type (for J1) or other settings
5. Click **Submit**

## Step 5: Check for Config Flow

Even if auto-discovery triggers, the config flow might be waiting:

1. Go to **Settings** → **Devices & Services**
2. Look for a notification badge or "Discovered" section
3. Click **Configure** on any pending Ubisys discovery

## Common Issues

### Issue: "Found unsupported Ubisys device"

**Symptom:** Logs show `Found unsupported Ubisys device: XYZ`

**Cause:** Device model not in `SUPPORTED_MODELS` list

**Fix:**
- Check if you have an S2/S2-R (not yet supported)
- File an issue with your device model

### Issue: "Device already configured"

**Symptom:** Logs show `Device XXX already configured`

**Cause:** Config entry already exists for this device

**Fix:**
- Check **Settings** → **Devices & Services** for existing Ubisys entry
- If duplicate, remove one and restart

### Issue: No logs at all

**Symptom:** No "Scanning device registry" messages in logs

**Cause:** Integration not loading or discovery not running

**Fix:**
1. Check integration files are in correct location
2. Check `manifest.json` has correct domain: "ubisys"
3. Restart Home Assistant
4. Check for Python errors in logs

### Issue: ZHA Quirk Not Loading

**Symptom:** Device attributes (calibration, phase mode) not available

**Cause:** Custom ZHA quirk not loaded

**Fix:**
1. Check files in `config/custom_zha_quirks/`
2. Verify `configuration.yaml` has:
   ```yaml
   zha:
     custom_quirks_path: custom_zha_quirks
   ```
3. Restart Home Assistant
4. Check ZHA device signature shows custom clusters

## Getting Help

If none of the above works, collect this information:

1. Home Assistant version
2. ZHA version
3. Device model from ZHA device page
4. Logs with debug enabled (last 100 lines):
   ```bash
   grep -i "ubisys" home-assistant.log | tail -100
   ```
5. Integration version from `manifest.json`

Post this information to:
- GitHub Issues: https://github.com/jihlenburg/homeassistant-ubisys/issues
- Home Assistant Community: https://community.home-assistant.io/
