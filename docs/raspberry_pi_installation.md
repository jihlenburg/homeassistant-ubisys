# Raspberry Pi Installation Guide

This guide covers installing the Ubisys integration on Home Assistant running on a Raspberry Pi directly from the GitHub repository.

## Prerequisites

- Home Assistant installed on Raspberry Pi (Home Assistant OS, Supervised, or Container)
- SSH access enabled to your Home Assistant instance
- Git installed (usually pre-installed on Home Assistant OS)
- Network connectivity from Raspberry Pi to GitHub

## Installation Methods

### Method 1: Direct Git Clone (Recommended for Development)

This method clones the repository directly onto your Raspberry Pi and creates symbolic links.

#### Step 1: SSH into Your Raspberry Pi

```bash
# For Home Assistant OS
ssh root@homeassistant.local
# Password: (your configured password)

# Or use IP address
ssh root@192.168.1.xxx
```

#### Step 2: Navigate to Config Directory

```bash
# Home Assistant OS / Supervised
cd /config

# Home Assistant Container (adjust path as needed)
cd /path/to/homeassistant/config
```

#### Step 3: Clone the Repository

```bash
# Clone to a temporary location
cd /config
git clone https://github.com/jihlenburg/homeassistant-ubisys.git ubisys-repo
```

#### Step 4: Create Required Directories

```bash
mkdir -p /config/custom_components
mkdir -p /config/custom_zha_quirks
mkdir -p /config/python_scripts
```

#### Step 5: Copy Files to Home Assistant

```bash
# Copy custom integration
cp -r /config/ubisys-repo/custom_components/ubisys /config/custom_components/

# Copy ZHA quirk
cp /config/ubisys-repo/custom_zha_quirks/ubisys_j1.py /config/custom_zha_quirks/

# Copy calibration script
cp /config/ubisys-repo/python_scripts/ubisys_j1_calibrate.py /config/python_scripts/

# Set proper permissions
chmod -R 755 /config/custom_components/ubisys
chmod 644 /config/custom_zha_quirks/ubisys_j1.py
chmod 644 /config/python_scripts/ubisys_j1_calibrate.py
```

#### Step 6: Configure Home Assistant

Edit your configuration.yaml:

```bash
# Using nano editor
nano /config/configuration.yaml

# Or using vi
vi /config/configuration.yaml
```

Add these lines:

```yaml
# ZHA Configuration
zha:
  custom_quirks_path: custom_zha_quirks

# Python Scripts
python_script:
```

Save and exit (Ctrl+X, then Y, then Enter for nano).

#### Step 7: Restart Home Assistant

```bash
# Via Home Assistant CLI (if available)
ha core restart

# Or from Home Assistant UI:
# Configuration → System → Restart
```

#### Step 8: Clean Up (Optional)

```bash
# Remove the cloned repository after installation
rm -rf /config/ubisys-repo
```

### Method 2: Using the Installation Script

The repository includes an automated installation script that can be adapted for Raspberry Pi.

#### Step 1: SSH into Your Raspberry Pi

```bash
ssh root@homeassistant.local
```

#### Step 2: Download and Run Installer

```bash
cd /config

# Download the installer
curl -sSL https://raw.githubusercontent.com/jihlenburg/homeassistant-ubisys/main/install.sh -o install.sh

# Make it executable
chmod +x install.sh

# Run the installer
./install.sh
```

**Note:** The installer may need modifications for Home Assistant OS paths. It's designed for standard Linux installations.

#### Step 3: Verify Installation

```bash
# Check files were created
ls -la /config/custom_components/ubisys/
ls -la /config/custom_zha_quirks/ubisys_j1.py
ls -la /config/python_scripts/ubisys_j1_calibrate.py
```

#### Step 4: Restart Home Assistant

```bash
ha core restart
```

### Method 3: Manual File Download (No Git Required)

If Git is not available or you prefer not to use it:

#### Step 1: SSH into Your Raspberry Pi

```bash
ssh root@homeassistant.local
```

#### Step 2: Create Directories

```bash
cd /config
mkdir -p custom_components/ubisys/translations
mkdir -p custom_zha_quirks
mkdir -p python_scripts
```

