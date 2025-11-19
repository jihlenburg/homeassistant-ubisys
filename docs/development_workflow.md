# Development Workflow

This document describes the fast-iteration development workflow for the Ubisys integration.

## Overview

There are two development workflows available:

1. **Release-Based Workflow** (Traditional)
   - Commit → Tag → Release → HACS Update
   - Time per iteration: 5-10 minutes
   - Use for: Official releases to users

2. **Direct-Push Workflow** (Fast Development) ⚡
   - Save → Sync → Restart
   - Time per iteration: 45-90 seconds
   - Use for: Active development and debugging

## Fast Development Workflow

### Prerequisites

1. **SSH Access Configured**
   - Advanced SSH & Web Terminal add-on installed on Home Assistant
   - SSH key configured: `/Users/jihlenburg/.ssh/homeadmin_ed25519`
   - User `homeadmin` has sudo privileges (wheel group)

2. **Verify Prerequisites**
   ```bash
   # Test SSH connection
   ssh -i /Users/jihlenburg/.ssh/homeadmin_ed25519 homeadmin@homeassistant.local "echo OK"

   # Verify rsync and ha CLI available
   ssh -i /Users/jihlenburg/.ssh/homeadmin_ed25519 homeadmin@homeassistant.local "which rsync && which ha"

   # Verify sudo access
   ssh -i /Users/jihlenburg/.ssh/homeadmin_ed25519 homeadmin@homeassistant.local "groups"
   # Should show: homeadmin wheel
   ```

### Development Commands

#### Full Deployment (Deploy + Restart)

Use this for most development work:

```bash
# From repository root
./scripts/deploy.sh

# With log tailing
./scripts/deploy.sh --logs
```

**What it does:**
1. Syncs all files from `custom_components/ubisys/` to Home Assistant
2. Removes deleted files remotely (via `--delete` flag)
3. Cleans Python cache (`__pycache__`, `*.pyc`)
4. Restarts Home Assistant Core automatically
5. Optionally tails logs filtered for ubisys/calibration/j1

**Timeline:**
- Sync: ~5 seconds
- HA Core restart: ~30-45 seconds
- **Total: ~45-90 seconds**

#### Quick Sync (No Restart)

Use this when you want to manually reload the integration:

```bash
./scripts/sync.sh
```

**What it does:**
1. Syncs files only (no restart)
2. You manually reload via UI: Configuration → Integrations → Ubisys → ⋮ → Reload

**When to use:**
- Testing small changes
- Want to keep HA running (e.g., monitoring other devices)
- Deploying documentation/non-code changes

### Typical Development Cycle

```bash
# 1. Make code changes in editor
vim custom_components/ubisys/j1_calibration.py

# 2. Run local CI checks (recommended but optional)
make ci

# 3. Deploy to Home Assistant
./scripts/deploy.sh --logs

# 4. Watch logs, test changes on hardware
# ... logs streaming ...
# Press Ctrl+C when done

# 5. Iterate: Make more changes, repeat from step 1
```

### How It Works

The deployment scripts use **rsync with elevated privileges** to bypass file permission issues:

```bash
rsync -avz \
    --delete \
    --no-owner --no-group \
    --exclude '__pycache__' \
    --rsync-path="sudo rsync" \
    -e "ssh -i $SSH_KEY" \
    ./custom_components/ubisys/ \
    homeadmin@homeassistant.local:/config/custom_components/ubisys/
```

**Key Flags:**
- `--rsync-path="sudo rsync"` - Elevates privileges on remote to write root-owned files
- `--no-owner --no-group` - Prevents UID/GID metadata errors
- `--delete` - Syncs file deletions (keeps remote clean)
- `-a` - Archive mode (recursive, preserves symlinks/permissions/timestamps)
- `-z` - Compress during transfer (faster over network)

This solves the file locking issue we encountered earlier:
```
❌ OLD: cp: can't create '/config/custom_components/ubisys/j1_calibration.py': File exists
✅ NEW: rsync with sudo elevation handles root-owned files
```

