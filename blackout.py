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


def get_monitor_geometries() -> list[dict]:
    """
    Detect all connected monitors and their geometries via xrandr.
    Falls back to full virtual desktop if xrandr is unavailable.
    """
    try:
        result = subprocess.run(
            ["xrandr", "--query"],
            capture_output=True, text=True, timeout=3
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

    # Fallback: cover the full virtual desktop
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
