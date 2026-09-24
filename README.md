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
- 🎬 **Video-aware** — no blackout while YouTube, mpv, VLC & co. are playing video — from any source, browser or local file
- ⚡ **Instant dismiss** — left click closes it immediately
- 🔋 **Near-zero resource usage** — sleeping daemon + blocking event wait
- 🔌 **Auto-starts on login** — managed as a systemd user service
- 🧩 **Wayland-native** — idle detection via DBus (GNOME, KDE, and others)
- 📦 **Minimal dependencies** — `python3-dbus` + `tkinter` (usually pre-installed)
- 🖱️ **App menu shortcut** — appears in GNOME, KDE, and other freedesktop-compliant app launchers with right-click actions for service management

---

## How it works

```
watcher.py        (always running, ~6 MB RAM, <0.1% CPU)
    │  polls DBus for idle time every 15 s
    │  after 5 min idle ──► video playing (idle inhibitor)? ──► skip
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

### Video playback (YouTube etc.)

Video players and browsers block session idle while a *video* is playing —
the mechanism that keeps a screensaver away during a movie. When the idle
threshold is reached, OLED Guard checks for such an idle inhibitor and skips
the blackout. This works for any source: browser (YouTube, streams, ...),
local files in VLC/mpv/Celluloid, Kodi, Flatpak apps via the portal.

Idle time itself is raw keyboard/mouse idle, so a truly idle desktop still
blanks, even with Steam, Discord etc. running in the background.

| Source | Compositor | Covers |
|--------|-----------|--------|
| `org.gnome.SessionManager` (idle flag) | GNOME | GNOME inhibit API, Wayland idle-inhibit protocol, portal |
| `org.freedesktop.PowerManagement.Inhibit` | KDE Plasma | `org.freedesktop.ScreenSaver.Inhibit`, portal |
| `org.freedesktop.login1` idle inhibitors | any | `systemd-inhibit --what=idle` |

| Situation | Result |
|-----------|--------|
| Video playing (fullscreen or visible window), mouse untouched | stays on |
| Video paused, minimized or in a background tab | blanks |
| Music only (browser "Playing audio" inhibits suspend, not idle) | blanks |
| App that blocks idle permanently | stays on → add it to `ignore_inhibitors` |

After `max_inhibited_idle_seconds` (default 4 h) of idle it blanks anyway.

Check what OLED Guard sees right now (e.g. with a YouTube video running):

```bash
python3 ~/.config/oled-guard/watcher.py --check
```

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
1. Copy all scripts to `~/.config/oled-guard/` and create `config.ini` there (only if it does not exist yet)
2. Install `python3-tk` if missing (supports both Homebrew and apt)
3. Install `python3-dbus` if missing
4. Detect available monitor geometry tools (`wlr-randr`, `kscreen-doctor`, GNOME Mutter DBus, `xrandr`)
5. Install desktop entry and icon to `~/.local/share/applications/` and `~/.local/share/icons/`
6. Register and start the systemd user service

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

Settings live in `~/.config/oled-guard/config.ini`. The installer creates it
from [`config.example.ini`](config.example.ini) with every option commented
out, so the built-in defaults apply. Uncomment a line to override it.
`update.sh` never overwrites this file.

```ini
[oled-guard]

# Idle time (seconds) before the screens go black
#idle_threshold_seconds = 300

# How often idle time is checked (seconds)
#poll_interval_seconds = 15

# Stay on while an app blocks idle (video playing). yes/no
#respect_idle_inhibitors = yes

# Comma-separated app ids to ignore (case-insensitive substring)
#ignore_inhibitors = steam, discord

# Blank anyway after this much idle despite inhibitors (0 = never)
#max_inhibited_idle_seconds = 14400
```

Invalid values are logged and replaced by their default, so a typo never stops
the service. Check the result in the startup line of the log:

```bash
journalctl --user -u oled-guard -n 5
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

### Blackout triggers during videos

Run `python3 ~/.config/oled-guard/watcher.py --check` while the video plays.
If it reports `blockers: none`, the player does not block session idle.
Check its settings (mpv: `stop-screensaver=yes`, the default).

### Blackout never triggers (inhibitor)

`journalctl --user -u oled-guard` logs `blackout skipped — …` with the app
holding the inhibitor; `watcher.py --check` shows it as well. Add a matching
part of its app id to `ignore_inhibitors` in `config.ini`.

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
2. Copy updated scripts to `~/.config/oled-guard/` (your `config.ini` is kept;
   it is only created if missing)
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

This removes `~/.config/oled-guard/` including `config.ini` — back it up first
if you want to keep your settings.

---

## Contributing

PRs welcome. Especially interested in:
- Compatibility reports for non-GNOME compositors
- `wlr-layer-shell` native Wayland fullscreen (no Xwayland needed)
- Alternative idle detection for niche setups

---

## License

MIT — see [LICENSE](LICENSE).
