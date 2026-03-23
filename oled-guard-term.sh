#!/usr/bin/env bash
# oled-guard-term.sh — run a command in the user's terminal emulator

WAIT=false
if [ "$1" = "--wait" ]; then
    WAIT=true
    shift
fi

CMD="$1"
if [ -z "$CMD" ]; then
    echo "Usage: oled-guard-term.sh [--wait] 'command'" >&2
    exit 1
fi

if [ "$WAIT" = true ]; then
    CMD="$CMD; echo; echo 'Press Enter to close this window...'; read _"
fi

if command -v gnome-terminal &>/dev/null; then
    exec gnome-terminal -- bash -c "$CMD"
elif command -v kgx &>/dev/null; then
    exec kgx -- bash -c "$CMD"
elif command -v konsole &>/dev/null; then
    exec konsole -e bash -c "$CMD"
elif command -v xfce4-terminal &>/dev/null; then
    exec xfce4-terminal -e "bash -c \"$CMD\""
elif command -v mate-terminal &>/dev/null; then
    exec mate-terminal -- bash -c "$CMD"
elif command -v xterm &>/dev/null; then
    exec xterm -e bash -c "$CMD"
else
    notify-send "OLED Guard" "No terminal emulator found. Install gnome-terminal, konsole, or xterm." 2>/dev/null
    exit 1
fi
