import importlib.util
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).with_name('display.py')
SAMPLE = '''Screen 0: current 1920 x 1080
eDP-1 connected primary 1920x1080+0+0 (normal)
   1920x1080 60.06*+ 60.01
   1280x720 60.00 59.99
HDMI-1 disconnected (normal)
'''

PORTRAIT = '''Screen 0: current 1080 x 1920
eDP-1 connected primary 1080x1920+0+0 left (normal left inverted right)
   1920x1080 60.06*+ 60.01
   1280x720 60.00 59.99
'''

class DisplayTest(unittest.TestCase):
    def load(self):
        self.assertTrue(SCRIPT.exists(), 'Falta el selector de resoluciones')
        spec = importlib.util.spec_from_file_location('display_menu', SCRIPT)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    def test_lists_only_active_output_modes_and_marks_current(self):
        m = self.load()
        self.assertEqual(m.parse_outputs(SAMPLE), [{'name': 'eDP-1', 'current': '1920x1080', 'rate': '60.06', 'modes': ['1920x1080', '1280x720']}])

    def test_cancel_does_not_apply(self):
        m = self.load()
        with patch.object(m, 'query', return_value=SAMPLE), patch.object(m, 'choose', return_value=None), patch.object(m, 'apply') as apply:
            m.main()
        apply.assert_not_called()

    def test_apply_then_revert_unconfirmed_change(self):
        m = self.load()
        with patch.object(m, 'query', return_value=SAMPLE), patch.object(m, 'choose', return_value=1), patch.object(m, 'confirm', return_value=False), patch.object(m, 'apply') as apply:
            m.main()
        self.assertEqual(apply.call_args_list[0].args, ('eDP-1', '1280x720'))
        self.assertEqual(apply.call_args_list[1].args, ('eDP-1', '1920x1080', '60.06'))

    def test_portrait_rollback_uses_starred_mode_and_refresh(self):
        m = self.load()
        with patch.object(m, 'query', return_value=PORTRAIT), patch.object(m, 'choose', return_value=1), patch.object(m, 'confirm', return_value=False), patch.object(m, 'apply') as apply:
            m.main()
        self.assertEqual([call.args for call in apply.call_args_list], [
            ('eDP-1', '1280x720'),
            ('eDP-1', '1920x1080', '60.06'),
        ])

    def test_confirm_keeps_selected_mode(self):
        m = self.load()
        with patch.object(m, 'query', return_value=SAMPLE), patch.object(m, 'choose', return_value=1), patch.object(m, 'confirm', return_value=True), patch.object(m, 'apply') as apply:
            m.main()
        apply.assert_called_once_with('eDP-1', '1280x720')

if __name__ == '__main__':
    unittest.main()
