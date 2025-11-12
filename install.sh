#!/bin/bash

# Ubisys Home Assistant Integration Installer
# This script installs the Ubisys custom integration and quirks

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
REPO_URL="https://raw.githubusercontent.com/jihlenburg/homeassistant-ubisys/main"

# Auto-detect Home Assistant config directory
if [ -d "/config" ]; then
    # Home Assistant OS / Supervised
    HA_CONFIG_DIR="/config"
elif [ -d "${HOME}/.homeassistant" ]; then
    # Home Assistant Core / Container
    HA_CONFIG_DIR="${HOME}/.homeassistant"
else
    # Default fallback
    HA_CONFIG_DIR="${HOME}/.homeassistant"
fi

BACKUP_DIR="${HA_CONFIG_DIR}/backups/ubisys_install_$(date +%Y%m%d_%H%M%S)"

# Print colored message
print_message() {
    local color=$1
    shift
    echo -e "${color}$*${NC}"
}

# Print success message
success() {
    print_message "$GREEN" "✓ $*"
}

# Print error message
error() {
    print_message "$RED" "✗ $*"
}

# Print warning message
warning() {
    print_message "$YELLOW" "⚠ $*"
}

# Print info message
info() {
    print_message "$NC" "ℹ $*"
}

# Check if Home Assistant config directory exists
check_ha_directory() {
    if [ ! -d "$HA_CONFIG_DIR" ]; then
        error "Home Assistant config directory not found at $HA_CONFIG_DIR"
        read -p "Enter the path to your Home Assistant config directory: " HA_CONFIG_DIR
        HA_CONFIG_DIR="${HA_CONFIG_DIR/#\~/$HOME}"

        if [ ! -d "$HA_CONFIG_DIR" ]; then
            error "Directory $HA_CONFIG_DIR does not exist"
            exit 1
        fi
    fi

    success "Found Home Assistant config directory: $HA_CONFIG_DIR"
}

# Create backup directory
create_backup() {
    info "Creating backup directory: $BACKUP_DIR"
    mkdir -p "$BACKUP_DIR"
    success "Backup directory created"
}

# Backup existing files
backup_existing() {
    local source=$1
    local name=$2

    if [ -e "$source" ]; then
        info "Backing up existing $name"
        cp -r "$source" "$BACKUP_DIR/" 2>/dev/null || true
        success "Backed up $name"
    fi
}

# Create required directories
create_directories() {
    info "Creating required directories..."

    mkdir -p "$HA_CONFIG_DIR/custom_components/ubisys/translations"
    mkdir -p "$HA_CONFIG_DIR/custom_zha_quirks"

    success "Directories created"
}

# Download file from GitHub
download_file() {
    local url=$1
    local destination=$2
    local description=$3

    info "Downloading $description..."

    if command -v curl &> /dev/null; then
        curl -sfL "$url" -o "$destination"
    elif command -v wget &> /dev/null; then
        wget -q "$url" -O "$destination"
    else
        error "Neither curl nor wget is available. Please install one of them."
        exit 1
    fi

    if [ $? -eq 0 ]; then
        success "Downloaded $description"
    else
        error "Failed to download $description from $url"
        exit 1
    fi
}