### Troubleshooting

#### Error: "Sync failed"

**Possible causes:**

1. **SSH key not configured**
   ```bash
   # Verify SSH key exists
   ls -l /Users/jihlenburg/.ssh/homeadmin_ed25519

   # Test SSH connection
   ssh -i /Users/jihlenburg/.ssh/homeadmin_ed25519 homeadmin@homeassistant.local "echo OK"
   ```

2. **No sudo access**
   ```bash
   # Check if user is in wheel group
   ssh -i /Users/jihlenburg/.ssh/homeadmin_ed25519 homeadmin@homeassistant.local "groups"
   # Should show: homeadmin wheel
   ```

3. **Wrong hostname**
   - Try IP address instead: Edit `REMOTE_HOST` in script
   ```bash
   # Find Home Assistant IP
   ping homeassistant.local

   # Edit deploy.sh and sync.sh
   REMOTE_HOST="192.168.1.100"  # Use actual IP
   ```

#### Error: "Restart command failed"

**Possible causes:**

1. **ha CLI not available**
   ```bash
   # Verify ha CLI exists
   ssh -i /Users/jihlenburg/.ssh/homeadmin_ed25519 homeadmin@homeassistant.local "which ha"
   ```

2. **Supervisor communication issue**
   - Check Advanced SSH & Web Terminal add-on is running
   - Check Supervisor is healthy in HA UI

3. **API token error** (Fixed in scripts)
   ```
   Error: unauthorized: missing or invalid API token
   ```

   **Cause:** Non-login SSH shells don't source `/etc/profile.d/` scripts that set `SUPERVISOR_TOKEN`

   **Solution:** Scripts use login shell: `bash -lc 'ha core restart'`

   If you see this error in custom commands:
   ```bash
   # WRONG (no API token):
   ssh homeadmin@ha "ha core info"

   # CORRECT (sources environment):
   ssh homeadmin@ha "bash -lc 'ha core info'"
   ```

   The `-l` flag forces bash to act as a login shell, sourcing profile scripts that provide the Supervisor API token.

#### Files Not Updating

**Possible causes:**

1. **Python cache not cleared**
   - Script automatically clears `__pycache__` and `*.pyc`
   - If issues persist, manually clear:
   ```bash
   ssh -i /Users/jihlenburg/.ssh/homeadmin_ed25519 homeadmin@homeassistant.local \
       "rm -rf /config/custom_components/ubisys/__pycache__"
   ```

2. **Integration not reloading**
   - Full Core restart via `deploy.sh` should reload everything
   - If issues persist, try full HA restart:
   ```bash
   ssh -i /Users/jihlenburg/.ssh/homeadmin_ed25519 homeadmin@homeassistant.local \
       "ha core restart"
   ```

### Best Practices

1. **Run CI Before Deployment**
   ```bash
   make ci && ./scripts/deploy.sh
   ```
   Catches linting/type errors before deploying to hardware.

2. **Use Log Tailing for Active Development**
   ```bash
   ./scripts/deploy.sh --logs
   ```
   Immediately see integration behavior after restart.

3. **Manual Reload for Small Changes**
   - If changing only log messages or non-functional code
   - Use `./scripts/sync.sh` + manual reload (faster than full restart)

4. **Commit Frequently During Development**
   - Fast deployment doesn't replace git
   - Commit working changes to avoid losing work
   - But skip git push/release until feature is complete

5. **Test with Real Hardware**
   - Calibration logic requires actual J1 device
   - Input monitoring requires physical button presses
   - Use fast deployment for rapid hardware testing iterations

## Release-Based Workflow (Traditional)

When you're ready to release to users:

1. **Ensure All CI Checks Pass**
   ```bash
   make ci
   ```

2. **Update Version and Changelog**
   ```bash
   # Edit custom_components/ubisys/manifest.json
   "version": "X.Y.Z"

   # Move "Unreleased" items in CHANGELOG.md to new version
   ## [X.Y.Z] - YYYY-MM-DD
   ```

