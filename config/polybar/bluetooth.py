#!/usr/bin/env python3
"""Bluetooth status for Polybar and a rofi menu to scan, pair, connect and forget devices."""
import fcntl
import os
from pathlib import Path
import re
import subprocess
import sys

ICON = '\uf293'
SCAN_SECONDS = 10
ANSI = re.compile(r'\x1b\[[0-9;]*m|\x01|\x02')


def ctl(*args, timeout=10):
    result = subprocess.run(['bluetoothctl', *args], env={**os.environ, 'LC_ALL': 'C'}, capture_output=True, text=True, timeout=timeout, check=False)
    return result.returncode, ANSI.sub('', result.stdout + result.stderr)


def powered():
    return 'Powered: yes' in ctl('show')[1]


def parse_devices(text):
    devices = []
    for line in text.splitlines():
        match = re.search(r'\bDevice ((?:[0-9A-F]{2}:){5}[0-9A-F]{2}) (.+)$', line.strip())
        if match:
            devices.append(dict(mac=match[1], name=match[2].strip()))
    return devices


def devices(kind=None):
    return parse_devices(ctl('devices', *([kind] if kind else []))[1])


def is_mac_name(device):
    # Devices without a real name are advertised as their address with dashes.
    return device['name'].replace('-', ':') == device['mac']


def render():
    if not powered():
        return f'%{{F#8087a2}}{ICON}%{{F-}}'
    connected = devices('Connected')
    if connected:
        name = connected[0]['name']
        name = name if len(name) <= 14 else name[:13] + '…'
        return f'%{{F#a6da95}}{ICON}%{{F-}} {name}'
    return f'%{{F#8aadf4}}{ICON}%{{F-}}'


def choose(labels, title, message=None):
    cmd = ['rofi', '-dmenu', '-i', '-no-custom', '-format', 'i', '-p', title]
    if message:
        cmd += ['-mesg', message]
    result = subprocess.run(cmd, input='\n'.join(labels), capture_output=True, text=True, check=False)
    if result.returncode == 0 and result.stdout.strip().isdigit():
        index = int(result.stdout.strip())
        if 0 <= index < len(labels):
            return index
    return None


def notify(message):
    subprocess.run(['rofi', '-e', message], check=False)


def scan():
    ctl('pairable', 'on')
    # Keep a message on screen while discovery runs; it closes on its own.
    waiting = subprocess.Popen(['rofi', '-e', f'Buscando dispositivos ({SCAN_SECONDS} s)…\nPoné el auricular en modo vinculación.'])
    try:
        ctl('--timeout', str(SCAN_SECONDS), 'scan', 'on', timeout=SCAN_SECONDS + 10)
    finally:
        waiting.terminate()
    paired = {d['mac'] for d in devices('Paired')}
    found = [d for d in devices() if d['mac'] not in paired]
    return sorted(found, key=lambda d: (is_mac_name(d), d['name'].lower()))


def pair(device):
    code, out = ctl('pair', device['mac'], timeout=40)
    if code != 0 and 'AlreadyExists' not in out:
        detail = next((l for l in out.splitlines() if 'Failed' in l or 'org.bluez.Error' in l), out.strip()[-200:])
        notify(f'No se pudo vincular {device["name"]}.\n{detail}')
        return False
    ctl('trust', device['mac'])
    return connect(device)


def connect(device):
    code, out = ctl('connect', device['mac'], timeout=30)
    if code != 0 or 'Connection successful' not in out:
        detail = next((l for l in out.splitlines() if 'Failed' in l or 'org.bluez.Error' in l), out.strip()[-200:])
        notify(f'No se pudo conectar {device["name"]}.\n{detail}')
        return False
    return True


def device_menu(device, connected):
    actions = ['Desconectar' if connected else 'Conectar', 'Olvidar dispositivo']
    index = choose(actions, device['name'])
    if index == 0:
        if connected:
            ctl('disconnect', device['mac'])
        else:
            connect(device)
    elif index == 1:
        ctl('remove', device['mac'])


def main():
    if not powered():
        if choose(['Encender Bluetooth'], 'Bluetooth') == 0:
            ctl('power', 'on')
        return
    connected = {d['mac'] for d in devices('Connected')}
    paired = devices('Paired')
    labels = ['Buscar y vincular dispositivo…']
    labels += [f'{d["name"]} · conectado' if d['mac'] in connected else d['name'] for d in paired]
    labels += ['Apagar Bluetooth']
    index = choose(labels, 'Bluetooth')
    if index is None:
        return
    if index == 0:
        found = scan()
        if not found:
            notify('No se encontraron dispositivos.\n¿Está el auricular en modo vinculación?')
            return
        index = choose([d['name'] for d in found], 'Vincular')
        if index is not None:
            pair(found[index])
    elif index == len(labels) - 1:
        ctl('power', 'off')
    else:
        device = paired[index - 1]
        device_menu(device, device['mac'] in connected)


if __name__ == '__main__':
    if sys.argv[1:] == ['status']:
        try:
            print(render())
        except (OSError, subprocess.SubprocessError):
            print(f'%{{F#8087a2}}{ICON}%{{F-}}')
        raise SystemExit(0)
    lock_dir = Path(os.environ.get('XDG_RUNTIME_DIR', Path.home() / '.cache'))
    lock_dir.mkdir(parents=True, exist_ok=True)
    with (lock_dir / 'polybar-bluetooth.lock').open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise SystemExit(0)
        try:
            main()
        except (OSError, subprocess.SubprocessError) as error:
            notify(f'Error de Bluetooth: {error}')
