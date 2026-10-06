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

if __name__ == '__main__':
    unittest.main()
