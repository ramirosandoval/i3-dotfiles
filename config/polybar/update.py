#!/usr/bin/env python3
"""Actualizador a demanda (Python estándar, sin sondeo ni servicio).

Uso: python3 ~/.config/polybar/update.py [--check]
--check hace un fetch real y devuelve JSON: current/available/error, pending,
sha y head. Nunca abre diálogos ni aplica cambios; códigos de salida 0/1.

Producción exige el origin HTTPS exacto y main limpia, incluidos archivos no
seguidos. Confirmar en Rofi autoriza ejecutar el instalador del repositorio
confiable en el SHA mostrado: no se ejecuta código descargado antes de eso.

Política conservadora SIN overlays: se rechaza la instalación antes del merge
si hay destinos locales distintos o si el config remoto perdería el botón.
No se pisa la personalización de audio ni se añade el micrófono. Para habilitar
la aplicación se deben integrar manualmente esas diferencias y conservar el
módulo updates remoto; destinos enlazados al repo pueden avanzar normalmente.
El propio update.py solo puede ser sustituido si ya está enlazado al repo o si
el archivo entrante es idéntico. Si el remoto no lo incluye, solo se permite
conservar un updater local que no dependa del enlace al repositorio.

El instalador existente guarda archivos reemplazados en
~/.local/state/i3-dotfiles/backup-* y revierte enlaces si falla su validación.
El updater no hace reset automático si falla después del merge. Solo invoca
launch.sh de Polybar, nunca reinicia i3, sesión, PipeWire ni PulseAudio.
Los tests usan repositorios temporales bajo TMPDIR; nunca el instalador real.
"""
import os
from pathlib import Path
import subprocess
import contextlib
import fcntl


@contextlib.contextmanager
def update_lock(path):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd = os.open(path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'w') as stream:
        try:
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise UpdateError('Ya hay una consulta o actualización en curso.') from None
        yield

TRUSTED_ORIGIN = 'https://github.com/ramirosandoval/i3-dotfiles.git'
REPOSITORY = Path.home() / 'i3-dotfiles'


def git(repo, *args):
    env = dict(os.environ, GIT_TERMINAL_PROMPT='0', GIT_ASKPASS='/bin/false',
               SSH_ASKPASS='/bin/false', GCM_INTERACTIVE='Never', LC_ALL='C')
    return subprocess.check_output(
        ['git', '-c', 'credential.helper=', '-C', str(repo), *args],
        text=True, stderr=subprocess.PIPE, env=env, timeout=30).strip()


class UpdateError(RuntimeError):
    """Refusal with a user-facing Spanish explanation."""


def validate(repo, trusted):
    if git(repo, 'remote', 'get-url', '--all', 'origin').splitlines() != [trusted]:
        raise UpdateError('Origen no permitido: se exige el repositorio de confianza exacto.')
    if git(repo, 'rev-parse', '--abbrev-ref', 'HEAD') != 'main':
        raise UpdateError('Se requiere la rama main; no se cambia de rama automáticamente.')
    if git(repo, 'status', '--porcelain', '--untracked-files=all'):
        raise UpdateError('Hay cambios locales o archivos sin seguimiento. Guardalos antes de actualizar.')


def install_preflight(repo, sha, home):
    """No overlays: refuse to overwrite machine-specific config or lose the button."""
    import configparser
    entries = git(repo, 'ls-tree', '-r', '--name-only', sha, '--', 'config').splitlines()
    updater = 'config/polybar/update.py'
    active_updater = home / '.config/polybar/update.py'
    if (updater not in entries and active_updater.is_symlink()
            and active_updater.resolve() == (repo / updater).resolve()):
        raise UpdateError('La versión remota elimina update.py enlazado al repositorio. Aplicación bloqueada para no perder el botón; requiere integración manual.')
    for entry in entries:
        parts = Path(entry).parts
        if len(parts) != 3:
            continue
        dest = home / '.config' / Path(*parts[1:])
        if dest.is_symlink() and dest.resolve() == (repo / entry).resolve():
            continue
        if dest.exists() or dest.is_symlink():
            incoming = subprocess.check_output(['git', '-C', str(repo), 'show', sha + ':' + entry], timeout=30)
            if not dest.is_file() or dest.read_bytes() != incoming:
                raise UpdateError('Configuración local distinta: ' + str(dest) +
                                  '. No se sobrescribe ni se fusiona automáticamente. Integrá tus cambios manualmente antes de instalar.')
    parser = configparser.ConfigParser(interpolation=None, strict=True)
    try:
        parser.read_string(git(repo, 'show', sha + ':config/polybar/config.ini'))
        modules = ' '.join(parser.get('bar/main', 'modules-' + side, fallback='') for side in ('left', 'center', 'right')).split()
        retained = ('updates' in modules and parser.get('module/updates', 'click-left', fallback='') == 'python3 ~/.config/polybar/update.py')
    except (subprocess.SubprocessError, configparser.Error):
        retained = False
    if not retained:
        raise UpdateError('La versión remota no conserva el botón de actualización. Aplicación bloqueada para no perderlo; requiere integración manual.')


