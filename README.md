# 🖤 OLED TV Guard

> Burn-in protection for TV OLEDs used as monitors on Wayland Linux — lightweight, instant, and automatic.

![Python](https://img.shields.io/badge/python-3.10%2B-blue?logo=python&logoColor=white)
![Platform](https://img.shields.io/badge/platform-Wayland%20Linux-informational?logo=linux&logoColor=white)
![License](https://img.shields.io/badge/license-MIT-green)
![systemd](https://img.shields.io/badge/managed%20by-systemd-orange)

Modern Linux desktops have largely dropped traditional screensavers, leaving OLED TVs used as PC monitors exposed to static content indefinitely. Unlike dedicated OLED PC monitors, OLED TVs such as LG's OLED lineup have no proper desktop standby mode - instead they start cycling through random images and eventually switch themselves off, constantly interrupting your workflow. OLED Guard fills that gap: it watches for inactivity and blanks all screens completely black after a configurable idle timeout. Dismiss it instantly with a left mouse click.

Due to the nature of OLED, a fully black screen draws very little power - though it is not the most power-efficient solution compared to a true display-off state. I built this app primarily to reduce the risk of burn-in from static elements like taskbars and desktop icons. It lets me step away from my desk without having to think about it.

---

## Features

- 🖥️ **Multi-monitor** — covers every connected display simultaneously
- ⚡ **Instant dismiss** — left click, `ESC`, or any key closes it immediately
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
- One of the following for accurate per-monitor geometry detection (optional, falls back to virtual desktop):
  - GNOME Wayland: uses `python3-dbus` (already required — no extra tool needed)
  - wlroots compositors (sway, Hyprland, …): `wlr-randr`
  - KDE Plasma: `kscreen-doctor` (included with KDE)
  - X11 / Xwayland fallback: `xrandr` (`x11-xserver-utils`)

The installer checks and installs all dependencies automatically.

---

## Installation

```bash
git clone https://github.com/betoldster/oled-guard.git
cd oled-guard
bash install.sh
```

The installer will:
1. Copy all scripts to `~/.config/oled-guard/`
2. Install `python3-tk` if missing (supports both Homebrew and apt)
3. Install `python3-dbus` if missing
4. Detect available monitor geometry tools (`wlr-randr`, `kscreen-doctor`, GNOME Mutter DBus, `xrandr`)
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

`xrandr` (`x11-xserver-utils`) is an **X11 tool** and does not reliably detect individual monitor geometries under native Wayland. OLED Guard now uses Wayland-native detection methods instead, tried in this order:

| Method | Compositor | What to install |
|--------|-----------|-----------------|
| GNOME Mutter DBus | GNOME Wayland | Nothing — uses `python3-dbus` (already required) |
| `wlr-randr` | sway, Hyprland, wlroots | `sudo apt install wlr-randr` |
| `kscreen-doctor` | KDE Plasma | Included with KDE |
| `xrandr` | X11 / Xwayland | `sudo apt install x11-xserver-utils` |

If none of the above are available, the fallback mode covers the entire virtual desktop with a single window.

The installer automatically checks which tools are present and reports what it finds.

### `No module named '_tkinter'` error

If you're using Homebrew Python:

```bash
brew install python-tk
```

Or for a specific Python version (e.g. 3.12):

```bash
brew install python-tk@3.12
```

### ESC or keypress doesn't dismiss the blackout

This can happen on compositors that don't honor focus requests for
`overrideredirect` windows (common with XWayland). The blackout window
uses `grab_set()` to capture all keyboard and pointer input, so if you
encounter this issue make sure you are running the latest version:

```bash
bash update.sh
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
bash ~/.config/oled-guard/update.sh
```

Or from the repo directory:

```bash
bash update.sh
```

`update.sh` will:
1. Pull the latest source (`git pull`)
2. Copy updated scripts to `~/.config/oled-guard/`
3. Refresh and re-patch the systemd service file
4. Reload systemd and restart the service

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
