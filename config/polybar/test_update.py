"""Isolated Git integration tests; never install into the real home."""
import importlib.util
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
import contextlib
import io
import json
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location('dotfiles_update', Path(__file__).with_name('update.py'))
up = importlib.util.module_from_spec(SPEC)
if SPEC.loader and Path(SPEC.origin).exists():
    SPEC.loader.exec_module(up)


def git(repo, *args):
    return subprocess.check_output(['git', '-C', str(repo), *args], text=True, stderr=subprocess.PIPE).strip()


class GitUpdates(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=os.environ.get('TMPDIR'))
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.remote = self.root / 'remote.git'
        self.seed = self.root / 'seed'
        self.repo = self.root / 'client'
        subprocess.run(['git', 'init', '--bare', '--initial-branch=main', str(self.remote)], check=True, capture_output=True)
        subprocess.run(['git', 'clone', str(self.remote), str(self.seed)], check=True, capture_output=True)
        git(self.seed, 'config', 'user.name', 'Test')
        git(self.seed, 'config', 'user.email', 'test@example.invalid')
        self.commit(self.seed, 'initial')
        git(self.seed, 'push', 'origin', 'main')
        subprocess.run(['git', 'clone', str(self.remote), str(self.repo)], check=True, capture_output=True)
        git(self.repo, 'config', 'user.name', 'Test')
        git(self.repo, 'config', 'user.email', 'test@example.invalid')

    def commit(self, repo, text):
        (repo / 'file').write_text(text)
        git(repo, 'add', 'file')
        git(repo, 'commit', '-m', text)
        return git(repo, 'rev-parse', 'HEAD')

    def pending(self):
        sha = self.commit(self.seed, 'next')
        git(self.seed, 'push', 'origin', 'main')
        return sha

    def check(self):
        return up.check(self.repo, str(self.remote))

    def test_current_fetch_reports_zero_without_changing_head(self):
        before = git(self.repo, 'rev-parse', 'HEAD')
        report = self.check()
        self.assertEqual(report['status'], 'current')
        self.assertEqual(report['pending'], 0)
        self.assertEqual(report['sha'], before)
        self.assertEqual(git(self.repo, 'rev-parse', 'HEAD'), before)

    def test_pending_counts_exact_fetched_commit(self):
        sha = self.pending()
        report = self.check()
        self.assertEqual(report['status'], 'available')
        self.assertEqual(report['pending'], 1)
        self.assertEqual(report['sha'], sha)

    def test_unsafe_repositories_refused_before_fetch(self):
        scenarios = ('origin', 'branch', 'untracked', 'modified', 'ahead', 'diverged')
        for scenario in scenarios:
            with self.subTest(scenario=scenario):
                if scenario == 'origin':
                    git(self.repo, 'remote', 'set-url', 'origin', str(self.seed))
                elif scenario == 'branch':
                    git(self.repo, 'checkout', '-b', 'other')
                elif scenario == 'untracked':
                    (self.repo / 'untracked').write_text('keep')
                elif scenario == 'modified':
                    (self.repo / 'file').write_text('keep')
                elif scenario in ('ahead', 'diverged'):
                    self.commit(self.repo, 'local')
                    if scenario == 'diverged':
                        self.pending()
                with self.assertRaises(up.UpdateError):
                    self.check()
                git(self.repo, 'remote', 'set-url', 'origin', str(self.remote))
                git(self.repo, 'checkout', 'main')
                git(self.repo, 'reset', '--hard', git(self.seed, 'rev-parse', 'HEAD~1') if scenario == 'diverged' else git(self.seed, 'rev-parse', 'HEAD'))
                (self.repo / 'untracked').unlink(missing_ok=True)

    def test_cancel_does_not_merge_or_run_installer(self):
        self.pending()
        report = self.check()
        calls = []
        self.assertFalse(up.apply_update(self.repo, report, False, lambda: calls.append('install'), lambda: calls.append('preflight'), str(self.remote)))
        self.assertEqual(git(self.repo, 'rev-parse', 'HEAD'), report['head'])
        self.assertEqual(calls, [])

    def test_confirmed_ff_merges_exact_shown_sha_not_new_remote_tip(self):
        sha = self.pending()
        report = self.check()
        self.commit(self.seed, 'later')
        git(self.seed, 'push', 'origin', 'main')
        calls = []
        self.assertTrue(up.apply_update(self.repo, report, True, lambda: calls.append(git(self.repo, 'rev-parse', 'HEAD')), lambda: None, str(self.remote)))
        self.assertEqual(git(self.repo, 'rev-parse', 'HEAD'), sha)
        self.assertEqual(calls, [sha])

    def test_changes_after_confirmation_refuse_before_merge(self):
        self.pending()
        report = self.check()
        (self.repo / 'new-local').write_text('keep')
        with self.assertRaises(up.UpdateError):
            up.apply_update(self.repo, report, True, lambda: self.fail('installed'), lambda: None, str(self.remote))
        self.assertEqual(git(self.repo, 'rev-parse', 'HEAD'), report['head'])

    def test_preflight_refusal_does_not_merge(self):
        self.pending()
        report = self.check()
        def refuse():
            raise up.UpdateError('local changes')
        with self.assertRaises(up.UpdateError):
            up.apply_update(self.repo, report, True, lambda: self.fail('installed'), refuse, str(self.remote))
        self.assertEqual(git(self.repo, 'rev-parse', 'HEAD'), report['head'])

    def policy_tree(self, text=None):
        folder = self.seed / 'config/polybar'
        folder.mkdir(parents=True)
        (folder / 'config.ini').write_text(text or '[bar/main]\nmodules-right = updates\n[module/updates]\nclick-left = python3 ~/.config/polybar/update.py\n')
        git(self.seed, 'add', '.')
        git(self.seed, 'commit', '-m', 'config')
        git(self.seed, 'push', 'origin', 'main')
        return self.check()

    def test_policy_refuses_local_overrides_without_modifying_them(self):
        report = self.policy_tree()
        home = self.root / 'home'
        active = home / '.config/polybar/config.ini'
        active.parent.mkdir(parents=True)
        active.write_text('custom audio and no microphone')
        with self.assertRaisesRegex(up.UpdateError, 'local'):
            up.install_preflight(self.repo, report['sha'], home)
        self.assertEqual(active.read_text(), 'custom audio and no microphone')

    def test_policy_refuses_remote_without_update_button(self):
        report = self.policy_tree('[bar/main]\nmodules-right = audio\n')
        with self.assertRaisesRegex(up.UpdateError, 'botón'):
            up.install_preflight(self.repo, report['sha'], self.root / 'home')

    def test_policy_allows_identical_files_with_retained_button(self):
        report = self.policy_tree()
        home = self.root / 'home'
        active = home / '.config/polybar/config.ini'
        active.parent.mkdir(parents=True)
        active.write_bytes((self.seed / 'config/polybar/config.ini').read_bytes())
        up.install_preflight(self.repo, report['sha'], home)

    def test_policy_refuses_deleted_repo_linked_updater_before_merge(self):
        self.policy_tree()
        updater = 'config/polybar/update.py'
        (self.seed / updater).write_text('# updater\n')
        git(self.seed, 'add', updater)
        git(self.seed, 'commit', '-m', 'add updater')
        git(self.seed, 'push', 'origin', 'main')
        report = self.check()
        git(self.repo, 'merge', '--ff-only', report['sha'])
        home = self.root / 'home'
        active = home / '.config/polybar/update.py'
        active.parent.mkdir(parents=True)
        active.symlink_to(self.repo / updater)
        git(self.seed, 'rm', updater)
        git(self.seed, 'commit', '-m', 'delete updater but retain button')
        git(self.seed, 'push', 'origin', 'main')
        report = self.check()
        with self.assertRaisesRegex(up.UpdateError, 'update.py'):
            up.apply_update(self.repo, report, True, lambda: self.fail('installed'),
                            lambda: up.install_preflight(self.repo, report['sha'], home), str(self.remote))
        self.assertEqual(git(self.repo, 'rev-parse', 'HEAD'), report['head'])
        self.assertTrue(active.is_file())

    def test_policy_allows_standalone_updater_when_incoming_omits_it(self):
        report = self.policy_tree()
        home = self.root / 'home'
        active = home / '.config/polybar/update.py'
        active.parent.mkdir(parents=True)
        active.write_text('# standalone updater\n')
        up.install_preflight(self.repo, report['sha'], home)
        self.assertEqual(active.read_text(), '# standalone updater\n')

    def test_check_cli_json_fetches_without_dialog_or_apply(self):
        self.pending()
        out = io.StringIO()
        with contextlib.redirect_stdout(out), patch.object(up, 'confirm', side_effect=AssertionError('dialog'), create=True), patch.object(up, 'install', side_effect=AssertionError('install'), create=True), patch.dict(os.environ, {'XDG_RUNTIME_DIR': str(self.root)}):
            self.assertEqual(up.main(['--check'], repo=self.repo, trusted=str(self.remote)), 0)
        self.assertEqual(json.loads(out.getvalue())['pending'], 1)
        self.assertEqual(git(self.repo, 'rev-parse', 'HEAD'), git(self.seed, 'rev-parse', 'HEAD~1'))

    def test_lock_refuses_second_click_and_releases_after_exit(self):
        path = self.root / 'update.lock'
        with up.update_lock(path):
            with self.assertRaisesRegex(up.UpdateError, 'curso'):
                with up.update_lock(path):
                    self.fail('lock acquired twice')
        with up.update_lock(path):
            pass

    def test_check_cli_errors_are_json_without_dialogs(self):
        (self.repo / 'untracked').write_text('keep')
        out = io.StringIO()
        with contextlib.redirect_stdout(out), patch.dict(os.environ, {'XDG_RUNTIME_DIR': str(self.root)}):
            self.assertEqual(up.main(['--check'], repo=self.repo, trusted=str(self.remote)), 1)
        self.assertEqual(json.loads(out.getvalue())['status'], 'error')
        self.assertIn('local', json.loads(out.getvalue())['message'])

    def test_rofi_confirmation_has_fixed_no_custom_plain_labels(self):
        report = {'pending': 2, 'sha': 'a' * 40}
        with patch.object(up.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, '1\n', '')) as run:
            self.assertTrue(up.confirm(report))
        command = run.call_args.args[0]
        self.assertIn('-no-custom', command)
        self.assertIn('-no-markup-rows', command)
        self.assertNotIn('-mesg', command)
        self.assertEqual(run.call_args.kwargs['input'], 'Cancelar\nActualizar repositorio de confianza\n')
        with patch.object(up.subprocess, 'run', return_value=subprocess.CompletedProcess([], 1, '', '')):
            self.assertFalse(up.confirm(report))

    def test_install_runs_fixture_installer_then_only_bar_launcher(self):
        # Harmless fixture programs, not the live installer or launch script.
        (self.repo / 'install.py').write_text("from pathlib import Path\np=Path('events'); p.write_text('install\\n')\n")
        launch = self.repo / 'config/polybar/launch.sh'
        launch.parent.mkdir(parents=True)
        launch.write_text("#!/bin/sh\nprintf 'bar\\n' >> events\n")
        up.install(self.repo)
        self.assertEqual((self.repo / 'events').read_text(), 'install\nbar\n')

    def test_default_current_shows_spanish_message_without_confirmation(self):
        with patch.object(up, 'inform', create=True) as inform, patch.object(up, 'confirm', side_effect=AssertionError('confirmation')), patch.dict(os.environ, {'XDG_RUNTIME_DIR': str(self.root)}):
            self.assertEqual(up.main([], repo=self.repo, trusted=str(self.remote)), 0)
        self.assertIn('actualizado', inform.call_args.args[0])

    def test_default_cancel_leaves_head_and_installed_config_unchanged(self):
        self.pending()
        before = git(self.repo, 'rev-parse', 'HEAD')
        with patch.object(up, 'confirm', return_value=False), patch.object(up, 'install', create=True, side_effect=AssertionError('install')), patch.dict(os.environ, {'XDG_RUNTIME_DIR': str(self.root)}):
            self.assertEqual(up.main([], repo=self.repo, trusted=str(self.remote)), 0)
        self.assertEqual(git(self.repo, 'rev-parse', 'HEAD'), before)

    def test_detached_head_has_clear_main_refusal(self):
        git(self.repo, 'checkout', '--detach')
        with self.assertRaisesRegex(up.UpdateError, 'main'):
            self.check()

    def test_fetch_is_bounded_noninteractive_without_submodule_recursion(self):
        actual = up.subprocess.check_output
        calls = []
        def observe(command, **kwargs):
            if 'fetch' in command:
                calls.append((command, kwargs))
            return actual(command, **kwargs)
        with patch.object(up.subprocess, 'check_output', side_effect=observe):
            self.check()
        command, options = calls[0]
        self.assertIn('--no-recurse-submodules', command)
        self.assertEqual(options['timeout'], 30)
        self.assertEqual(options['env']['GIT_TERMINAL_PROMPT'], '0')
        self.assertEqual(options['env']['GIT_ASKPASS'], '/bin/false')
        self.assertIn('credential.helper=', command)

    def test_information_dialog_explicitly_disables_markup(self):
        with patch.object(up.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0)) as run:
            up.inform('Mensaje <local>')
        self.assertIn('--no-markup', run.call_args.args[0])
        self.assertIn('--text=Mensaje <local>', run.call_args.args[0])

    def test_default_approved_refusal_keeps_head_and_shows_reason(self):
        self.pending()
        before = git(self.repo, 'rev-parse', 'HEAD')
        with patch.object(up, 'confirm', return_value=True), patch.object(up, 'inform') as inform, patch.object(up, 'install', side_effect=AssertionError('install')), patch.object(up.Path, 'home', return_value=self.root / 'home'), patch.dict(os.environ, {'XDG_RUNTIME_DIR': str(self.root)}):
            self.assertEqual(up.main([], repo=self.repo, trusted=str(self.remote)), 1)
        self.assertIn('botón', inform.call_args.args[0])
        self.assertEqual(git(self.repo, 'rev-parse', 'HEAD'), before)


if __name__ == '__main__':
    unittest.main()
