#!/usr/bin/env python3
"""Run with python3 check.py; no desktop changes."""
import importlib.util
import os
from pathlib import Path
import subprocess
import tempfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent


def load(name, path):
    specification = importlib.util.spec_from_file_location(name, path)
    assert specification is not None and specification.loader is not None
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


brightness = load('brightness', ROOT / 'config/polybar/brightness.py')
with patch.dict(os.environ, {}, clear=True):
    desktop = 'HDMI-A-0 connected primary 1920x1080+0+0\n\tBrightness: 0.65\n'
    laptop = 'eDP-1 connected primary 1920x1080+0+0\n\tBrightness: 1.0\n'
    assert brightness.display_output(desktop) == 'HDMI-A-0'
    assert brightness.display_output(laptop) == 'eDP-1'
    assert brightness.read_brightness(laptop, 'eDP-1') == 100
    with patch.dict(os.environ, {'BRIGHTNESS_OUTPUT': 'missing'}):
        try:
            brightness.display_output(laptop)
        except ValueError:
            pass
        else:
            raise AssertionError('Invalid monitor override accepted')
subprocess.run(['python3', str(ROOT / 'config/polybar/brightness.py'), '--self-test'], check=True)
subprocess.run(['python3', str(ROOT / 'config/polybar/check.py')], check=True)
launch = (ROOT / 'config/polybar/launch.sh').read_text()
network_parser = launch.split("python3 -c '", 1)[1].split("')", 1)[0]
for inventory, expected in (
    ('tun0:tun:connected\nenp5s0:ethernet:connected\nwlan0:wifi:disconnected\n', 'enp5s0'),
    ('enp1s0:ethernet:disconnected\nwlan0:wifi:connected\n', 'wlan0'),
    ('wlan0:wifi:disconnected\nveth0:ethernet:unmanaged\n', 'wlan0'),
    ('lo:loopback:connected\n', ''),
):
    detected = subprocess.check_output(['python3', '-c', network_parser], input=inventory, text=True).strip()
    assert detected == expected, (inventory, detected)
for script in (ROOT / 'config/polybar').glob('*.sh'):
    subprocess.run(['sh', '-n', str(script)], check=True)

installer = load('installer', ROOT / 'install.py')
with tempfile.TemporaryDirectory(dir=os.environ.get('TMPDIR')) as directory:
    home = Path(directory)
    existing = home / '.config/i3/config'
    existing.parent.mkdir(parents=True)
    existing.write_text('old configuration')
    local = existing.with_name('local.conf')
    local.write_text('# Keep this machine-specific setting\n')
    with patch.dict(os.environ, {'HOME': str(home)}):
        backup = installer.install(home)
        assert existing.is_symlink()
        assert (backup / 'i3/config').read_text() == 'old configuration'
        assert local.read_text() == '# Keep this machine-specific setting\n'
        installer.install(home)
        assert existing.resolve() == ROOT / 'config/i3/config'
        subprocess.run(['rofi', '-dump-config'], check=True, stdout=subprocess.DEVNULL)
with tempfile.TemporaryDirectory(dir=os.environ.get('TMPDIR')) as directory:
    home = Path(directory)
    existing = home / '.config/i3/config'
    existing.parent.mkdir(parents=True)
    existing.write_text('original')
    with patch.object(installer.subprocess, 'run', side_effect=subprocess.CalledProcessError(1, 'i3')):
        try:
            installer.install(home)
        except subprocess.CalledProcessError:
            pass
        else:
            raise AssertionError('Validation failure was ignored')
    assert not existing.is_symlink() and existing.read_text() == 'original'
print('PASS: monitor detection, menu, shell syntax, real i3/Rofi validation, backups, repeat install and rollback')
