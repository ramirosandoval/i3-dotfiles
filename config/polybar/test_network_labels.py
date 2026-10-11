"""Prevent untrusted Wi-Fi names from becoming Polybar action markup."""
import configparser
from pathlib import Path
import unittest


class NetworkLabelTests(unittest.TestCase):
    def test_wifi_labels_are_static(self):
        config = configparser.ConfigParser(interpolation=None)
        config.read(Path(__file__).with_name('config.ini'), encoding='utf-8')
        expected = '%{A1:x-terminal-emulator -e nmtui connect:}%{A}'
        for state in ('connected', 'disconnected'):
            with self.subTest(state=state):
                label = config['module/wifi'][f'label-{state}']
                self.assertNotRegex(label.lower(), r'%(?:essid|ssid)(?::[^%]*)?%')
                self.assertEqual(label, expected)


if __name__ == '__main__':
    unittest.main()
