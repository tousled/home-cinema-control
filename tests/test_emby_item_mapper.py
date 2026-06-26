import unittest

from home_cinema_control.media_servers.common.media_tracks import MediaTrackKind
from home_cinema_control.media_servers.emby.item_mapper import (
    media_server_item_playback_info_from_item,
    media_tracks_from_item,
)


class EmbyItemMapperTest(unittest.TestCase):
    def test_maps_item_playback_info_from_selected_media_source(self):
        info = media_server_item_playback_info_from_item(
            {
                "UserData": {
                    "PlaybackPositionTicks": "420000000",
                    "Played": False,
                    "PlayCount": 2,
                    "PlayedPercentage": 50.5,
                },
                "MediaSources": [
                    {"Id": "source-1", "Container": "mkv", "VideoType": "VideoFile"},
                ],
            },
            media_source_id="source-1",
        )

        self.assertEqual(420000000, info.saved_position_ticks)
        self.assertFalse(info.played)
        self.assertEqual(2, info.play_count)
        self.assertEqual(50.5, info.playback_percentage)
        self.assertEqual("mkv", info.media_source_container)
        self.assertEqual("VideoFile", info.media_source_video_type)

    def test_item_playback_info_falls_back_to_first_media_source_when_id_unmatched(self):
        info = media_server_item_playback_info_from_item(
            {"MediaSources": [{"Id": "other-source", "Container": "mp4"}]},
            media_source_id="missing-source",
        )

        self.assertEqual("mp4", info.media_source_container)

    def test_missing_item_response_maps_to_empty_playback_info(self):
        info = media_server_item_playback_info_from_item(
            None,
            media_source_id="source-1",
        )

        self.assertIsNone(info.saved_position_ticks)
        self.assertIsNone(info.played)
        self.assertIsNone(info.media_source_container)

    def test_maps_media_streams_to_tracks(self):
        tracks = media_tracks_from_item(
            {
                "MediaStreams": [
                    {"Type": "Video", "Index": 0},
                    {"Type": "Audio", "Index": "1"},
                    {"Type": "Subtitle", "Index": 3},
                    {"Type": "Data", "Index": "not-valid"},
                ]
            }
        )

        self.assertEqual(MediaTrackKind.VIDEO, tracks[0].kind)
        self.assertEqual(0, tracks[0].source_index)
        self.assertEqual(MediaTrackKind.AUDIO, tracks[1].kind)
        self.assertEqual(1, tracks[1].source_index)
        self.assertEqual(MediaTrackKind.SUBTITLE, tracks[2].kind)
        self.assertEqual(3, tracks[2].source_index)
        self.assertEqual(MediaTrackKind.OTHER, tracks[3].kind)
        self.assertEqual(-1, tracks[3].source_index)


if __name__ == "__main__":
    unittest.main()
