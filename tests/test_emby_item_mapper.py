import unittest

from home_cinema_control.media_servers.common.media_tracks import MediaTrackKind
from home_cinema_control.media_servers.emby.item_mapper import (
    media_server_item_playback_info_from_item,
    media_server_playback_source_from_item,
    media_tracks_from_item,
)


class EmbyItemMapperTest(unittest.TestCase):
    def test_maps_normal_playback_source_without_overriding_filename(self):
        source = media_server_playback_source_from_item(
            {
                "Path": "/media/Movie/Movie.mkv",
                "Container": "mkv",
                "MediaSources": [
                    {
                        "Id": "source-1",
                        "Path": "/media/Movie/Movie.mkv",
                        "Container": "mkv",
                        "RunTimeTicks": 10_000_000,
                    }
                ],
            },
            "source-1",
        )

        self.assertEqual("/media/Movie/Movie.mkv", source.path)
        self.assertEqual("mkv", source.container)
        self.assertIsNone(source.playback_file_name)

    def test_missing_media_source_id_uses_first_source_metadata_and_strm_filename(self):
        source = media_server_playback_source_from_item(
            {
                "Path": "/media/Movie/Movie.strm",
                "Container": "strm",
                "MediaSources": [
                    {
                        "Id": "source-1",
                        "Path": "/media/Movie/Movie.strm",
                        "Container": "mkv",
                    }
                ],
            },
            "",
        )

        self.assertEqual("/media/Movie/Movie.strm", source.path)
        self.assertEqual("mkv", source.container)
        self.assertEqual("Movie.mkv", source.playback_file_name)

    def test_unmatched_media_source_id_uses_first_source_metadata(self):
        source = media_server_playback_source_from_item(
            {
                "Path": "/media/Movie/Movie.strm",
                "Container": "strm",
                "MediaSources": [
                    {
                        "Id": "source-1",
                        "Path": "/media/Movie/Movie.strm",
                        "Container": "mp4",
                    }
                ],
            },
            "missing-source",
        )

        self.assertEqual("mp4", source.container)
        self.assertEqual("Movie.mp4", source.playback_file_name)

    def test_strm_source_container_falls_back_to_parent_container(self):
        source = media_server_playback_source_from_item(
            {
                "Path": "/media/Movie/Movie.strm",
                "Container": "mp4",
                "MediaSources": [
                    {
                        "Id": "source-1",
                        "Path": "/media/Movie/Movie.strm",
                        "Container": "strm",
                    }
                ],
            },
            "source-1",
        )

        self.assertEqual("mp4", source.container)
        self.assertEqual("Movie.mp4", source.playback_file_name)

    def test_empty_source_container_falls_back_to_parent_container(self):
        source = media_server_playback_source_from_item(
            {
                "Path": "/media/Movie/Movie.strm",
                "Container": "mkv",
                "MediaSources": [
                    {
                        "Id": "source-1",
                        "Path": "/media/Movie/Movie.strm",
                        "Container": "",
                    }
                ],
            },
            "source-1",
        )

        self.assertEqual("mkv", source.container)
        self.assertEqual("Movie.mkv", source.playback_file_name)

    def test_strm_target_path_supplies_extension_without_retaining_query(self):
        source = media_server_playback_source_from_item(
            {
                "Path": "/media/Movie/Movie.strm",
                "Container": "strm",
                "MediaSources": [
                    {
                        "Id": "source-1",
                        "Path": "https://example/path/Movie.m2ts?token=secret",
                        "Container": "strm",
                    }
                ],
            },
            "source-1",
        )

        self.assertEqual("/media/Movie/Movie.strm", source.path)
        self.assertEqual("m2ts", source.container)
        self.assertEqual("Movie.m2ts", source.playback_file_name)
        self.assertNotIn("secret", source.playback_file_name)

    def test_strm_without_reliable_container_fails_without_mkv_guess(self):
        with self.assertRaisesRegex(ValueError, "playable container"):
            media_server_playback_source_from_item(
                {
                    "Path": "/media/Movie/Movie.strm",
                    "Container": "strm",
                    "MediaSources": [
                        {
                            "Id": "source-1",
                            "Path": "https://example/path/stream",
                            "Container": "strm",
                        }
                    ],
                },
                "source-1",
            )

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