#### Step 3: Download Files Individually

```bash
# Set repository URL
REPO_URL="https://raw.githubusercontent.com/jihlenburg/homeassistant-ubisys/main"

# Download integration files
curl -sL "$REPO_URL/custom_components/ubisys/__init__.py" -o custom_components/ubisys/__init__.py
curl -sL "$REPO_URL/custom_components/ubisys/manifest.json" -o custom_components/ubisys/manifest.json
curl -sL "$REPO_URL/custom_components/ubisys/config_flow.py" -o custom_components/ubisys/config_flow.py
curl -sL "$REPO_URL/custom_components/ubisys/const.py" -o custom_components/ubisys/const.py
curl -sL "$REPO_URL/custom_components/ubisys/cover.py" -o custom_components/ubisys/cover.py
curl -sL "$REPO_URL/custom_components/ubisys/services.yaml" -o custom_components/ubisys/services.yaml
curl -sL "$REPO_URL/custom_components/ubisys/strings.json" -o custom_components/ubisys/strings.json
curl -sL "$REPO_URL/custom_components/ubisys/translations/en.json" -o custom_components/ubisys/translations/en.json

# Download quirk
curl -sL "$REPO_URL/custom_zha_quirks/ubisys_j1.py" -o custom_zha_quirks/ubisys_j1.py

# Download calibration script
curl -sL "$REPO_URL/python_scripts/ubisys_j1_calibrate.py" -o python_scripts/ubisys_j1_calibrate.py
```

#### Step 4: Configure and Restart

Follow steps 6-7 from Method 1.

## Post-Installation Verification

### Check Integration Files

```bash
# Verify all files exist
ls -R /config/custom_components/ubisys/
ls -l /config/custom_zha_quirks/ubisys_j1.py
ls -l /config/python_scripts/ubisys_j1_calibrate.py
```

Expected output:
```
/config/custom_components/ubisys/:
__init__.py  config_flow.py  const.py  cover.py  manifest.json  services.yaml  strings.json  translations

/config/custom_components/ubisys/translations:
en.json
```

### Check Configuration

```bash
# Verify configuration.yaml includes required sections
grep -A 2 "^zha:" /config/configuration.yaml
grep "^python_script:" /config/configuration.yaml
```

Should show:
```
zha:
  custom_quirks_path: custom_zha_quirks

python_script:
```

### Check Home Assistant Logs

After restart, check that the integration loaded successfully:

```bash
# View recent logs
tail -100 /config/home-assistant.log | grep -i ubisys

# Or check for errors
grep -i "error.*ubisys" /config/home-assistant.log
```

### Verify in Home Assistant UI

1. Go to **Configuration** → **Integrations**
2. Click **+ Add Integration**
3. Search for "Ubisys" - it should appear in the list

## Updating the Integration

### Update from Git

```bash
cd /config
git clone https://github.com/jihlenburg/homeassistant-ubisys.git ubisys-repo
cd ubisys-repo
git pull origin main

# Copy updated files
cp -r custom_components/ubisys/* /config/custom_components/ubisys/
cp custom_zha_quirks/ubisys_j1.py /config/custom_zha_quirks/
cp python_scripts/ubisys_j1_calibrate.py /config/python_scripts/

# Restart Home Assistant
ha core restart

# Clean up
cd /config
rm -rf ubisys-repo
```

### Update Script

Create an update script for easy updates:

```bash
nano /config/update_ubisys.sh
```

Add this content:

```bash
#!/bin/bash

echo "Updating Ubisys integration..."

# Backup existing installation
echo "Creating backup..."
cp -r /config/custom_components/ubisys /config/custom_components/ubisys.bak

# Clone latest version
cd /config
rm -rf ubisys-repo
git clone https://github.com/jihlenburg/homeassistant-ubisys.git ubisys-repo

# Copy files
echo "Installing updated files..."
cp -r ubisys-repo/custom_components/ubisys/* /config/custom_components/ubisys/
cp ubisys-repo/custom_zha_quirks/ubisys_j1.py /config/custom_zha_quirks/
cp ubisys-repo/python_scripts/ubisys_j1_calibrate.py /config/python_scripts/

# Clean up
rm -rf ubisys-repo

echo "Update complete. Please restart Home Assistant."
```

