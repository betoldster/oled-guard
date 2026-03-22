#!/usr/bin/env bash
# update.sh — OLED Guard updater
# Can be run from the repo directory OR from ~/.config/oled-guard/

set -e

INSTALL_DIR="$HOME/.config/oled-guard"
SERVICE_DIR="$HOME/.config/systemd/user"
SERVICE_NAME="oled-guard.service"
PYTHON="$(which python3)"

echo "── OLED Guard Updater ──"
echo ""

# ── 0. Locate repo ──────────────────────────────────────────────────────────────
# If run from the install dir (not a git repo), navigate to the saved repo path
if ! git -C "$(pwd)" rev-parse --git-dir &>/dev/null; then
    REPO_PATH_FILE="$INSTALL_DIR/.repo_path"
    if [[ ! -f "$REPO_PATH_FILE" ]]; then
        echo "ERROR: Cannot find the oled-guard repo."
        echo "  Re-clone it and run: bash install.sh"
        exit 1
    fi
    REPO_DIR="$(cat "$REPO_PATH_FILE")"
    if [[ ! -d "$REPO_DIR/.git" ]]; then
        echo "ERROR: Saved repo path '$REPO_DIR' no longer exists."
        echo "  Re-clone it and run: bash install.sh"
        exit 1
    fi
    echo "→ Using repo at $REPO_DIR"
    cd "$REPO_DIR"
fi

# ── 1. Pull latest changes ──────────────────────────────────────────────────────
echo "→ Fetching latest changes..."
git fetch origin

LOCAL=$(git rev-parse HEAD)
REMOTE=$(git rev-parse @{u} 2>/dev/null || echo "")

if [[ -z "$REMOTE" ]]; then
    echo "  WARNING: No upstream branch tracked. Run 'git pull' manually."
elif [[ "$LOCAL" == "$REMOTE" ]]; then
    echo "  ✓ Already up to date — nothing to do."
    exit 0
fi

# Detect new files added upstream vs current HEAD
NEW_FILES=$(git diff --name-only --diff-filter=A HEAD @{u} 2>/dev/null || true)

echo "→ Pulling changes..."
git pull

# ── 2. Copy updated scripts ─────────────────────────────────────────────────────
echo "→ Updating scripts in $INSTALL_DIR..."
mkdir -p "$INSTALL_DIR"
cp blackout.py watcher.py update.sh "$INSTALL_DIR/"
chmod +x "$INSTALL_DIR/blackout.py" "$INSTALL_DIR/watcher.py" "$INSTALL_DIR/update.sh"
echo "  ✓ blackout.py, watcher.py, and update.sh updated"

echo "→ Updating management scripts in $INSTALL_DIR..."
cp install.sh uninstall.sh update.sh "$INSTALL_DIR/"
chmod +x "$INSTALL_DIR/install.sh" "$INSTALL_DIR/uninstall.sh" "$INSTALL_DIR/update.sh"
echo "  ✓ install.sh, uninstall.sh, and update.sh updated"

# ── 3. Handle any new files added in this update ────────────────────────────────
if [[ -n "$NEW_FILES" ]]; then
    echo "→ New files detected in this update:"
    while IFS= read -r file; do
        echo "    + $file"
    done <<< "$NEW_FILES"

    # Copy any new .py scripts to the install dir
    while IFS= read -r file; do
        if [[ "$file" == *.py && -f "$file" ]]; then
            cp "$file" "$INSTALL_DIR/"
            chmod +x "$INSTALL_DIR/$file"
            echo "  ✓ Installed new script: $file"
        fi
    done <<< "$NEW_FILES"

    # Install updated/new systemd service if it changed
    if echo "$NEW_FILES" | grep -q "oled-guard.service"; then
        echo "→ New service file detected — reinstalling..."
        cp oled-guard.service "$SERVICE_DIR/$SERVICE_NAME"
        sed -i "s|/usr/bin/python3|$PYTHON|g" "$SERVICE_DIR/$SERVICE_NAME"
        systemctl --user daemon-reload
        echo "  ✓ Service file updated and reloaded"
    fi
else
    echo "→ No new files in this update"
fi

# ── 4. Update service file if it changed (but wasn't new) ──────────────────────
CHANGED_SERVICE=$(git diff --name-only HEAD@{1} HEAD 2>/dev/null | grep "oled-guard.service" || true)
if [[ -n "$CHANGED_SERVICE" ]]; then
    echo "→ Service file changed — reinstalling..."
    cp oled-guard.service "$SERVICE_DIR/$SERVICE_NAME"
    sed -i "s|/usr/bin/python3|$PYTHON|g" "$SERVICE_DIR/$SERVICE_NAME"
    systemctl --user daemon-reload
    echo "  ✓ Service file updated and reloaded"
fi

# ── 5. Restart the service to apply changes ─────────────────────────────────────
echo "→ Restarting oled-guard service..."
systemctl --user restart oled-guard
echo "  ✓ Service restarted"

echo ""
echo "✓ OLED Guard updated successfully!"
echo ""
echo "Useful commands:"
echo "  systemctl --user status oled-guard        # check status"
echo "  journalctl --user -u oled-guard -f        # live logs"
