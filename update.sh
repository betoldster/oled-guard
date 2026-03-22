#!/usr/bin/env bash
# update.sh — OLED Guard updater
# Run from the repo directory: bash update.sh

set -e

INSTALL_DIR="$HOME/.config/oled-guard"
SERVICE_DIR="$HOME/.config/systemd/user"
SERVICE_NAME="oled-guard.service"
PYTHON="$(which python3)"

echo "── OLED Guard Updater ──"

# ── 1. Pull latest changes ─────────────────────────────────────────────────────
if git rev-parse --is-inside-work-tree &>/dev/null; then
    echo "→ Pulling latest changes..."
    git pull
else
    echo "  WARNING: Not inside a git repository — skipping git pull."
    echo "  To get the latest source, re-clone and run this script again."
fi

# ── 2. Check install dir ───────────────────────────────────────────────────────
if [[ ! -d "$INSTALL_DIR" ]]; then
    echo ""
    echo "  ERROR: OLED Guard does not appear to be installed."
    echo "  Run bash install.sh first."
    exit 1
fi

# ── 3. Copy updated scripts ────────────────────────────────────────────────────
echo "→ Updating scripts in $INSTALL_DIR"
cp blackout.py watcher.py "$INSTALL_DIR/"
chmod +x "$INSTALL_DIR/blackout.py" "$INSTALL_DIR/watcher.py"

# ── 4. Update service file (preserves python path patch) ──────────────────────
echo "→ Updating systemd service..."
cp oled-guard.service "$SERVICE_DIR/$SERVICE_NAME"
sed -i "s|/usr/bin/python3|$PYTHON|g" "$SERVICE_DIR/$SERVICE_NAME"

# ── 5. Reload and restart ──────────────────────────────────────────────────────
echo "→ Reloading systemd and restarting service..."
systemctl --user daemon-reload
systemctl --user restart "$SERVICE_NAME"

echo ""
echo "✓ OLED Guard updated and restarted!"
systemctl --user status "$SERVICE_NAME" --no-pager --lines=0
