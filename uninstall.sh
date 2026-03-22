#!/usr/bin/env bash
# uninstall.sh — removes OLED Guard completely

set -e

echo "── OLED Guard Uninstaller ──"

echo "→ Stopping and disabling service..."
systemctl --user disable --now oled-guard.service 2>/dev/null || true

echo "→ Removing files..."
rm -rf "$HOME/.config/oled-guard"
rm -f  "$HOME/.config/systemd/user/oled-guard.service"

echo "→ Reloading systemd..."
systemctl --user daemon-reload

echo ""
echo "✓ OLED Guard removed."
