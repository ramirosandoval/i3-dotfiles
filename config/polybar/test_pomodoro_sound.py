import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).with_name('pomodoro.py')


class PomodoroSoundTest(unittest.TestCase):
    def test_work_completion_plays_once(self):
        self.check_completion('work', expected_plays=1)

    def test_break_completion_plays_once(self):
        self.check_completion('break', expected_plays=1)

    def check_completion(self, phase, expected_plays):
        spec = importlib.util.spec_from_file_location('pomodoro_sound', SCRIPT)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as tmp:
            state = dict(phase=phase, remaining=1, running=True, stamp=100, completed=0)
            (Path(tmp) / 'state.json').write_text(json.dumps(state))
            with patch.dict(os.environ, {'POMODORO_STATE_DIR': tmp}), \
                    patch('sys.argv', [str(SCRIPT), 'status']), \
                    patch('time.time', return_value=102), \
                    patch('subprocess.run', return_value=subprocess.CompletedProcess([], 0)) as runner, \
                    contextlib.redirect_stdout(io.StringIO()):
                module.main()
                module.main()
            plays = [c for c in runner.call_args_list if c.args[0][0] == 'pw-play']
            self.assertEqual(len(plays), expected_plays)
            if plays:
                self.assertIn('--volume=0.5', plays[0].args[0])
                self.assertTrue(Path(plays[0].args[0][-1]).is_file())
                self.assertLessEqual(plays[0].kwargs['timeout'], 5)
            saved = json.loads((Path(tmp) / 'state.json').read_text())
            self.assertFalse(saved['running'])
            self.assertEqual(saved['phase'], 'break' if phase == 'work' else 'work')


if __name__ == '__main__':
    unittest.main()
