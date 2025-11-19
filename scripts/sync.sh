#!/bin/bash
#
# sync.sh - Quick file sync without restarting Home Assistant
#
# This script syncs files to Home Assistant but does NOT restart Core.
# Use this when you want to manually reload the integration via the UI
# (Configuration → Integrations → Ubisys → ⋮ → Reload).
#
# Usage:
#   ./scripts/sync.sh
#
# For full deployment with automatic restart, use: ./scripts/deploy.sh
#

set -e

# --- CONFIGURATION ---
REMOTE_HOST="homeassistant.local"
REMOTE_USER="homeadmin"
SSH_KEY="/Users/jihlenburg/.ssh/homeadmin_ed25519"
COMPONENT="ubisys"
# ---------------------

LOCAL_PATH="./custom_components/$COMPONENT/"
REMOTE_PATH="/config/custom_components/$COMPONENT/"

echo "📦 Syncing $COMPONENT to $REMOTE_HOST (no restart)..."

# Verify local path exists
if [ ! -d "$LOCAL_PATH" ]; then
    echo "❌ Error: Local path not found: $LOCAL_PATH"
    exit 1
fi

# Verify SSH key exists
if [ ! -f "$SSH_KEY" ]; then
    echo "❌ Error: SSH key not found: $SSH_KEY"
    exit 1
fi

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
    echo "❌ Sync failed!"
    exit 1
fi

echo ""
echo "✅ Sync complete!"
echo ""
echo "Files synced but Home Assistant Core NOT restarted."
echo "To apply changes:"
echo "  1. Go to Configuration → Integrations"
echo "  2. Find 'Ubisys Zigbee Devices'"
echo "  3. Click ⋮ → Reload"
echo ""
echo "Or run: ./scripts/deploy.sh (for automatic restart)"
