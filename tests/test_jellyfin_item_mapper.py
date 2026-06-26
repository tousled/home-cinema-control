import unittest

from home_cinema_control.media_servers.common.media_tracks import MediaTrackKind
from home_cinema_control.media_servers.jellyfin.item_mapper import (
    media_server_item_playback_info_from_item,
    media_server_playback_source_from_item,
    media_tracks_from_item,
)
from home_cinema_control.playback.content_kind import MediaContentKind


class JellyfinItemMapperTest(unittest.TestCase):
    def test_maps_playback_source_from_selected_media_source(self):
        source = media_server_playback_source_from_item(
            {
                "Type": "Episode",
                "Name": "Pilot",
                "ProductionYear": 2025,
                "MediaSources": [
                    {
                        "Id": "source-1",
                        "Path": "/tv/pilot.mkv",
                        "Container": "mkv",
                        "RunTimeTicks": 12_000_000_000,
                    }
                ],
            },
            "source-1",
        )

        self.assertEqual("/tv/pilot.mkv", source.path)
        self.assertEqual("mkv", source.container)
        self.assertEqual(1200, source.duration_seconds)
        self.assertEqual(2025, source.production_year)
        self.assertEqual("Pilot", source.title)
        self.assertEqual(MediaContentKind.EPISODE, source.content_kind)

    def test_maps_item_playback_info_from_default_media_source(self):
        info = media_server_item_playback_info_from_item(
            {
                "UserData": {"PlaybackPositionTicks": 10},
                "MediaSources": [
                    {"Container": "mp4", "VideoType": "VideoFile"},
                ],
            },
            media_source_id=None,
        )

        self.assertEqual(10, info.saved_position_ticks)
        self.assertEqual("mp4", info.media_source_container)
        self.assertEqual("VideoFile", info.media_source_video_type)

    def test_maps_media_streams_to_tracks(self):
        tracks = media_tracks_from_item(
            {
                "MediaStreams": [
                    {"Type": "Audio", "Index": 1},
                    {"Type": "Subtitle", "Index": 2},
                ]
            }
        )

        self.assertEqual(MediaTrackKind.AUDIO, tracks[0].kind)
        self.assertEqual(1, tracks[0].source_index)
        self.assertEqual(MediaTrackKind.SUBTITLE, tracks[1].kind)
        self.assertEqual(2, tracks[1].source_index)


if __name__ == "__main__":
    unittest.main()
