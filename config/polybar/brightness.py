#!/usr/bin/env python3
"""Software dimming for the selected X11 display; no extra dependencies."""
import fcntl
import os
from pathlib import Path
import re
import subprocess
import sys

def display_output(text):
    override = os.environ.get('BRIGHTNESS_OUTPUT')
    outputs = re.findall(r'^(\S+) connected([^\n]*)', text, re.M)
    if override:
        if override not in [name for name, details in outputs]:
            raise ValueError(f'{override} is not connected')
        return override
    active = [(name, details) for name, details in outputs if re.search(r'\d+x\d+\+\d+\+\d+', details)]
    if not active:
        raise ValueError('No active display')
    return next((name for name, details in active if 'primary' in details), active[0][0])


def read_brightness(text, output):
    section = re.search(r'^' + re.escape(output) + r' connected[^\n]*\n((?:[ \t].*\n)*)', text, re.M)
    if not section:
        raise ValueError(f'{output} is not connected')
    match = re.search(r'Brightness:\s*([0-9.]+)', section[1])
    if not match:
        raise ValueError('Display brightness unavailable')
    return round(float(match[1]) * 100)


def target(current, action):
    return {'up': min(100, current + 5), 'down': max(20, current - 5), 'reset': 100}[action]


def main():
    action = sys.argv[1] if len(sys.argv) == 2 else 'show'
    if action == '--self-test':
        sample = 'HDMI-A-0 connected primary 1920x1080\n\tBrightness: 0.65\nDP-0 disconnected\n\tBrightness: 1.0\n'
        assert read_brightness(sample, 'HDMI-A-0') == 65
        assert target(65, 'up') == 70 and target(65, 'down') == 60
        assert target(20, 'down') == 20 and target(100, 'up') == 100
        assert target(20, 'reset') == 100
        try:
            read_brightness('HDMI-A-0 disconnected\n', 'HDMI-A-0')
        except ValueError:
            pass
        else:
            raise AssertionError('Disconnected display accepted')
        print('PASS: reading, steps, bounds, reset and disconnected display')
        return
    if action not in ('show', 'up', 'down', 'reset'):
        raise ValueError('Expected show, up, down or reset')
    lock = Path(os.environ.get('XDG_RUNTIME_DIR', str(Path.home() / '.cache'))) / 'polybar-brightness.lock'
    with lock.open('w') as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        display = subprocess.check_output(['xrandr', '--verbose'], text=True)
        output = display_output(display)
        current = read_brightness(display, output)
        if action != 'show':
            subprocess.run(['xrandr', '--output', output, '--brightness', f'{target(current, action) / 100:.2f}'], check=True)
        else:
            print(f'{current}% SW')


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        print(error, file=sys.stderr)
        sys.exit(1)
