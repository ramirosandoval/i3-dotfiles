#!/usr/bin/env python3
"""Show mute state of the real default microphone, never a sink monitor."""
import subprocess


def icon(description, volume):
    if 'media.class = "Audio/Source"' not in description or not volume.startswith('Volume: '):
        return '%{F#8087a2} ?%{F-}'
    return '%{F#ed8796}%{F-}' if '[MUTED]' in volume else '%{F#a6da95}%{F-}'


def main():
    try:
        description = subprocess.check_output(['wpctl', 'inspect', '@DEFAULT_AUDIO_SOURCE@'], text=True, stderr=subprocess.DEVNULL, timeout=2)
        volume = subprocess.check_output(['wpctl', 'get-volume', '@DEFAULT_AUDIO_SOURCE@'], text=True, stderr=subprocess.DEVNULL, timeout=2)
    except (OSError, subprocess.SubprocessError):
        description, volume = '', ''
    print(icon(description, volume))


if __name__ == '__main__':
    main()
