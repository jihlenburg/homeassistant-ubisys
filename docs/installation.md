# Installation Guide

Complete installation instructions for the Ubisys Zigbee Devices integration.

## 📋 Prerequisites

- Home Assistant 2024.1.0 or newer
- ZHA integration installed and configured
- Zigbee coordinator paired and operational

## 📦 Installation Methods

### Method 1: HACS (Recommended)

The simplest method for most users.

1. **Open HACS** in Home Assistant
   - Navigate to **HACS** in the sidebar

2. **Add Custom Repository**
   - Click the **⋮** menu (top right)
   - Select **Custom repositories**
   - Add repository URL: `https://github.com/jihlenburg/homeassistant-ubisys`
   - Category: **Integration**
   - Click **Add**

3. **Install Integration**
   - Search for "Ubisys Zigbee Devices"
   - Click **Download**
   - Select the latest version
   - Wait for download to complete

4. **Restart Home Assistant**
   - Go to **Settings** → **System** → **Restart**
   - Or via CLI: `ha core restart`

5. **Verify Installation**
   - Check logs: `grep -i ubisys /config/home-assistant.log`
   - Integration should appear in **Settings** → **Devices & Services** → **Add Integration**

---

### Method 2: One-Line Installer

Automated installation script for advanced users.

> [!WARNING]
> This method modifies your `configuration.yaml` file. A backup is created automatically.

#### For Raspberry Pi / Home Assistant OS

```bash
# SSH into your Home Assistant instance
ssh root@homeassistant.local
# (or use your IP: ssh root@192.168.1.xxx)

# Run the installer
curl -sSL https://raw.githubusercontent.com/jihlenburg/homeassistant-ubisys/main/install.sh | bash
```

#### For Standard Linux/macOS

```bash
curl -sSL https://raw.githubusercontent.com/jihlenburg/homeassistant-ubisys/main/install.sh | bash
```

#### What the Installer Does

- ✅ Creates required directories (`custom_components`, `custom_zha_quirks`)
- ✅ Downloads all integration files from GitHub
- ✅ Installs ZHA quirk for manufacturer-specific attributes
- ✅ Updates `configuration.yaml` with required settings
- ✅ Creates timestamped backups of existing files
- ✅ Validates Home Assistant configuration
- ✅ Provides rollback capability on errors

#### Post-Installation Steps

1. **Restart Home Assistant**
   ```bash
   ha core restart
   ```

2. **Verify Installation**
   ```bash
   # Check logs
   grep -i ubisys /config/home-assistant.log

   # Verify quirk loaded
   grep -i "Successfully imported custom quirk" /config/home-assistant.log
   ```

3. **Configure Integration**
   - Navigate to **Settings** → **Devices & Services** → **Add Integration**
   - Search for "Ubisys"
   - Follow configuration prompts

---

### Method 3: Manual Installation

For users who prefer complete control.

#### Step 1: Download Files

Download the latest release from GitHub:
```bash
wget https://github.com/jihlenburg/homeassistant-ubisys/archive/refs/tags/vX.Y.Z.tar.gz
tar -xzf vX.Y.Z.tar.gz
cd homeassistant-ubisys-X.Y.Z
```

Or clone the repository:
```bash
git clone https://github.com/jihlenburg/homeassistant-ubisys.git
cd homeassistant-ubisys
```

#### Step 2: Copy Integration Files

```bash
# Copy main integration
cp -r custom_components/ubisys /config/custom_components/

# Copy ZHA quirks
mkdir -p /config/custom_zha_quirks
cp custom_zha_quirks/*.py /config/custom_zha_quirks/
```

#### Step 3: Update Configuration

Add to your `configuration.yaml`:

```yaml
# Enable custom ZHA quirks
zha:
  custom_quirks_path: custom_zha_quirks
```

> [!TIP]
> If you already have a `zha:` section, just add the `custom_quirks_path` line under it.

#### Step 4: Verify File Structure

Your Home Assistant configuration directory should look like this:

```
/config/
├── configuration.yaml
├── custom_components/
│   └── ubisys/
│       ├── __init__.py
│       ├── manifest.json
│       ├── config_flow.py
│       ├── cover.py
│       ├── light.py
│       ├── switch.py
│       ├── button.py
│       ├── sensor.py
│       ├── j1_calibration.py
│       ├── d1_config.py
│       ├── helpers.py
│       ├── input_config.py
│       ├── input_monitor.py
│       ├── input_parser.py
│       ├── device_trigger.py
│       ├── diagnostics.py
│       ├── logbook.py
│       ├── repairs.py
│       ├── const.py
│       ├── services.yaml
│       ├── strings.json
│       └── translations/
│           ├── en.json
│           ├── de.json
│           ├── fr.json
│           └── es.json
└── custom_zha_quirks/
    ├── ubisys_common.py
    ├── ubisys_j1.py
    ├── ubisys_d1.py
    └── ubisys_s1.py
```

#### Step 5: Validate Configuration

```bash
# Check config is valid
ha core check

# Or via Home Assistant UI:
# Settings → System → Restart → Check Configuration
```

#### Step 6: Restart Home Assistant

```bash
ha core restart
```

Or via UI: **Settings** → **System** → **Restart**