# Install integration files
install_integration() {
    info "Installing Ubisys integration files..."

    # Backup existing installation
    backup_existing "$HA_CONFIG_DIR/custom_components/ubisys" "custom integration"

    # Download integration files
    download_file \
        "$REPO_URL/custom_components/ubisys/__init__.py" \
        "$HA_CONFIG_DIR/custom_components/ubisys/__init__.py" \
        "integration __init__.py"

    download_file \
        "$REPO_URL/custom_components/ubisys/manifest.json" \
        "$HA_CONFIG_DIR/custom_components/ubisys/manifest.json" \
        "manifest.json"

    download_file \
        "$REPO_URL/custom_components/ubisys/config_flow.py" \
        "$HA_CONFIG_DIR/custom_components/ubisys/config_flow.py" \
        "config_flow.py"

    download_file \
        "$REPO_URL/custom_components/ubisys/const.py" \
        "$HA_CONFIG_DIR/custom_components/ubisys/const.py" \
        "const.py"

    download_file \
        "$REPO_URL/custom_components/ubisys/cover.py" \
        "$HA_CONFIG_DIR/custom_components/ubisys/cover.py" \
        "cover.py"

    download_file \
        "$REPO_URL/custom_components/ubisys/services.yaml" \
        "$HA_CONFIG_DIR/custom_components/ubisys/services.yaml" \
        "services.yaml"

    download_file \
        "$REPO_URL/custom_components/ubisys/strings.json" \
        "$HA_CONFIG_DIR/custom_components/ubisys/strings.json" \
        "strings.json"

    download_file \
        "$REPO_URL/custom_components/ubisys/translations/en.json" \
        "$HA_CONFIG_DIR/custom_components/ubisys/translations/en.json" \
        "translations"

    download_file \
        "$REPO_URL/custom_components/ubisys/button.py" \
        "$HA_CONFIG_DIR/custom_components/ubisys/button.py" \
        "button.py"

    download_file \
        "$REPO_URL/custom_components/ubisys/j1_calibration.py" \
        "$HA_CONFIG_DIR/custom_components/ubisys/j1_calibration.py" \
        "j1_calibration.py"

    download_file \
        "$REPO_URL/custom_components/ubisys/d1_config.py" \
        "$HA_CONFIG_DIR/custom_components/ubisys/d1_config.py" \
        "d1_config.py"

    download_file \
        "$REPO_URL/custom_components/ubisys/helpers.py" \
        "$HA_CONFIG_DIR/custom_components/ubisys/helpers.py" \
        "helpers.py"

    download_file \
        "$REPO_URL/custom_components/ubisys/input_monitor.py" \
        "$HA_CONFIG_DIR/custom_components/ubisys/input_monitor.py" \
        "input_monitor.py"

    download_file \
        "$REPO_URL/custom_components/ubisys/device_trigger.py" \
        "$HA_CONFIG_DIR/custom_components/ubisys/device_trigger.py" \
        "device_trigger.py"

    download_file \
        "$REPO_URL/custom_components/ubisys/input_config.py" \
        "$HA_CONFIG_DIR/custom_components/ubisys/input_config.py" \
        "input_config.py"

    success "Integration files installed"
}

# Install ZHA quirks
install_quirks() {
    info "Installing Ubisys ZHA quirks..."

    # Backup existing quirks
    backup_existing "$HA_CONFIG_DIR/custom_zha_quirks/ubisys_j1.py" "J1 quirk"
    backup_existing "$HA_CONFIG_DIR/custom_zha_quirks/ubisys_d1.py" "D1 quirk"
    backup_existing "$HA_CONFIG_DIR/custom_zha_quirks/ubisys_s1.py" "S1 quirk"
    backup_existing "$HA_CONFIG_DIR/custom_zha_quirks/ubisys_common.py" "common quirk module"

    # Download all quirk files
    download_file \
        "$REPO_URL/custom_zha_quirks/ubisys_common.py" \
        "$HA_CONFIG_DIR/custom_zha_quirks/ubisys_common.py" \
        "common quirk module"

    download_file \
        "$REPO_URL/custom_zha_quirks/ubisys_j1.py" \
        "$HA_CONFIG_DIR/custom_zha_quirks/ubisys_j1.py" \
        "J1 quirk"

    download_file \
        "$REPO_URL/custom_zha_quirks/ubisys_d1.py" \
        "$HA_CONFIG_DIR/custom_zha_quirks/ubisys_d1.py" \
        "D1 quirk"

    download_file \
        "$REPO_URL/custom_zha_quirks/ubisys_s1.py" \
        "$HA_CONFIG_DIR/custom_zha_quirks/ubisys_s1.py" \
        "S1/S1-R quirk"

    success "All quirks installed"
}

