#!/usr/bin/env python3
"""Clickable Polybar pomodoro; state survives bar restarts."""

def initial():
    return dict(phase='work', remaining=1500, running=False, stamp=0, completed=0)


def step(state, action, now):
    state = dict(state)
    durations = {'work': 1500, 'short-break': 300, 'long-break': 900}
    if action in durations:
        state.update(phase='work' if action == 'work' else 'break',
                     remaining=durations[action], running=False, stamp=now)
        return state, None
    if state['running']:
        state['remaining'] = max(0, state['remaining'] - max(0, now - state['stamp']))
        state['stamp'] = now
    if action == 'reset':
        return initial(), None
    event = None
    if state['running'] and state['remaining'] <= 0:
        if state['phase'] == 'work':
            state['completed'] += 1
            state['phase'] = 'break'
            state['remaining'] = 900 if state['completed'] % 4 == 0 else 300
            event = 'Sesión terminada. Descanso de %s minutos.' % (state['remaining'] // 60)
        else:
            state['phase'] = 'work'
            state['remaining'] = 1500
            event = 'Descanso terminado. Listo para concentrarte.'
        state['running'] = False
    if action == 'toggle':
        state['running'] = not state['running']
        state['stamp'] = now
    return state, event


def select_action():
    import subprocess
    choices = {
        'Tarea · 25 minutos': 'work',
        'Descanso · 5 minutos': 'short-break',
        'Descanso largo · 15 minutos': 'long-break',
        'Reiniciar ciclo': 'reset',
    }
    try:
        result = subprocess.run(
            ['rofi', '-dmenu', '-i', '-no-custom', '-p', 'Pomodoro',
             '-mesg', 'Elegí una etapa. Clic izquierdo en el reloj para iniciar.'],
            input='\n'.join(choices) + '\n', text=True, capture_output=True,
            check=False,
        )
    except OSError:
        return None
    return choices.get(result.stdout.strip()) if result.returncode == 0 else None


def main():
    import fcntl
    import json
    import math
    import os
    from pathlib import Path
    import subprocess
    import sys
    import time

    action = sys.argv[1] if len(sys.argv) > 1 else 'status'
    if action == 'menu':
        action = select_action()
        if action is None:
            return
    if action not in ('status', 'toggle', 'reset', 'work', 'short-break', 'long-break'):
        raise SystemExit('Use: status, toggle, reset, menu, work, short-break, long-break')
    directory = Path(os.environ.get('POMODORO_STATE_DIR', str(Path.home() / '.local/state/polybar-pomodoro')))
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / 'state.json'
    with (directory / 'state.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        try:
            state = json.loads(path.read_text()) if path.exists() else initial()
            state, event = step(state, action, time.time())
        except (ValueError, KeyError, TypeError):
            state, event = initial(), None
        temp = directory / 'state.json.tmp'
        temp.write_text(json.dumps(state))
        temp.replace(path)
        if event:
            try:
                subprocess.run([
                    'gdbus', 'call', '--session',
                    '--dest', 'org.freedesktop.Notifications',
                    '--object-path', '/org/freedesktop/Notifications',
                    '--method', 'org.freedesktop.Notifications.Notify',
                    'Pomodoro', '0', 'alarm-symbolic', 'Pomodoro', event,
                    '[]', '{}', '10000',
                ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=3, check=False)
            except (OSError, subprocess.TimeoutExpired):
                pass
    if event and state['phase'] == 'break':
        try:
            subprocess.run([
                'pw-play', '--volume=0.5',
                '/usr/share/sounds/freedesktop/stereo/complete.oga',
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                timeout=3, check=False)
        except (OSError, subprocess.TimeoutExpired):
            pass
    seconds = max(0, math.ceil(state['remaining']))
    color = '#a6da95' if state['phase'] == 'break' else '#8aadf4'
    print(f'%{{F{color}}}\uf017%{{F-}} {seconds // 60:02}:{seconds % 60:02}')


if __name__ == '__main__':
    main()
