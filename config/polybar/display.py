#!/usr/bin/env python3
"""Select an advertised resolution; revert if not confirmed in 15 seconds."""
import fcntl
import os
from pathlib import Path
import re
import subprocess


def query():
    return subprocess.run(['xrandr', '--current'], env={**os.environ, 'LC_ALL': 'C'}, capture_output=True, text=True, timeout=5, check=True).stdout


def parse_outputs(text):
    outputs = []
    active = None
    for line in text.splitlines():
        if line and not line[0].isspace():
            active = None
            match = re.match(r'^(\S+) connected (?:primary )?(\d+x\d+)\+[-\d]+\+[-\d]+', line)
            if match:
                active = dict(name=match[1], current=match[2], rate=None, modes=[])
                outputs.append(active)
        elif active:
            match = re.match(r'^\s+(\d+x\d+)\s+(.+)$', line)
            if match:
                if match[1] not in active['modes']:
                    active['modes'].append(match[1])
                for rate in match[2].split():
                    if '*' in rate:
                        active['current'] = match[1]
                        active['rate'] = rate.rstrip('*+')
    return [o for o in outputs if o['rate'] and o['modes']]


def choose(labels, title):
    result = subprocess.run(['rofi', '-dmenu', '-i', '-no-custom', '-format', 'i', '-p', title], input='\n'.join(labels), capture_output=True, text=True, check=False)
    if result.returncode == 0 and result.stdout.strip().isdigit():
        index = int(result.stdout.strip())
        if 0 <= index < len(labels):
            return index
    return None


def apply(output, mode, rate=None):
    cmd = ['xrandr', '--output', output, '--mode', mode]
    if rate:
        cmd += ['--rate', rate]
    subprocess.run(cmd, capture_output=True, text=True, timeout=8, check=True)


def confirm():
    try:
        result = subprocess.run(['rofi', '-dmenu', '-no-custom', '-format', 'i', '-p', 'Resolución', '-mesg', '¿Conservar el cambio? Se revierte en 15 segundos.'], input='Conservar\nRevertir', capture_output=True, text=True, timeout=15, check=False)
        return result.returncode == 0 and result.stdout.strip() == '0'
    except subprocess.TimeoutExpired:
        return False


def main():
    outputs = parse_outputs(query())
    if not outputs:
        return
    index = choose([o['name'] for o in outputs], 'Pantalla') if len(outputs) > 1 else 0
    if index is None:
        return
    output = outputs[index]
    labels = [mode + (' · actual' if mode == output['current'] else '') for mode in output['modes']]
    index = choose(labels, 'Resolución')
    if index is None or output['modes'][index] == output['current']:
        return
    # Refresh after the menu so unplugging a display cannot apply stale modes.
    fresh = next((o for o in parse_outputs(query()) if o['name'] == output['name']), None)
    if not fresh or output['modes'][index] not in fresh['modes']:
        return
    try:
        apply(output['name'], output['modes'][index])
        keep = confirm()
    except (OSError, subprocess.SubprocessError):
        apply(output['name'], fresh['current'], fresh['rate'])
        raise
    if not keep:
        apply(output['name'], fresh['current'], fresh['rate'])


if __name__ == '__main__':
    # Prevent overlapping menus and conflicting rollback timers.
    lock_dir = Path(os.environ.get('XDG_RUNTIME_DIR', Path.home() / '.cache'))
    lock_dir.mkdir(parents=True, exist_ok=True)
    with (lock_dir / 'polybar-display.lock').open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise SystemExit(0)
        try:
            main()
        except (OSError, subprocess.SubprocessError) as error:
            print(f'No se pudo cambiar la resolución: {error}', file=__import__('sys').stderr)