def apply_update(repo, report, confirmed, install, preflight, trusted=TRUSTED_ORIGIN):
    if not confirmed:
        return False
    validate(repo, trusted)
    if git(repo, 'rev-parse', 'HEAD') != report['head']:
        raise UpdateError('El repositorio cambió durante la confirmación. Volvé a consultar.')
    preflight()
    git(repo, 'merge', '--ff-only', '--no-edit', report['sha'])
    install()
    return True


def check(repo, trusted=TRUSTED_ORIGIN):
    validate(repo, trusted)
    git(repo, 'fetch', '--no-tags', '--no-recurse-submodules', 'origin', 'main')
    sha = git(repo, 'rev-parse', 'FETCH_HEAD')
    ahead = int(git(repo, 'rev-list', '--count', sha + '..HEAD'))
    if ahead:
        raise UpdateError('main tiene commits locales o divergió de origin/main. Se requiere revisión manual; no se hace reset ni rebase.')
    pending = int(git(repo, 'rev-list', '--count', 'HEAD..' + sha))
    return {'status': 'available' if pending else 'current', 'pending': pending,
            'sha': sha, 'head': git(repo, 'rev-parse', 'HEAD')}


def confirm(report):
    prompt = f"{report['pending']} cambio(s) pendientes · {report['sha'][:12]} · ejecutar instalador confiable"
    result = subprocess.run(
        ['rofi', '-dmenu', '-no-custom', '-no-markup-rows', '-no-sort',
         '-format', 'i', '-selected-row', '0', '-p', prompt],
        input='Cancelar\nActualizar repositorio de confianza\n', text=True,
        capture_output=True, timeout=300)
    return result.returncode == 0 and result.stdout.strip() == '1'


def install(repo):
    """Called only after approval and safety checks. No session/audio restart."""
    try:
        subprocess.run(['python3', str(repo / 'install.py')], cwd=repo,
                       check=True, capture_output=True, text=True, timeout=120)
        subprocess.run(['sh', str(repo / 'config/polybar/launch.sh')], cwd=repo,
                       check=True, capture_output=True, text=True, timeout=15)
    except (OSError, subprocess.SubprocessError) as error:
        raise UpdateError('La revisión Git ya avanzó, pero falló la instalación o la recarga de Polybar. Revisá manualmente; no se revierte Git automáticamente. Backups del instalador: ~/.local/state/i3-dotfiles/backup-*') from error


def inform(message):
    try:
        subprocess.run(['zenity', '--info', '--no-markup', '--title=Actualización de dotfiles',
                        '--width=600', '--text=' + message], timeout=300, check=False)
    except (OSError, subprocess.SubprocessError):
        print(message)


def main(argv=None, *, repo=REPOSITORY, trusted=TRUSTED_ORIGIN):
    import argparse
    import json
    parser = argparse.ArgumentParser(description='Consultar y actualizar dotfiles a demanda.')
    parser.add_argument('--check', action='store_true', help='Solo fetch y JSON; sin diálogos ni instalación.')
    args = parser.parse_args(argv)
    try:
        runtime = Path(os.environ.get('XDG_RUNTIME_DIR', str(Path.home() / '.cache')))
        with update_lock(runtime / 'polybar/dotfiles-update.lock'):
            report = check(repo, trusted)
            if args.check:
                print(json.dumps(report, ensure_ascii=False))
                return 0
            if report['status'] == 'current':
                inform('El repositorio ya está actualizado: main coincide con origin/main. No se modificó la configuración instalada.')
                return 0
            approved = confirm(report)
            applied = apply_update(repo, report, approved, lambda: install(repo),
                                   lambda: install_preflight(repo, report['sha'], Path.home()), trusted)
            if applied:
                inform('Actualización aplicada. Solo se recargó Polybar; no se reinició i3 ni el audio.\nBackups: ~/.local/state/i3-dotfiles/backup-*')
            return 0
    except (UpdateError, OSError, subprocess.SubprocessError) as error:
        message = str(error) if isinstance(error, UpdateError) else 'No se pudo completar la operación Git (red, credenciales, tiempo agotado o repositorio inválido). No se hizo reset ni rebase.'
        if args.check:
            print(json.dumps({'status': 'error', 'message': message}, ensure_ascii=False))
        else:
            inform(message)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
