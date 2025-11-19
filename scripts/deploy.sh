#!/bin/bash
#
# deploy.sh - Fast deployment to Home Assistant via SSH
#
# This script uses rsync with elevated privileges to deploy the ubisys
# integration to a running Home Assistant OS instance. It bypasses the
# traditional "git commit → release → HACS update" workflow for rapid
# iteration during development.
#
# Usage:
#   ./scripts/deploy.sh          # Deploy and restart Core
#   ./scripts/deploy.sh --logs   # Deploy, restart, and tail logs
#
# Prerequisites:
#   - SSH access configured to homeassistant.local
#   - homeadmin user with sudo privileges (wheel group)
#   - rsync installed on remote (default in Advanced SSH & Web Terminal)
#
# Based on: "Deploy Custom HA Add-on via SSH.md"
#

set -e

# --- CONFIGURATION ---
# Hostname or IP (can use homeassistant.local for mDNS)
REMOTE_HOST="homeassistant.local"
# SSH user configured in Advanced SSH & Web Terminal add-on
REMOTE_USER="homeadmin"
# SSH key path (adjust if different)
SSH_KEY="/Users/jihlenburg/.ssh/homeadmin_ed25519"
# Integration domain name
COMPONENT="ubisys"
# ---------------------

LOCAL_PATH="./custom_components/$COMPONENT/"
REMOTE_PATH="/config/custom_components/$COMPONENT/"

echo "🚀 Deploying $COMPONENT to $REMOTE_HOST..."

# Verify local path exists
if [ ! -d "$LOCAL_PATH" ]; then
    echo "❌ Error: Local path not found: $LOCAL_PATH"
    echo "   Run this script from the repository root."
    exit 1
fi

# Verify SSH key exists
if [ ! -f "$SSH_KEY" ]; then
    echo "❌ Error: SSH key not found: $SSH_KEY"
    echo "   Update SSH_KEY variable in this script."
    exit 1
fi

# RSYNC COMMAND ANALYSIS
# --rsync-path="sudo rsync": Elevates privileges on remote to write root-owned files
# --no-owner --no-group: Prevents metadata errors when crossing UID boundaries
# --delete: Ensures removed local files are removed remotely (sync deletions)
# -a: Archive mode (recursive, preserves symlinks, permissions, timestamps, etc.)
# -v: Verbose output
# -z: Compress during transfer (faster over network)
echo "📦 Syncing files..."
rsync -avz \
    --delete \
    --no-owner --no-group \
    --exclude '__pycache__' \
    --exclude '*.pyc' \
    --exclude '*.backup' \
    --exclude '*.bak' \
    --exclude '.git' \
    --exclude '.pytest_cache' \
    --exclude '*.egg-info' \
    --rsync-path="sudo rsync" \
    -e "ssh -i $SSH_KEY" \
    "$LOCAL_PATH" "$REMOTE_USER@$REMOTE_HOST:$REMOTE_PATH"

if [ $? -ne 0 ]; then
    echo ""
    echo "❌ Sync failed!"
    echo ""
    echo "Common issues:"
    echo "  1. SSH key not configured: Verify key is added to Advanced SSH & Web Terminal config"
    echo "  2. No sudo access: Verify homeadmin user is in wheel group"
    echo "  3. Wrong hostname: Try IP address instead of homeassistant.local"
    echo ""
    exit 1
fi

echo "✅ Sync complete"

# RESTART COMMAND
# Uses 'ha' CLI tool available in the SSH Add-on container
# This restarts only the Core container, not the entire host (~30-45 seconds)
# Using login shell (-l) to ensure proper environment variables (SUPERVISOR_TOKEN)
echo "🔄 Restarting Home Assistant Core..."
ssh -i "$SSH_KEY" "$REMOTE_USER@$REMOTE_HOST" "bash -lc 'ha core restart'"

if [ $? -ne 0 ]; then
    echo "❌ Restart command failed"
    exit 1
fi

echo ""
echo "✅ Deployment complete!"
echo ""
echo "Home Assistant Core is restarting (takes ~30-45 seconds)."
echo "The integration will reload automatically."

# Optional: Tail logs if --logs flag provided
if [ "$1" = "--logs" ]; then
    echo ""
    echo "👀 Tailing logs (Ctrl+C to stop)..."
    echo "   Filtering for: ubisys, calibration, j1"
    echo ""
    sleep 5  # Give HA a moment to start writing logs
    ssh -i "$SSH_KEY" "$REMOTE_USER@$REMOTE_HOST" \
        "bash -lc 'tail -f /config/home-assistant.log | grep -iE \"ubisys|calibration|j1\"'"
fi
