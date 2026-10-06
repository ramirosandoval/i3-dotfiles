#!/usr/bin/env python3
"""Check menu routing without opening apps or changing the desktop."""
import os
from pathlib import Path
import subprocess
import tempfile

script = Path(__file__).with_name('settings.sh')
with tempfile.TemporaryDirectory(dir=os.environ.get('TMPDIR')) as directory:
    root = Path(directory)
    stub = root / 'stub'
    stub.write_text('''#!/bin/sh
if [ "${0##*/}" = rofi ]; then
    [ -n "$CHOICE" ] || exit 1
    printf '%s\\n' "$CHOICE"
else
    printf '%s' "${0##*/}" > "$RESULT"
    [ "$#" -eq 0 ] || printf ' %s' "$@" >> "$RESULT"
fi
''')
    stub.chmod(0o700)
    for command in ('rofi', 'pavucontrol', 'nm-connection-editor', 'nautilus', 'flameshot', 'i3-msg', 'loginctl', 'xdg-open'):
        (root / command).symlink_to(stub)
    cases = {
        'Audio y micrófono': 'pavucontrol',
        'Conexiones de red': 'nm-connection-editor',
        'Explorar archivos': 'nautilus --new-window',
        'Captura de pantalla': 'flameshot gui',
        'Ventanas sin separación': 'i3-msg gaps inner current set 0; gaps outer current set 0',
        'Ventanas con separación': 'i3-msg gaps inner current set 10; gaps outer current set 4',
        'Bloquear pantalla': 'loginctl lock-session',
        'Editar configuración de Polybar': f'xdg-open {Path.home()}/.config/polybar/config.ini',
        '': '',
        'unknown': '',
    }
    result = root / 'result'
    for choice, expected in cases.items():
        result.unlink(missing_ok=True)
        env = dict(os.environ, PATH=f'{root}:{os.environ["PATH"]}', CHOICE=choice, RESULT=str(result))
        subprocess.run(['sh', str(script)], env=env, check=True)
        assert (result.read_text() if result.exists() else '') == expected, choice
print('PASS: 8 menu routes, cancellation and unknown selection')
