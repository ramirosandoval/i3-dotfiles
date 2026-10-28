#!/usr/bin/env python3
"""Link the shared configuration, backing up existing files first."""
from pathlib import Path
import shutil
import subprocess
import tempfile

REPOSITORY = Path(__file__).resolve().parent


def install(home):
    config = home / '.config'
    backup_root = home / '.local/state/i3-dotfiles'
    backup_root.mkdir(parents=True, exist_ok=True)
    backup = Path(tempfile.mkdtemp(prefix='backup-', dir=backup_root))
    changes = []
    try:
        for source in sorted((REPOSITORY / 'config').glob('*/*')):
            if not source.is_file() or source.name.endswith('.pyc'):
                continue
            relative = source.relative_to(REPOSITORY / 'config')
            destination = config / relative
            if destination.is_symlink() and destination.resolve() == source:
                continue
            destination.parent.mkdir(parents=True, exist_ok=True)
            previous = None
            if destination.exists() or destination.is_symlink():
                previous = backup / relative
                previous.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(destination), str(previous))
            changes.append((destination, previous))
            destination.symlink_to(source)
        local = config / 'i3/local.conf'
        if not local.exists():
            local.touch()
        subprocess.run(['i3', '-C', '-c', str(config / 'i3/config')], check=True)
    except Exception:
        for destination, previous in reversed(changes):
            destination.unlink(missing_ok=True)
            if previous:
                shutil.move(str(previous), str(destination))
        raise
    print(f'Configuration linked. Backup: {backup}')
    print('Reload with Super+Shift+R inside your i3 session.')
    return backup


if __name__ == '__main__':
    required = ('i3', 'polybar', 'rofi', 'python3', 'ip', 'nmcli', 'xrandr', 'flock', 'wpctl', 'pavucontrol', 'nm-connection-editor', 'alacritty', 'nautilus', 'flameshot', 'zenity', 'feh', 'xss-lock', 'i3lock', 'dex', 'nm-applet', 'nmtui', 'gdbus', 'pw-play', 'bluetoothctl')
    missing = [command for command in required if not shutil.which(command)]
    if missing:
        raise SystemExit('Install missing commands first: ' + ', '.join(missing))
    install(Path.home())