3. **Commit, Tag, Push**
   ```bash
   git add -A
   git commit -m "chore: bump version to X.Y.Z"
   git tag -a vX.Y.Z -m "Release version X.Y.Z"
   git push origin main
   git push origin vX.Y.Z
   ```

4. **Create GitHub Release**
   ```bash
   ./scripts/create_release.sh vX.Y.Z
   ```

5. **HACS Auto-Update**
   - HACS detects new tag automatically
   - Users see update notification
   - "Read release announcement" links to GitHub Release

## Comparison: Fast vs. Release Workflow

| Aspect | Fast Development | Release-Based |
|--------|------------------|---------------|
| **Time per iteration** | 45-90 seconds | 5-10 minutes |
| **User impact** | None (local only) | All users notified |
| **CI enforcement** | Optional (recommended) | Required (git hooks) |
| **Use case** | Active development | Official releases |
| **Hardware testing** | Immediate | After release |
| **Risk** | Low (local only) | High (public release) |

## When to Use Each Workflow

### Use Fast Development Workflow When:
- Debugging calibration logic with real J1 hardware
- Testing input monitoring with physical button presses
- Iterating on error handling and edge cases
- Experimenting with new features
- Fixing bugs found during testing

### Use Release-Based Workflow When:
- Feature is complete and tested
- Bug fix is verified on hardware
- Documentation is updated
- Ready to share with users
- CI checks all pass

## Advanced: File Watchers (Optional)

For even faster iteration, use file watchers to automatically deploy on save:

```bash
# Install entr (macOS)
brew install entr

# Auto-deploy on any Python file change
ls custom_components/ubisys/*.py | entr -r ./scripts/deploy.sh
```

**Effect:** Every time you save a Python file, deployment runs automatically.

**Caution:** This restarts HA Core frequently. Use only during active development sessions.

## Architecture Details

### Home Assistant OS Container Structure

```
┌─────────────────────────────────────────────┐
│ Home Assistant OS (Host)                    │
│                                             │
│  ┌─────────────────────────────────────┐  │
│  │ Core Container                       │  │
│  │ - Runs Home Assistant Core           │  │
│  │ - Loads integrations from /config   │  │
│  │ - Owned by root (UID 0)              │  │
│  └─────────────────────────────────────┘  │
│                                             │
│  ┌─────────────────────────────────────┐  │
│  │ SSH Add-on Container                 │  │
│  │ - homeadmin user (UID 1000)          │  │
│  │ - Has rsync, ha CLI                  │  │
│  │ - Member of wheel group (sudo)       │  │
│  └─────────────────────────────────────┘  │
│                                             │
│  ┌─────────────────────────────────────┐  │
│  │ Shared Volume: /config               │  │
│  │ - Mounted in both containers         │  │
│  │ - Files owned by root (UID 0)        │  │
│  │ - custom_components/ubisys/ here     │  │
│  └─────────────────────────────────────┘  │
└─────────────────────────────────────────────┘
```

### Why rsync with sudo?

Files in `/config/custom_components/` are owned by root (UID 0) because the Core container runs as root. When we SSH into the SSH Add-on container as `homeadmin` (UID 1000), we don't have permission to overwrite these files.

**Traditional cp command fails:**
```bash
cp /tmp/file.py /config/custom_components/ubisys/file.py
# Error: Permission denied (can't overwrite root-owned file)
```

**rsync with sudo elevation succeeds:**
```bash
rsync --rsync-path="sudo rsync" /tmp/file.py homeadmin@ha:/config/custom_components/ubisys/
# Success: sudo elevation on remote allows writing to root-owned files
```

The `--no-owner --no-group` flags prevent rsync from trying to preserve the source file's ownership (which would fail due to UID mismatch).

## References

- [Advanced SSH & Web Terminal Add-on](https://github.com/hassio-addons/addon-ssh) - Official add-on repository
- [How to Use Rsync to Sync Local and Remote Directories](https://www.digitalocean.com/community/tutorials/how-to-use-rsync-to-sync-local-and-remote-directories) - rsync tutorial
