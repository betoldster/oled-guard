#!/usr/bin/env python3
"""
blackout.py — OLED Guard
Creates a fullscreen black window on every connected monitor.
Exits immediately on left mouse click, ESC, or any keypress.

Usage:
    python3 blackout.py
"""

import tkinter as tk
import subprocess
import sys
import re


def _monitors_via_mutter_dbus() -> list[dict]:
    """Detect monitors via GNOME Mutter DisplayConfig DBus (GNOME Wayland)."""
    try:
        import dbus
        bus = dbus.SessionBus()
        proxy = bus.get_object(
            "org.gnome.Mutter.DisplayConfig",
            "/org/gnome/Mutter/DisplayConfig"
        )
        iface = dbus.Interface(proxy, "org.gnome.Mutter.DisplayConfig")
        serial, monitors, logical_monitors, _props = iface.GetCurrentState()

        # Build map: (connector, serial) -> (width, height) for the current mode
        mode_dims: dict[tuple, tuple] = {}
        for connector, _vendor, _product, mon_serial, modes, _mon_props in monitors:
            for _mode_id, w, h, _refresh, _pref_scale, _supp_scales, mode_props in modes:
                if mode_props.get("is-current", False):
                    mode_dims[(str(connector), str(mon_serial))] = (int(w), int(h))
                    break

        result = []
        for x, y, _scale, _transform, _primary, mon_specs, _lm_props in logical_monitors:
            for connector, mon_serial, _mode_id in mon_specs:
                dims = mode_dims.get((str(connector), str(mon_serial)))
                if dims:
                    result.append({"w": dims[0], "h": dims[1], "x": int(x), "y": int(y)})
                    break
        return result
    except Exception:
        return []


def _monitors_via_wlr_randr() -> list[dict]:
    """Detect monitors via wlr-randr (wlroots compositors: sway, Hyprland, etc.)."""
    try:
        result = subprocess.run(
            ["wlr-randr"], capture_output=True, text=True, timeout=3
        )
        if result.returncode != 0:
            return []

        monitors = []
        # Each monitor block starts with a non-indented line
        blocks = re.split(r"\n(?=\S)", result.stdout.strip())
        for block in blocks:
            size_m = re.search(r"(\d+)x(\d+)\s+px", block)
            pos_m = re.search(r"Position:\s+(\d+),(\d+)", block)
            enabled_m = re.search(r"Enabled:\s+(yes|no)", block, re.IGNORECASE)
            if not (size_m and pos_m):
                continue
            if enabled_m and enabled_m.group(1).lower() == "no":
                continue
            monitors.append({
                "w": int(size_m.group(1)), "h": int(size_m.group(2)),
                "x": int(pos_m.group(1)), "y": int(pos_m.group(2)),
            })
        return monitors
    except Exception:
        return []


def _monitors_via_kscreen() -> list[dict]:
    """Detect monitors via kscreen-doctor (KDE Plasma Wayland)."""
    try:
        result = subprocess.run(
            ["kscreen-doctor", "-o"], capture_output=True, text=True, timeout=3
        )
        if result.returncode != 0:
            return []

        monitors = []
        # Each output block starts with "Output:"
        blocks = re.split(r"\n(?=Output:)", result.stdout.strip())
        for block in blocks:
            if not re.search(r"Enabled:\s+true", block, re.IGNORECASE):
                continue
            size_m = re.search(r"Size:\s+(\d+)x(\d+)", block)
            pos_m = re.search(r"Pos:\s+(\d+),(\d+)", block)
            if size_m and pos_m:
                monitors.append({
                    "w": int(size_m.group(1)), "h": int(size_m.group(2)),
                    "x": int(pos_m.group(1)), "y": int(pos_m.group(2)),
                })
        return monitors
    except Exception:
        return []


def _monitors_via_xrandr() -> list[dict]:
    """Detect monitors via xrandr (X11 / Xwayland fallback)."""
    try:
        result = subprocess.run(
            ["xrandr", "--query"], capture_output=True, text=True, timeout=3
        )
        if result.returncode == 0:
            pattern = re.compile(
                r"connected\s+(?:primary\s+)?(\d+)x(\d+)\+(\d+)\+(\d+)"
            )
            monitors = [
                {"w": int(w), "h": int(h), "x": int(x), "y": int(y)}
                for w, h, x, y in pattern.findall(result.stdout)
            ]
            if monitors:
                return monitors
    except Exception:
        pass
    return []


def get_monitor_geometries() -> list[dict]:
    """
    Detect all connected monitors and their geometries.
    Tries Wayland-native methods first (GNOME Mutter DBus, wlr-randr, kscreen-doctor),
    then xrandr for X11/Xwayland, then falls back to the full virtual desktop.
    """
    for fn in (
        _monitors_via_mutter_dbus,
        _monitors_via_wlr_randr,
        _monitors_via_kscreen,
        _monitors_via_xrandr,
    ):
        monitors = fn()
        if monitors:
            return monitors

    # Final fallback: cover the full virtual desktop
    root = tk.Tk()
    w, h = root.winfo_screenwidth(), root.winfo_screenheight()
    root.destroy()
    return [{"w": w, "h": h, "x": 0, "y": 0}]


def dismiss(root: tk.Tk, _event=None):
    """Destroy all windows and exit immediately."""
    try:
        root.destroy()
    except Exception:
        pass
    sys.exit(0)


def main():
    monitors = get_monitor_geometries()

    root = tk.Tk()

    # Bind dismiss to root
    for seq in ("<Button-1>", "<Escape>", "<KeyPress>"):
        root.bind(seq, lambda e, r=root: dismiss(r, e))

    all_windows = [root]

    # Build one window per monitor
    for i, mon in enumerate(monitors):
        win = root if i == 0 else tk.Toplevel(root)
        win.configure(bg="black", cursor="none")
        win.overrideredirect(True)
        win.attributes("-fullscreen", True)
        win.attributes("-topmost", True)
        win.geometry(f"{mon['w']}x{mon['h']}+{mon['x']}+{mon['y']}")

        if i > 0:
            for seq in ("<Button-1>", "<Escape>", "<KeyPress>"):
                win.bind(seq, lambda e, r=root: dismiss(r, e))
            all_windows.append(win)

    root.focus_force()
    root.grab_set()
    root.mainloop()


if __name__ == "__main__":
    main()
