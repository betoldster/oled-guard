#!/usr/bin/env bash
# uninstall.sh — removes OLED Guard completely

set -e

SERVICE_NAME="oled-guard.service"
SERVICE_DIR="$HOME/.config/systemd/user"
INSTALL_DIR="$HOME/.config/oled-guard"

echo "── OLED Guard Uninstaller ──"

echo "→ Stopping and disabling service..."
systemctl --user disable --now "$SERVICE_NAME" 2>/dev/null || true
systemctl --user reset-failed "$SERVICE_NAME" 2>/dev/null || true

echo "→ Removing installed files..."
rm -rf "$INSTALL_DIR"
rm -f  "$SERVICE_DIR/$SERVICE_NAME"
rm -f  "$SERVICE_DIR/graphical-session.target.wants/$SERVICE_NAME"

echo "→ Reloading systemd..."
systemctl --user daemon-reload

echo ""
echo "✓ OLED Guard removed."
