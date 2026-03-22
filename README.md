# 🖤 OLED Guard

> Burn-in protection for OLED monitors on Wayland Linux — lightweight, instant, and automatic.

![Python](https://img.shields.io/badge/python-3.10%2B-blue?logo=python&logoColor=white)
![Platform](https://img.shields.io/badge/platform-Wayland%20Linux-informational?logo=linux&logoColor=white)
![License](https://img.shields.io/badge/license-MIT-green)
![systemd](https://img.shields.io/badge/managed%20by-systemd-orange)

Modern Linux desktops have largely dropped traditional screensavers, leaving OLED monitors exposed to static content indefinitely. OLED Guard fills that gap: it watches for inactivity and blanks all screens completely black after a configurable idle timeout. Dismiss it instantly with a click or keypress.

---

## Features

- 🖥️ **Multi-monitor** — covers every connected display simultaneously
- ⚡ **Instant dismiss** — left click or any key closes it immediately
- 🔋 **Near-zero resource usage** — sleeping daemon + blocking event wait
- 🔌 **Auto-starts on login** — managed as a systemd user service
- 🧩 **Wayland-native** — idle detection via DBus (GNOME, KDE, and others)
- 📦 **Minimal dependencies** — `python3-dbus` + `tkinter` (usually pre-installed)

---

## How it works

```
watcher.py        (always running, ~6 MB RAM, <0.1% CPU)
    │  polls DBus for idle time every 15 s
    │  after 5 min idle ──►
    └─► blackout.py        (active only while blanked, ~12 MB RAM, 0% CPU)
            one fullscreen black window per monitor
            exits instantly on click or any keypress
```

Idle time is read from the DBus session bus, tried in order:

| Interface | Compositor |
|-----------|-----------|
| `org.gnome.Mutter.IdleMonitor` | GNOME, PikaOS |
| `org.freedesktop.ScreenSaver` | KDE Plasma, generic |
| `org.kde.screensaver` | KDE fallback |

---

## Requirements

- Wayland compositor (GNOME, KDE Plasma, sway, …)
- Python 3.10+
- `python3-tk` — for the blackout window
- `python3-dbus` — for idle detection
- `xrandr` (`x11-xserver-utils`) — for accurate per-monitor geometry detection (optional, falls back to virtual desktop)

The installer checks and installs all dependencies automatically.

---

## Installation

```bash
git clone https://github.com/betoldster/oled-guard.git
cd oled-guard
bash install.sh
```

The installer will:
1. Copy `blackout.py`, `watcher.py`, `install.sh`, `uninstall.sh`, and `update.sh` to `~/.config/oled-guard/`
2. Install `python3-tk` if missing (supports both Homebrew and apt)
3. Install `python3-dbus` if missing
4. Install `xrandr` if missing (for accurate per-monitor geometry)
5. Register and start the systemd user service

---

## Usage

### Service management

```bash
systemctl --user status oled-guard        # check if running
systemctl --user stop oled-guard          # stop temporarily
systemctl --user start oled-guard         # start again
systemctl --user restart oled-guard       # restart after config change
journalctl --user -u oled-guard -f        # live logs
```

### Test blackout manually

```bash
python3 ~/.config/oled-guard/blackout.py
```

Press `ESC`, click, or press any key to dismiss.

---

## Configuration

Edit `~/.config/oled-guard/watcher.py`:

```python
# Idle timeout before blackout (default: 5 minutes)
IDLE_THRESHOLD_SECONDS = 5 * 60

# How often to poll for idle time (default: 15 seconds)
POLL_INTERVAL_SECONDS = 15
```

Then restart the service:

```bash
systemctl --user restart oled-guard
```

---

## Troubleshooting

### Blackout never triggers

```bash
journalctl --user -u oled-guard -f
```

If you see `No idle-time DBus interface found`, your compositor uses a different DBus interface. Open an issue with your DE name and the output of:

```bash
dbus-send --session --print-reply --dest=org.freedesktop.DBus \
  /org/freedesktop/DBus org.freedesktop.DBus.ListNames
```

### Doesn't cover all monitors

The installer automatically installs `xrandr` (`x11-xserver-utils`) for per-monitor geometry detection. If it is still missing, install it manually:

```bash
sudo apt install x11-xserver-utils
```

Without it, the fallback mode covers the entire virtual desktop.

### `No module named '_tkinter'` error

If you're using Homebrew Python:

```bash
brew install python-tk
```

Or for a specific version:

```bash
brew install python-tk@3.14
```

### Service won't start after login

Check that `graphical-session.target` is active:

```bash
systemctl --user status graphical-session.target
```

If it's not, add `watcher.py` to your compositor's autostart as a workaround.

---

## Updating

Pull the latest changes and apply them in one command:

```bash
bash update.sh
```

The updater will:
1. Fetch and pull the latest commits
2. Copy updated `blackout.py`, `watcher.py`, `install.sh`, `uninstall.sh`, and `update.sh` to `~/.config/oled-guard/`
3. Detect and install any **new files** added in the update
4. Reinstall the systemd service unit if it changed
5. Restart the service automatically

If you are already on the latest version it exits immediately with no changes.

---

## Uninstall

From the cloned repo directory, or from the installed location:

```bash
bash uninstall.sh
# or, if you no longer have the repo:
bash ~/.config/oled-guard/uninstall.sh
```

---

## Contributing

PRs welcome. Especially interested in:
- Compatibility reports for non-GNOME compositors
- `wlr-layer-shell` native Wayland fullscreen (no Xwayland needed)
- Alternative idle detection for niche setups

---

## License

MIT — see [LICENSE](LICENSE).
