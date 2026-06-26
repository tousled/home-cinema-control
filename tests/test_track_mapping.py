import unittest

from home_cinema_control.media_servers.common.media_tracks import (
    MediaTrack,
    MediaTrackKind,
)
from home_cinema_control.media_servers.common.track_mapping import (
    player_audio_to_source_track_id,
    player_subtitle_to_source_track_id,
    source_audio_to_player_index,
    source_subtitle_to_player_index,
)


TRACKS = [
    MediaTrack(kind=MediaTrackKind.VIDEO, source_index=0),
    MediaTrack(kind=MediaTrackKind.AUDIO, source_index=1),
    MediaTrack(kind=MediaTrackKind.AUDIO, source_index=2),
    MediaTrack(kind=MediaTrackKind.SUBTITLE, source_index=3),
    MediaTrack(kind=MediaTrackKind.SUBTITLE, source_index=4),
    MediaTrack(kind=MediaTrackKind.SUBTITLE, source_index=5),
]

NON_CONTIGUOUS_TRACKS = [
    MediaTrack(kind=MediaTrackKind.VIDEO, source_index=0),
    MediaTrack(kind=MediaTrackKind.AUDIO, source_index=1),
    MediaTrack(kind=MediaTrackKind.SUBTITLE, source_index=2),
    MediaTrack(kind=MediaTrackKind.AUDIO, source_index=4),
    MediaTrack(kind=MediaTrackKind.SUBTITLE, source_index=6),
]


class TrackMappingTest(unittest.TestCase):
    def test_maps_source_audio_index_to_player_menu_index(self):
        self.assertEqual(2, source_audio_to_player_index(TRACKS, 2))

    def test_unknown_source_audio_defaults_to_first_player_audio(self):
        self.assertEqual(1, source_audio_to_player_index(TRACKS, 99))

    def test_maps_source_subtitle_index_to_player_menu_index(self):
        self.assertEqual(3, source_subtitle_to_player_index(TRACKS, 5))

    def test_disabled_source_subtitle_maps_to_player_off(self):
        self.assertEqual(0, source_subtitle_to_player_index(TRACKS, -1))

    def test_unknown_source_subtitle_uses_disabled_default(self):
        self.assertEqual(0, source_subtitle_to_player_index(TRACKS, 99))

    def test_maps_player_audio_index_to_source_track_id(self):
        self.assertEqual(1, player_audio_to_source_track_id(TRACKS, 1))
        self.assertEqual(2, player_audio_to_source_track_id(TRACKS, 2))

    def test_unknown_player_audio_index_returns_none(self):
        self.assertIsNone(player_audio_to_source_track_id(TRACKS, 3))

    def test_maps_player_subtitle_index_to_source_track_id(self):
        self.assertEqual(3, player_subtitle_to_source_track_id(TRACKS, 1))
        self.assertEqual(5, player_subtitle_to_source_track_id(TRACKS, 3))

    def test_player_subtitle_off_maps_to_disabled_source_subtitle(self):
        self.assertEqual(-1, player_subtitle_to_source_track_id(TRACKS, 0))

    def test_unknown_player_subtitle_index_returns_none(self):
        self.assertIsNone(player_subtitle_to_source_track_id(TRACKS, 4))

    def test_mapping_is_positional_not_equal_to_raw_source_index(self):
        # Source Index values need not be contiguous or match the player's
        # 1-based menu position; mapping is positional among same-type streams.
        self.assertEqual(
            2, source_audio_to_player_index(NON_CONTIGUOUS_TRACKS, 4)
        )
        self.assertEqual(
            2, source_subtitle_to_player_index(NON_CONTIGUOUS_TRACKS, 6)
        )
        self.assertEqual(
            4, player_audio_to_source_track_id(NON_CONTIGUOUS_TRACKS, 2)
        )
        self.assertEqual(
            6, player_subtitle_to_source_track_id(NON_CONTIGUOUS_TRACKS, 2)
        )


class TrackMappingEdgeCasesTest(unittest.TestCase):
    def test_empty_streams_returns_default_audio_player_index(self):
        self.assertEqual(1, source_audio_to_player_index([], 1))

    def test_empty_streams_returns_default_subtitle_player_index(self):
        self.assertEqual(0, source_subtitle_to_player_index([], 3))

    def test_empty_streams_returns_none_for_player_audio(self):
        self.assertIsNone(player_audio_to_source_track_id([], 1))

    def test_empty_streams_returns_none_for_player_subtitle(self):
        self.assertIsNone(player_subtitle_to_source_track_id([], 1))

    def test_other_tracks_are_skipped(self):
        tracks = [
            MediaTrack(kind=MediaTrackKind.OTHER, source_index=1),
            MediaTrack(kind=MediaTrackKind.OTHER, source_index=2),
        ]
        self.assertIsNone(player_audio_to_source_track_id(tracks, 1))
        self.assertEqual(1, source_audio_to_player_index(tracks, 1))


if __name__ == "__main__":
    unittest.main()
