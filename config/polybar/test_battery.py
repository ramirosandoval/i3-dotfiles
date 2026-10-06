import importlib.util
from pathlib import Path
import tempfile
import unittest

SCRIPT = Path(__file__).with_name('battery.py')

class BatteryTest(unittest.TestCase):
    def test_percentage_and_power_states(self):
        self.assertTrue(SCRIPT.exists(), 'Battery display script is missing')
        spec = importlib.util.spec_from_file_location('battery', SCRIPT)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bat = root / 'BAT1'
            ac = root / 'ACAD'
            bat.mkdir()
            ac.mkdir()
            (bat / 'type').write_text('Battery')
            (bat / 'capacity').write_text('87')
            (ac / 'type').write_text('Mains')
            for status, online, expected in [
                ('Discharging', '0', '87% · Batería'),
                ('Charging', '1', '87% · Cargando'),
                ('Not charging', '1', '87% · Conectada'),
                ('Full', '1', '87% · Completa'),
            ]:
                with self.subTest(status=status):
                    (bat / 'status').write_text(status)
                    (ac / 'online').write_text(online)
                    output = module.render(root)
                    self.assertRegex(output, r'^%\{F#[0-9a-f]+\}[\uf0e7\uf1e6\uf240]%\{F-\} 87%$')

if __name__ == '__main__':
    unittest.main()
