import unittest
from microphone import icon


class MicrophoneIconTest(unittest.TestCase):
    def test_real_microphone_mute_states(self):
        source = 'media.class = "Audio/Source"'
        self.assertEqual(icon(source, 'Volume: 0.65 [MUTED]'), '%{F#ed8796}%{F-}')
        self.assertEqual(icon(source, 'Volume: 0.65'), '%{F#a6da95}%{F-}')

    def test_missing_source_or_dummy_output_is_unknown(self):
        self.assertEqual(icon('media.class = "Audio/Sink"', 'Volume: 1.00'), '%{F#8087a2} ?%{F-}')
        self.assertEqual(icon('', ''), '%{F#8087a2} ?%{F-}')
