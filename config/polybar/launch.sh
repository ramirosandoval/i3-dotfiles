#!/bin/sh
set -eu
command -v polybar >/dev/null
# Local overrides are user-owned and are never tracked in this repository.
if [ -f "$HOME/.config/polybar/local.env" ]; then
    . "$HOME/.config/polybar/local.env"
fi
if [ -z "${NETWORK_INTERFACE:-}" ]; then
    NETWORK_INTERFACE=$(nmcli -t -f DEVICE,TYPE,STATE device | python3 -c 'import sys
interfaces = [line.strip().split(":") for line in sys.stdin]
physical = [fields for fields in interfaces if len(fields) == 3 and fields[1] in ("ethernet", "wifi") and fields[2] != "unmanaged"]
connected = [fields for fields in physical if fields[2] == "connected"]
print((connected or physical or [[""]])[0][0])')
fi
export NETWORK_INTERFACE BRIGHTNESS_OUTPUT
runtime="${XDG_RUNTIME_DIR:-$HOME/.cache}/polybar"
mkdir -p "$runtime"
exec 9>"$runtime/launch.lock"
flock -x 9
if [ -f "$runtime/main.pid" ]; then
    pid=$(cat "$runtime/main.pid")
    if [ -r "/proc/$pid/comm" ] && [ "$(cat "/proc/$pid/comm")" = polybar ]; then
        kill "$pid" 2>/dev/null || true
        timeout 3 tail --pid="$pid" -f /dev/null || true
    fi
fi
polybar --reload --config="$HOME/.config/polybar/config.ini" main >"$runtime/main.log" 2>&1 9>&- &
echo "$!" >"$runtime/main.pid"
