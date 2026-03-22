#!/usr/bin/env python3
"""
watcher.py — OLED Guard idle watcher daemon
Monitors system idle time via DBus and launches blackout.py
when the user has been idle for IDLE_THRESHOLD_SECONDS.

Designed to run as a systemd user service.
Consumes negligible CPU — sleeps between polls.

Dependencies:
    sudo apt install python3-dbus
    # or for Homebrew Python: pip install dbus-python
"""

import os
import sys
import time
import signal
import logging
import subprocess

# ── Configuration ──────────────────────────────────────────────────────────────

# How long (seconds) of idle before blackout triggers
IDLE_THRESHOLD_SECONDS = 5 * 60  # 5 minutes

# How often to check idle time (seconds)
POLL_INTERVAL_SECONDS = 15

# Paths
SCRIPT_DIR    = os.path.dirname(os.path.abspath(__file__))
BLACKOUT_SCRIPT = os.path.join(SCRIPT_DIR, "blackout.py")
PYTHON        = sys.executable

# ── Logging ────────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [oled-guard] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("oled-guard")

# ── Idle time via DBus ─────────────────────────────────────────────────────────

def get_idle_seconds() -> float:
    """
    Query idle time in seconds from the Wayland session via DBus.
    Tries multiple interfaces for GNOME, KDE, and generic compositors.
    Returns 0.0 on failure.
    """
    try:
        import dbus
    except ImportError:
        log.warning("dbus-python not available — idle detection disabled.")
        return 0.0

    interfaces = [
        # GNOME / PikaOS (Mutter)
        ("org.gnome.Mutter.IdleMonitor",
         "/org/gnome/Mutter/IdleMonitor/Core",
         "org.gnome.Mutter.IdleMonitor",
         "GetIdletime"),
        # Generic / KDE Plasma
        ("org.freedesktop.ScreenSaver",
         "/org/freedesktop/ScreenSaver",
         "org.freedesktop.ScreenSaver",
         "GetSessionIdleTime"),
        # KDE fallback
        ("org.kde.screensaver",
         "/ScreenSaver",
         "org.freedesktop.ScreenSaver",
         "GetSessionIdleTime"),
    ]

    try:
        bus = dbus.SessionBus()
        for service, path, iface_name, method in interfaces:
            try:
                obj   = bus.get_object(service, path)
                iface = dbus.Interface(obj, iface_name)
                ms    = getattr(iface, method)()
                return int(ms) / 1000.0
            except dbus.DBusException:
                continue

        log.warning("No idle-time DBus interface found — returning 0.")
        return 0.0

    except Exception as e:
        log.error(f"DBus error: {e}")
        return 0.0

# ── Blackout process ───────────────────────────────────────────────────────────

_proc: subprocess.Popen | None = None


def is_running() -> bool:
    global _proc
    if _proc is None:
        return False
    if _proc.poll() is not None:
        _proc = None
        return False
    return True


def launch_blackout():
    global _proc
    if is_running():
        return
    log.info("Idle threshold reached — launching blackout.")
    try:
        _proc = subprocess.Popen(
            [PYTHON, BLACKOUT_SCRIPT],
            env=os.environ.copy(),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            close_fds=True,
        )
    except Exception as e:
        log.error(f"Failed to launch blackout: {e}")

# ── Signal handling ─────────────────────────────────────────────────────────────

def _shutdown(signum, frame):
    log.info(f"Signal {signum} received — shutting down.")
    if is_running() and _proc:
        _proc.terminate()
    sys.exit(0)

signal.signal(signal.SIGTERM, _shutdown)
signal.signal(signal.SIGINT,  _shutdown)

# ── Main loop ───────────────────────────────────────────────────────────────────

def main():
    try:
        import dbus  # noqa: F401
    except ImportError:
        log.error(
            "dbus-python is not installed — cannot detect idle time.\n"
            "  Fix: sudo apt install python3-dbus\n"
            "  Then: systemctl --user restart oled-guard"
        )
        sys.exit(1)

    log.info(
        f"Started. Threshold: {IDLE_THRESHOLD_SECONDS}s, "
        f"poll every {POLL_INTERVAL_SECONDS}s."
    )
    while True:
        idle = get_idle_seconds()
        if idle >= IDLE_THRESHOLD_SECONDS:
            launch_blackout()
        time.sleep(POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