# Update configuration.yaml
update_configuration() {
    info "Checking configuration.yaml..."

    local config_file="$HA_CONFIG_DIR/configuration.yaml"

    if [ ! -f "$config_file" ]; then
        warning "configuration.yaml not found. Creating one..."
        echo "# Home Assistant Configuration" > "$config_file"
    fi

    # Backup configuration.yaml
    backup_existing "$config_file" "configuration.yaml"

    # Check if ZHA custom quirks path is configured
    if ! grep -q "custom_quirks_path:" "$config_file"; then
        info "Adding ZHA custom quirks path to configuration.yaml..."

        if grep -q "^zha:" "$config_file"; then
            # ZHA section exists, add custom_quirks_path under it
            sed -i.bak '/^zha:/a\
  custom_quirks_path: custom_zha_quirks
' "$config_file"
        else
            # Add new ZHA section
            cat >> "$config_file" << EOF

# ZHA Configuration
zha:
  custom_quirks_path: custom_zha_quirks
EOF
        fi
        success "Added ZHA custom quirks path"
    else
        success "ZHA custom quirks path already configured"
    fi
}

# Validate Home Assistant configuration
validate_configuration() {
    info "Validating Home Assistant configuration..."

    if command -v hass &> /dev/null; then
        if hass --script check_config -c "$HA_CONFIG_DIR" &> /dev/null; then
            success "Home Assistant configuration is valid"
        else
            warning "Configuration validation failed. Please check your configuration manually."
            warning "You may need to restart Home Assistant to see the changes."
        fi
    else
        warning "Home Assistant CLI not found. Skipping configuration validation."
    fi
}

# Print completion message
print_completion() {
    echo ""
    success "============================================"
    success "  Ubisys Integration Installed Successfully"
    success "============================================"
    echo ""
    info "Next steps:"
    info "  1. Restart Home Assistant"
    info "  2. Go to Settings > Devices & Services > Integrations"
    info "  3. Click '+ Add Integration'"
    info "  4. Search for 'Ubisys' and follow the setup"
    info "  5. For J1 devices: Use calibration button or service"
    info "  6. For D1/S1 devices: Configure via device settings"
    echo ""
    info "Backup location: $BACKUP_DIR"
    echo ""
    info "Documentation: https://github.com/jihlenburg/homeassistant-ubisys"
    echo ""
}

# Rollback on error
rollback() {
    error "Installation failed. Rolling back changes..."

    if [ -d "$BACKUP_DIR" ]; then
        # Restore backups
        if [ -d "$BACKUP_DIR/ubisys" ]; then
            rm -rf "$HA_CONFIG_DIR/custom_components/ubisys"
            cp -r "$BACKUP_DIR/ubisys" "$HA_CONFIG_DIR/custom_components/" 2>/dev/null || true
        fi

        # Restore quirks
        for quirk in ubisys_j1.py ubisys_d1.py ubisys_s1.py ubisys_common.py; do
            if [ -f "$BACKUP_DIR/$quirk" ]; then
                cp "$BACKUP_DIR/$quirk" "$HA_CONFIG_DIR/custom_zha_quirks/" 2>/dev/null || true
            fi
        done

        if [ -f "$BACKUP_DIR/configuration.yaml" ]; then
            cp "$BACKUP_DIR/configuration.yaml" "$HA_CONFIG_DIR/" 2>/dev/null || true
        fi

        success "Rollback completed"
    fi

    exit 1
}

# Set up error trap
trap rollback ERR

# Main installation flow
main() {
    echo ""
    print_message "$GREEN" "============================================"
    print_message "$GREEN" "  Ubisys Home Assistant Integration Installer"
    print_message "$GREEN" "============================================"
    echo ""

    check_ha_directory
    create_backup
    create_directories
    install_integration
    install_quirks
    update_configuration
    validate_configuration
    print_completion
}

# Run main
main
