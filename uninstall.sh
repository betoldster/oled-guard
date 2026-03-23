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

echo "→ Removing desktop entry and icon..."
rm -f "$HOME/.local/share/applications/oled-guard.desktop"
rm -f "$HOME/.local/share/icons/hicolor/scalable/apps/oled-guard.svg"
gtk-update-icon-cache -f -t "$HOME/.local/share/icons/hicolor" 2>/dev/null || true
update-desktop-database "$HOME/.local/share/applications" 2>/dev/null || true

echo "→ Reloading systemd..."
systemctl --user daemon-reload

echo ""
echo "✓ OLED Guard removed."
