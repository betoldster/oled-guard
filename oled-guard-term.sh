#!/usr/bin/env bash
# oled-guard-term.sh — run a command in the user's terminal emulator

CMD="$1"
if [ -z "$CMD" ]; then
    echo "Usage: oled-guard-term.sh 'command'" >&2
    exit 1
fi

if command -v gnome-terminal &>/dev/null; then
    exec gnome-terminal -- sh -c "$CMD"
elif command -v kgx &>/dev/null; then
    exec kgx -- sh -c "$CMD"
elif command -v konsole &>/dev/null; then
    exec konsole -e sh -c "$CMD"
elif command -v xfce4-terminal &>/dev/null; then
    exec xfce4-terminal -e "sh -c \"$CMD\""
elif command -v mate-terminal &>/dev/null; then
    exec mate-terminal -- sh -c "$CMD"
elif command -v xterm &>/dev/null; then
    exec xterm -e sh -c "$CMD"
else
    notify-send "OLED Guard" "No terminal emulator found. Install gnome-terminal, konsole, or xterm." 2>/dev/null
    exit 1
fi
