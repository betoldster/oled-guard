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

# Skip the blackout while an app blocks session idle. Video players and
# browsers do this only while a video plays (Brave/Chromium "Video Wake Lock",
# Firefox, VLC, mpv, ...); audio-only playback does not. Idle time itself is
# raw keyboard/mouse idle, so a truly idle desktop still blanks.
RESPECT_IDLE_INHIBITORS = True

# Inhibitors to ignore, matched case-insensitively as substrings of the app id
# (see `watcher.py --check`), e.g. ["steam", "discord"]. Use this if an app
# blocks idle permanently. Wayland-protocol inhibitors all show up as "mutter"
# on GNOME, and KDE reports no app ids, so those cannot be filtered per app.
IGNORE_INHIBITORS: list[str] = []

# Safety cap: blank anyway after this much idle time, even while an inhibitor
# is active. Protects against a video left looping or a stuck inhibitor.
# 0 disables the cap.
MAX_INHIBITED_IDLE_SECONDS = 4 * 60 * 60  # 4 hours

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

# ── Idle inhibitor detection ───────────────────────────────────────────────────

# GsmInhibitorFlag: 8 = inhibit session idle (4 = suspend, e.g. "Playing audio")
_GSM_INHIBIT_IDLE = 8


def _gnome_session_inhibitors(bus) -> list[str] | None:
    """
    GNOME: gnome-session tracks idle inhibitors from its own API, the Inhibit
    portal and Mutter's Wayland idle-inhibit protocol (app id "mutter").
    Returns "app (reason)" per idle inhibitor, or None if gnome-session is absent.
    """
    import dbus
    try:
        sm = dbus.Interface(
            bus.get_object("org.gnome.SessionManager", "/org/gnome/SessionManager"),
            "org.gnome.SessionManager",
        )
        paths = sm.GetInhibitors()
    except dbus.DBusException:
        return None
    apps = []
    for path in paths:
        try:
            inh = dbus.Interface(
                bus.get_object("org.gnome.SessionManager", path),
                "org.gnome.SessionManager.Inhibitor",
            )
            if int(inh.GetFlags()) & _GSM_INHIBIT_IDLE:
                apps.append(f"{inh.GetAppId() or '?'} ({inh.GetReason() or 'no reason'})")
        except dbus.DBusException:
            continue
    return apps


def _kde_inhibitors(bus) -> list[str] | None:
    """
    KDE Plasma: PowerDevil collects org.freedesktop.ScreenSaver.Inhibit and
    portal inhibitions. Returns None if PowerDevil is absent.
    """
    import dbus
    try:
        pm = dbus.Interface(
            bus.get_object("org.freedesktop.PowerManagement",
                           "/org/freedesktop/PowerManagement/Inhibit"),
            "org.freedesktop.PowerManagement.Inhibit",
        )
        return ["PowerManagement inhibitor"] if pm.HasInhibit() else []
    except dbus.DBusException:
        return None


def _logind_idle_inhibitors() -> list[str]:
    """Any compositor: blocking 'idle' inhibitors registered with systemd-logind."""
    import dbus
    try:
        login1 = dbus.Interface(
            dbus.SystemBus().get_object("org.freedesktop.login1",
                                        "/org/freedesktop/login1"),
            "org.freedesktop.login1.Manager",
        )
        uid = os.getuid()
        return [
            f"{who} ({why})"
            for what, who, why, mode, inh_uid, _pid in login1.ListInhibitors()
            if "idle" in str(what).split(":") and mode == "block" and int(inh_uid) == uid
        ]
    except dbus.DBusException:
        return []


def _ignored(inhibitor: str) -> bool:
    name = inhibitor.lower()
    return any(pat.lower() in name for pat in IGNORE_INHIBITORS)


def get_blackout_blockers() -> list[str]:
    """
    Return the idle inhibitors that should prevent the blackout right now
    (empty list = nothing is blocking).
    """
    if not RESPECT_IDLE_INHIBITORS:
        return []
    try:
        import dbus
        bus = dbus.SessionBus()
    except Exception as e:
        log.error(f"DBus error: {e}")
        return []

    found: list[str] = []
    for probe in (_gnome_session_inhibitors, _kde_inhibitors):
        found += probe(bus) or []
    found += _logind_idle_inhibitors()
    return [i for i in found if not _ignored(i)]

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
        f"poll every {POLL_INTERVAL_SECONDS}s, "
        f"respect inhibitors: {RESPECT_IDLE_INHIBITORS}, "
        f"ignore: {IGNORE_INHIBITORS}, cap: {MAX_INHIBITED_IDLE_SECONDS}s."
    )
    last_blockers: list[str] = []
    while True:
        idle = get_idle_seconds()
        blockers: list[str] = []
        if idle >= IDLE_THRESHOLD_SECONDS and not is_running():
            capped = (MAX_INHIBITED_IDLE_SECONDS > 0
                      and idle >= IDLE_THRESHOLD_SECONDS + MAX_INHIBITED_IDLE_SECONDS)
            blockers = [] if capped else get_blackout_blockers()
            if blockers:
                if blockers != last_blockers:
                    log.info(f"Idle {int(idle)}s but blackout skipped — {'; '.join(blockers)}")
            else:
                if capped:
                    log.info("Cap reached — blanking despite active inhibitors.")
                launch_blackout()
        last_blockers = blockers
        time.sleep(POLL_INTERVAL_SECONDS)


def check():
    """One-shot diagnostic: print idle time and current blockers, then exit."""
    print(f"idle: {get_idle_seconds():.0f}s (threshold {IDLE_THRESHOLD_SECONDS}s)")
    blockers = get_blackout_blockers()
    print("blockers:", "; ".join(blockers) if blockers else "none")
    if IGNORE_INHIBITORS:
        print("ignoring:", ", ".join(IGNORE_INHIBITORS))


if __name__ == "__main__":
    if "--check" in sys.argv[1:]:
        check()
    else:
        main()
