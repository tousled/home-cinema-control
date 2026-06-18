import unittest

from home_cinema_control.media_servers.emby.track_mapping import (
    player_audio_to_source_track_id,
    player_subtitle_to_source_track_id,
    source_audio_to_player_index,
    source_subtitle_to_player_index,
)


MEDIA_STREAMS = [
    {"Type": "Video", "Index": 0},
    {"Type": "Audio", "Index": 1},
    {"Type": "Audio", "Index": 2},
    {"Type": "Subtitle", "Index": 3},
    {"Type": "Subtitle", "Index": 4},
    {"Type": "Subtitle", "Index": 5},
]


class EmbyTrackMappingTest(unittest.TestCase):
    def test_maps_source_audio_index_to_player_menu_index(self):
        self.assertEqual(2, source_audio_to_player_index(MEDIA_STREAMS, 2))

    def test_unknown_source_audio_defaults_to_first_player_audio(self):
        self.assertEqual(1, source_audio_to_player_index(MEDIA_STREAMS, 99))

    def test_maps_source_subtitle_index_to_player_menu_index(self):
        self.assertEqual(3, source_subtitle_to_player_index(MEDIA_STREAMS, 5))

    def test_disabled_source_subtitle_maps_to_player_off(self):
        self.assertEqual(0, source_subtitle_to_player_index(MEDIA_STREAMS, -1))

    def test_maps_player_audio_index_to_source_track_id(self):
        self.assertEqual(1, player_audio_to_source_track_id(MEDIA_STREAMS, 1))
        self.assertEqual(2, player_audio_to_source_track_id(MEDIA_STREAMS, 2))

    def test_unknown_player_audio_index_returns_none(self):
        self.assertIsNone(player_audio_to_source_track_id(MEDIA_STREAMS, 3))

    def test_maps_player_subtitle_index_to_source_track_id(self):
        self.assertEqual(3, player_subtitle_to_source_track_id(MEDIA_STREAMS, 1))
        self.assertEqual(5, player_subtitle_to_source_track_id(MEDIA_STREAMS, 3))

    def test_player_subtitle_off_maps_to_disabled_source_subtitle(self):
        self.assertEqual(-1, player_subtitle_to_source_track_id(MEDIA_STREAMS, 0))

    def test_unknown_player_subtitle_index_returns_none(self):
        self.assertIsNone(player_subtitle_to_source_track_id(MEDIA_STREAMS, 4))


class EmbyTrackMappingEdgeCasesTest(unittest.TestCase):
    def test_empty_streams_returns_default_audio_player_index(self):
        self.assertEqual(1, source_audio_to_player_index([], 1))

    def test_empty_streams_returns_default_subtitle_player_index(self):
        self.assertEqual(0, source_subtitle_to_player_index([], 3))

    def test_empty_streams_returns_none_for_player_audio(self):
        self.assertIsNone(player_audio_to_source_track_id([], 1))

    def test_empty_streams_returns_none_for_player_subtitle(self):
        self.assertIsNone(player_subtitle_to_source_track_id([], 1))

    def test_streams_missing_type_key_are_skipped(self):
        streams = [{"Index": 1}, {"Index": 2}]
        self.assertIsNone(player_audio_to_source_track_id(streams, 1))
        self.assertEqual(1, source_audio_to_player_index(streams, 1))


if __name__ == "__main__":
    unittest.main()
