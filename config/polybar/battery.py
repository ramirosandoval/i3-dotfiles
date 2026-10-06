#!/usr/bin/env python3
"""Battery percentage and charging/connected state for Polybar."""
from pathlib import Path


def render(root=Path('/sys/class/power_supply')):
    supplies = list(root.glob('*'))
    batteries = [p for p in supplies if (p / 'type').read_text().strip() == 'Battery']
    if not batteries:
        return ''
    battery = batteries[0]
    capacity = int((battery / 'capacity').read_text().strip())
    status = (battery / 'status').read_text().strip()
    connected = any(
        (p / 'type').read_text().strip() != 'Battery'
        and (p / 'online').exists()
        and (p / 'online').read_text().strip() == '1'
        for p in supplies
    )
    if status == 'Charging':
        icon, color = '', '#a6da95'
    elif connected:
        icon, color = '', '#a6da95'
    else:
        icon, color = '', '#ed8796' if capacity <= 15 else '#8aadf4'
    return f'%{{F{color}}}{icon}%{{F-}} {capacity}%'


if __name__ == '__main__':
    try:
        print(render())
    except (OSError, ValueError):
        print(' ?%')
