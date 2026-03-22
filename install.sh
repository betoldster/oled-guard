#!/usr/bin/env bash
# install.sh — OLED Guard installer
# Run once from the repo directory: bash install.sh

set -e

INSTALL_DIR="$HOME/.config/oled-guard"
SERVICE_DIR="$HOME/.config/systemd/user"
SERVICE_NAME="oled-guard.service"
PYTHON="$(which python3)"

echo "── OLED Guard Installer ──"
echo "   Python: $PYTHON"
echo ""

# ── 1. Copy scripts ────────────────────────────────────────────────────────────
echo "→ Copying scripts to $INSTALL_DIR"
mkdir -p "$INSTALL_DIR"
cp blackout.py watcher.py "$INSTALL_DIR/"
chmod +x "$INSTALL_DIR/blackout.py" "$INSTALL_DIR/watcher.py"

echo "→ Copying management scripts to $INSTALL_DIR"
cp install.sh uninstall.sh update.sh "$INSTALL_DIR/"
chmod +x "$INSTALL_DIR/install.sh" "$INSTALL_DIR/uninstall.sh" "$INSTALL_DIR/update.sh"

# ── 2. Check tkinter ───────────────────────────────────────────────────────────
echo "→ Checking tkinter..."
if python3 -c "import tkinter" 2>/dev/null; then
    echo "  ✓ tkinter available"
else
    echo "  ✗ tkinter missing — installing..."
    if [[ "$PYTHON" == *"linuxbrew"* || "$PYTHON" == *"homebrew"* ]]; then
        echo "    Detected Homebrew Python → brew install python-tk"
        brew install python-tk || {
            echo "  ERROR: brew install python-tk failed."
            echo "  Try: brew install python-tk@$(python3 -V 2>&1 | grep -oP '\d+\.\d+')"
            exit 1
        }
    elif command -v apt &>/dev/null; then
        echo "    Detected apt → sudo apt install python3-tk"
        sudo apt install -y python3-tk || { echo "  ERROR: apt install python3-tk failed."; exit 1; }
    else
        echo "  ERROR: Cannot detect package manager. Install tkinter manually."
        exit 1
    fi

    # Verify
    python3 -c "import tkinter" 2>/dev/null || {
        echo "  ERROR: tkinter still not importable after install."
        echo "  Homebrew tip: brew install python-tk@$(python3 -V 2>&1 | grep -oP '\d+\.\d+')"
        exit 1
    }
    echo "  ✓ tkinter installed and verified"
fi

# ── 3. Check dbus-python ───────────────────────────────────────────────────────
echo "→ Checking dbus-python..."
if python3 -c "import dbus" 2>/dev/null; then
    echo "  ✓ dbus-python available"
else
    echo "  ✗ dbus-python missing — installing..."
    if [[ "$PYTHON" == *"linuxbrew"* || "$PYTHON" == *"homebrew"* ]]; then
        echo "    Detected Homebrew Python → installing build deps + pip"
        command -v apt &>/dev/null && sudo apt install -y libdbus-1-dev pkg-config 2>/dev/null || true
        python3 -m pip install dbus-python --quiet || {
            echo "  WARNING: pip install dbus-python failed."
            echo "  Try: sudo apt install python3-dbus"
        }
    elif command -v apt &>/dev/null; then
        sudo apt install -y python3-dbus || {
            echo "  WARNING: apt install python3-dbus failed. Install manually."
        }
    else
        echo "  WARNING: Cannot detect package manager. Install dbus-python manually."
    fi

    python3 -c "import dbus" 2>/dev/null && echo "  ✓ dbus-python installed" \
        || echo "  WARNING: dbus-python still not importable — watcher may fail."
fi

# ── 4. Check monitor geometry detection ────────────────────────────────────────
echo "→ Checking monitor geometry detection..."
MONITOR_TOOL_FOUND=false

if command -v wlr-randr &>/dev/null; then
    echo "  ✓ wlr-randr available (wlroots compositors: sway, Hyprland, …)"
    MONITOR_TOOL_FOUND=true
fi

if command -v kscreen-doctor &>/dev/null; then
    echo "  ✓ kscreen-doctor available (KDE Plasma)"
    MONITOR_TOOL_FOUND=true
fi

if python3 -c "
import dbus, sys
try:
    bus = dbus.SessionBus()
    bus.get_object('org.gnome.Mutter.DisplayConfig', '/org/gnome/Mutter/DisplayConfig')
    sys.exit(0)
except Exception:
    sys.exit(1)
" 2>/dev/null; then
    echo "  ✓ GNOME Mutter DisplayConfig available (GNOME Wayland)"
    MONITOR_TOOL_FOUND=true
fi

if command -v xrandr &>/dev/null; then
    echo "  ✓ xrandr available (X11 / Xwayland fallback)"
    MONITOR_TOOL_FOUND=true
fi

if [ "$MONITOR_TOOL_FOUND" = false ]; then
    echo "  ✗ No monitor detection tool found."
    echo "  NOTE: xrandr (x11-xserver-utils) is an X11 tool and may not detect"
    echo "        all monitors under native Wayland. Wayland-native tools are preferred:"
    echo "    wlroots (sway/Hyprland): sudo apt install wlr-randr"
    echo "    KDE Plasma:              kscreen-doctor is included with KDE"
    echo "    GNOME:                   uses DBus (no extra tool needed)"
    echo "  Falling back to xrandr as a last resort..."
    if command -v apt &>/dev/null; then
        sudo apt install -y x11-xserver-utils || {
            echo "  WARNING: apt install x11-xserver-utils failed."
            echo "  Multi-monitor detection will fall back to virtual desktop size."
        }
    else
        echo "  WARNING: Cannot detect package manager."
        echo "  Multi-monitor detection will fall back to virtual desktop size."
    fi
    command -v xrandr &>/dev/null && echo "  ✓ xrandr installed" \
        || echo "  WARNING: xrandr still not found — per-monitor blackout may not work correctly."
fi

# ── 5. Install systemd service ─────────────────────────────────────────────────
echo "→ Installing systemd user service..."
mkdir -p "$SERVICE_DIR"
cp oled-guard.service "$SERVICE_DIR/$SERVICE_NAME"

# Patch ExecStart to use whichever python3 is active
sed -i "s|/usr/bin/python3|$PYTHON|g" "$SERVICE_DIR/$SERVICE_NAME"
echo "  ExecStart patched → $PYTHON"

# ── 6. Enable and start ────────────────────────────────────────────────────────
echo "→ Enabling and starting oled-guard service..."
systemctl --user daemon-reload
systemctl --user enable "$SERVICE_NAME"
systemctl --user start "$SERVICE_NAME"

echo ""
echo "✓ OLED Guard is installed and running!"
echo ""
echo "Useful commands:"
echo "  systemctl --user status oled-guard        # check status"
echo "  journalctl --user -u oled-guard -f        # live logs"
echo "  systemctl --user restart oled-guard       # restart after config changes"
echo "  python3 ~/.config/oled-guard/blackout.py  # test blackout manually"