Make it executable:

```bash
chmod +x /config/update_ubisys.sh
```

Run it:

```bash
/config/update_ubisys.sh
ha core restart
```

## Troubleshooting

### Permission Issues

```bash
# Fix permissions if needed
chmod -R 755 /config/custom_components/ubisys
chown -R root:root /config/custom_components/ubisys
```

### Integration Not Showing

```bash
# Check manifest.json syntax
python3 -c "import json; json.load(open('/config/custom_components/ubisys/manifest.json'))"

# Restart Home Assistant
ha core restart
```

### Quirk Not Loading

```bash
# Verify quirk path in configuration.yaml
grep custom_quirks_path /config/configuration.yaml

# Check quirk file syntax
python3 -m py_compile /config/custom_zha_quirks/ubisys_j1.py

# Reload ZHA integration via UI
```

### Python Script Not Working

```bash
# Verify python_script enabled
grep python_script /config/configuration.yaml

# Check file exists and is readable
ls -l /config/python_scripts/ubisys_j1_calibrate.py

# Restart Home Assistant
ha core restart
```

### SSH Connection Issues

```bash
# If using Home Assistant OS and SSH add-on not installed:
# 1. Install "Terminal & SSH" add-on from Supervisor → Add-on Store
# 2. Configure the add-on with a password
# 3. Start the add-on
# 4. Connect via SSH

# Default SSH ports:
# - Home Assistant OS: port 22222
# - Standard SSH: port 22

ssh root@homeassistant.local -p 22222
```

## Automation for Easy Updates

Create a Home Assistant automation to notify when updates are available:

```yaml
automation:
  - alias: "Check Ubisys Integration Updates"
    trigger:
      - platform: time
        at: "09:00:00"
    action:
      - service: shell_command.check_ubisys_updates
      - delay: "00:00:05"
      - service: persistent_notification.create
        data:
          title: "Ubisys Integration Update Available"
          message: "A new version of Ubisys integration is available. Run update script to install."

shell_command:
  check_ubisys_updates: "cd /config/ubisys-repo && git fetch && [ $(git rev-list HEAD...origin/main --count) -gt 0 ] && echo 'Updates available' || echo 'Up to date'"
```

## Best Practices

1. **Keep backups**: Always backup before updating
2. **Test in development**: If possible, test updates on a non-production instance first
3. **Check logs**: After installation/update, always check logs for errors
4. **Use version control**: Keep track of which version you're running
5. **Monitor GitHub**: Watch the repository for updates and security notices

## File Locations Reference

### Home Assistant OS / Supervised

```
/config/custom_components/ubisys/
/config/custom_zha_quirks/ubisys_j1.py
/config/python_scripts/ubisys_j1_calibrate.py
/config/configuration.yaml
/config/home-assistant.log
```

### Home Assistant Container

Adjust paths based on your volume mounts:
```
/path/to/config/custom_components/ubisys/
/path/to/config/custom_zha_quirks/ubisys_j1.py
/path/to/config/python_scripts/ubisys_j1_calibrate.py
```

### Home Assistant Core (venv)

```
~/.homeassistant/custom_components/ubisys/
~/.homeassistant/custom_zha_quirks/ubisys_j1.py
~/.homeassistant/python_scripts/ubisys_j1_calibrate.py
```

## Additional Resources

- [Home Assistant SSH Access](https://www.home-assistant.io/common-tasks/os/#enabling-ssh)
- [Custom Components](https://www.home-assistant.io/integrations/custom_components/)
- [ZHA Custom Quirks](https://www.home-assistant.io/integrations/zha/#custom-quirks)
- [Python Scripts](https://www.home-assistant.io/integrations/python_script/)

## Support

If you encounter issues specific to Raspberry Pi installation:

1. Check Home Assistant logs: `/config/home-assistant.log`
2. Verify file permissions
3. Ensure sufficient disk space: `df -h`
4. Check Raspberry Pi resources: `top` or `htop`
5. Open an issue on GitHub with "Raspberry Pi" in the title
