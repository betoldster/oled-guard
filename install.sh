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

# ── 4. Install systemd service ─────────────────────────────────────────────────
echo "→ Installing systemd user service..."
mkdir -p "$SERVICE_DIR"
cp oled-guard.service "$SERVICE_DIR/$SERVICE_NAME"

# Patch ExecStart to use whichever python3 is active
sed -i "s|/usr/bin/python3|$PYTHON|g" "$SERVICE_DIR/$SERVICE_NAME"
echo "  ExecStart patched → $PYTHON"

# ── 5. Enable and start ────────────────────────────────────────────────────────
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