---

## ✅ Verification

### Check Integration Loaded

1. **Via UI:**
   - Go to **Settings** → **Devices & Services**
   - Click **Add Integration**
   - Search for "Ubisys"
   - You should see "Ubisys Zigbee Devices"

2. **Via Logs:**
   ```bash
   grep -i "ubisys" /config/home-assistant.log
   ```

   You should see:
   ```
   Successfully imported custom quirk ubisys_j1
   Successfully imported custom quirk ubisys_d1
   Successfully imported custom quirk ubisys_s1
   Loading ubisys
   Setup of domain ubisys took X seconds
   ```

### Check ZHA Quirk Loaded

Navigate to:
**Settings** → **Devices & Services** → **ZHA** → **Devices** → *[Your Ubisys Device]* → **Signature**

Look for manufacturer-specific clusters:
- J1: `WindowCovering` cluster with attributes `0x1000`, `0x1001`, `0x1002`
- D1: `Ballast`, `DimmerSetup`, `DeviceSetup` clusters
- S1: `DeviceSetup` cluster

---

## 🔄 Updating

### HACS Update

1. **Check for Updates**
   - HACS will notify you when updates are available
   - Or manually check: **HACS** → **Integrations** → **Ubisys Zigbee Devices**

2. **Install Update**
   - Click **Update**
   - Select version
   - Click **Download**

3. **Restart Home Assistant**
   - **Settings** → **System** → **Restart**

### Manual Update

1. **Backup Current Installation**
   ```bash
   cp -r /config/custom_components/ubisys /config/custom_components/ubisys.backup
   cp -r /config/custom_zha_quirks /config/custom_zha_quirks.backup
   ```

2. **Download Latest Release**
   ```bash
   wget https://github.com/jihlenburg/homeassistant-ubisys/archive/refs/tags/vX.Y.Z.tar.gz
   ```

3. **Replace Files**
   ```bash
   rm -rf /config/custom_components/ubisys
   cp -r homeassistant-ubisys-X.Y.Z/custom_components/ubisys /config/custom_components/

   rm -rf /config/custom_zha_quirks/ubisys*.py
   cp homeassistant-ubisys-X.Y.Z/custom_zha_quirks/*.py /config/custom_zha_quirks/
   ```

4. **Restart Home Assistant**
   ```bash
   ha core restart
   ```

---

## 🗑️ Uninstallation

### Remove Integration

1. **Remove Config Entries**
   - Go to **Settings** → **Devices & Services**
   - Find **Ubisys** integrations
   - Click **⋮** → **Delete**
   - Confirm deletion

2. **Remove Files**
   ```bash
   rm -rf /config/custom_components/ubisys
   rm /config/custom_zha_quirks/ubisys*.py
   ```

3. **Clean Configuration**
   Remove from `configuration.yaml`:
   ```yaml
   zha:
     custom_quirks_path: custom_zha_quirks  # Remove if no other quirks
   ```

4. **Restart Home Assistant**
   ```bash
   ha core restart
   ```

---

## 🔧 Troubleshooting Installation

### Integration Not Showing in UI

**Check file permissions:**
```bash
ls -la /config/custom_components/ubisys/
# All files should be readable
```

**Check manifest.json:**
```bash
cat /config/custom_components/ubisys/manifest.json
# Should be valid JSON with "domain": "ubisys"
```

**Check logs for errors:**
```bash
grep -i "ubisys\|error\|exception" /config/home-assistant.log
```

### ZHA Quirk Not Loading

**Verify quirk path:**
```bash
ls -la /config/custom_zha_quirks/
# Should contain ubisys_*.py files
```

**Check configuration.yaml:**
```yaml
zha:
  custom_quirks_path: custom_zha_quirks  # Must be exactly this
```

**Restart ZHA integration:**
- **Settings** → **Devices & Services** → **ZHA** → **⋮** → **Reload**

### Permission Denied Errors

**Fix ownership (Home Assistant OS):**
```bash
chown -R homeassistant:homeassistant /config/custom_components/ubisys
chown -R homeassistant:homeassistant /config/custom_zha_quirks
```

**Fix permissions:**
```bash
chmod -R 755 /config/custom_components/ubisys
chmod -R 755 /config/custom_zha_quirks
```

---

## 📞 Support

If installation fails:

1. **Check logs:**
   ```bash
   tail -f /config/home-assistant.log | grep -i ubisys
   ```

2. **Verify dependencies:**
   - Home Assistant version >= 2024.1.0
   - ZHA integration installed and operational

3. **Get help:**
   - [GitHub Issues](https://github.com/jihlenburg/homeassistant-ubisys/issues)
   - [GitHub Discussions](https://github.com/jihlenburg/homeassistant-ubisys/discussions)
   - [Home Assistant Community Forum](https://community.home-assistant.io/)

---

## 🔗 Next Steps

After successful installation:

1. **[Pair Your Device](getting_started.md)** - Add Ubisys devices to ZHA
2. **[Configure Integration](getting_started.md#configuration)** - Set up shade types and options
3. **[Run Calibration](j1_calibration.md)** - Calibrate J1 window coverings
4. **[Configure D1](d1_configuration.md)** - Set up phase mode for dimmers
