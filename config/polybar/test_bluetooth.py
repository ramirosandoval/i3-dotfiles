import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).with_name('bluetooth.py')
DEVICES = '''Device CA:DC:EE:E1:6C:28 716
\x1b[0;92mNEW\x1b[0m Device 66:FB:79:C1:66:87 66-FB-79-C1-66-87
'''

class BluetoothTest(unittest.TestCase):
    def load(self):
        spec = importlib.util.spec_from_file_location('bluetooth_menu', SCRIPT)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    def test_parses_devices_and_detects_unnamed(self):
        m = self.load()
        found = m.parse_devices(m.ANSI.sub('', DEVICES))
        self.assertEqual([d['name'] for d in found], ['716', '66-FB-79-C1-66-87'])
        self.assertEqual([m.is_mac_name(d) for d in found], [False, True])

    def test_status_shows_connected_device(self):
        m = self.load()
        with patch.object(m, 'powered', return_value=True), patch.object(m, 'devices', return_value=[{'mac': 'AA', 'name': 'Auriculares'}]):
            self.assertIn('Auriculares', m.render())

    def test_cancel_does_nothing(self):
        m = self.load()
        with patch.object(m, 'powered', return_value=True), patch.object(m, 'devices', return_value=[]), patch.object(m, 'choose', return_value=None), patch.object(m, 'ctl') as ctl:
            m.main()
        ctl.assert_not_called()

if __name__ == '__main__':
    unittest.main()
