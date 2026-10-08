import importlib.util
from pathlib import Path
import unittest

SCRIPT = Path(__file__).with_name('pomodoro.py')

class PomodoroTest(unittest.TestCase):
    def test_start_pause_resume_reset(self):
        self.assertTrue(SCRIPT.exists(), 'Pomodoro is not implemented')
        spec = importlib.util.spec_from_file_location('pomodoro', SCRIPT)
        p = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(p)
        s = p.initial()
        self.assertEqual(s['remaining'], 1500)
        s, _ = p.step(s, 'toggle', 100)
        self.assertTrue(s['running'])
        s, _ = p.step(s, 'toggle', 110)
        self.assertFalse(s['running'])
        self.assertEqual(s['remaining'], 1490)
        s, _ = p.step(s, 'toggle', 300)
        s, _ = p.step(s, 'status', 310)
        self.assertEqual(s['remaining'], 1480)
        s, _ = p.step(s, 'reset', 311)
        self.assertEqual(s, p.initial())

    def test_cycles_and_single_completion_event(self):
        spec = importlib.util.spec_from_file_location('pomodoro', SCRIPT)
        p = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(p)
        s = p.initial()
        now = 0
        for cycle in range(1, 5):
            s, _ = p.step(s, 'toggle', now)
            now += 1500
            s, event = p.step(s, 'status', now)
            self.assertIsNotNone(event)
            self.assertEqual(s['phase'], 'break')
            self.assertFalse(s['running'])
            self.assertEqual(s['remaining'], 900 if cycle == 4 else 300)
            self.assertEqual(s['completed'], cycle)
            s, event = p.step(s, 'status', now + 1)
            self.assertIsNone(event)
            s, _ = p.step(s, 'toggle', now + 1)
            now += 1 + s['remaining']
            s, event = p.step(s, 'status', now)
            self.assertEqual(s['phase'], 'work')
            self.assertEqual(s['remaining'], 1500)
            self.assertFalse(s['running'])
            self.assertIsNotNone(event)

    def test_cli_persists_state_and_renders_without_words(self):
        import os
        import subprocess
        import tempfile
        import json
        with tempfile.TemporaryDirectory() as tmp:
            env = dict(os.environ, POMODORO_STATE_DIR=tmp)
            def run(action):
                return subprocess.check_output(['python3', str(SCRIPT), action], env=env, text=True).strip()
            self.assertRegex(run('status'), r'^%\{F#[0-9a-f]+\}\uf017%\{F-\} 25:00$')
            run('toggle')
            state = json.loads((Path(tmp) / 'state.json').read_text())
            self.assertTrue(state['running'])
            run('toggle')
            self.assertFalse(json.loads((Path(tmp) / 'state.json').read_text())['running'])
            run('reset')
            self.assertRegex(run('status'), r'^%\{F#[0-9a-f]+\}\uf017%\{F-\} 25:00$')

    def test_manual_phase_selection_overrides_old_timer_without_counting_it(self):
        spec = importlib.util.spec_from_file_location('pomodoro', SCRIPT)
        p = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(p)
        old = dict(phase='break', remaining=10, running=True, stamp=1, completed=2)
        for action, phase, duration in [('work', 'work', 1500), ('short-break', 'break', 300), ('long-break', 'break', 900)]:
            with self.subTest(action=action):
                state, event = p.step(old, action, 99999)
                self.assertEqual(state['phase'], phase)
                self.assertEqual(state['remaining'], duration)
                self.assertFalse(state['running'])
                self.assertEqual(state['completed'], 2)
                self.assertIsNone(event)
        fresh, _ = p.step(p.initial(), 'short-break', 100)
        self.assertEqual(fresh['phase'], 'break')
        self.assertEqual(fresh['remaining'], 300)

    def test_menu_choices_and_cancellation(self):
        from unittest.mock import patch
        import subprocess
        spec = importlib.util.spec_from_file_location('pomodoro', SCRIPT)
        p = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(p)
        self.assertTrue(hasattr(p, 'select_action'), 'Phase selection menu missing')
        for choice, expected in [('Tarea · 25 minutos', 'work'), ('Descanso · 5 minutos', 'short-break'), ('Descanso largo · 15 minutos', 'long-break'), ('Reiniciar ciclo', 'reset')]:
            with patch('subprocess.run', return_value=subprocess.CompletedProcess([], 0, choice + '\n')) as runner:
                self.assertEqual(p.select_action(), expected)
                self.assertIn('-no-custom', runner.call_args.args[0])
        with patch('subprocess.run', return_value=subprocess.CompletedProcess([], 1, '')):
            self.assertIsNone(p.select_action())
        with patch('subprocess.run', return_value=subprocess.CompletedProcess([], 0, 'arbitrary command')):
            self.assertIsNone(p.select_action())

    def test_cli_manual_phase_selection_persists(self):
        import os
        import subprocess
        import tempfile
        import json
        with tempfile.TemporaryDirectory() as tmp:
            env = dict(os.environ, POMODORO_STATE_DIR=tmp)
            for action, phase, remaining in [('short-break', 'break', 300), ('work', 'work', 1500), ('long-break', 'break', 900)]:
                subprocess.check_output(['python3', str(SCRIPT), action], env=env, text=True)
                state = json.loads((Path(tmp) / 'state.json').read_text())
                self.assertEqual(state['phase'], phase)
                self.assertEqual(state['remaining'], remaining)
                self.assertFalse(state['running'])

if __name__ == '__main__':
    unittest.main()
