import unittest

from home_cinema_control.media_servers.common.models import (
    MediaServerItemPlaybackInfo,
    MediaServerNowPlaying,
    MediaServerSession,
)
from home_cinema_control.media_servers.common.session_monitor import (
    describe_session_playback_source,
    playback_intent_from_session,
)
from home_cinema_control.media_servers.emby.session_events import (
    find_monitored_session,
    is_same_media_item_request,
    playback_request_media_item_id,
)


class EmbySessionEventsTest(unittest.TestCase):
    def test_extracts_selected_item_id_from_list(self):
        self.assertEqual(
            "movie-2",
            playback_request_media_item_id(
                {
                    "ItemIds": ["movie-1", "movie-2"],
                    "StartIndex": 1,
                }
            ),
        )

    def test_extracts_item_id_from_scalar_value(self):
        self.assertEqual("11136", playback_request_media_item_id({"ItemIds": 11136}))

    def test_detects_same_media_item_request(self):
        self.assertTrue(
            is_same_media_item_request(
                {"ItemIds": [11136]},
                {"ItemIds": ["11136"]},
            )
        )

    def test_does_not_match_missing_current_item(self):
        self.assertFalse(
            is_same_media_item_request(
                None,
                {"ItemIds": ["11136"]},
            )
        )

    def test_maps_monitored_session_by_device_id_to_domain(self):
        session = find_monitored_session(
            [
                {"DeviceId": "phone"},
                {
                    "DeviceId": "lg-tv",
                    "Id": "session-1",
                    "DeviceName": "LG TV",
                    "UserId": "user-1",
                    "NowPlayingItem": {"Id": "11136", "Name": "Aquaman"},
                    "PlayState": {"MediaSourceId": "source-1"},
                },
            ],
            "lg-tv",
        )

        self.assertIsInstance(session, MediaServerSession)
        self.assertEqual("lg-tv", session.device_id)
        self.assertEqual("session-1", session.client_session_id)
        self.assertEqual("11136", session.now_playing.item_id)
        self.assertEqual("source-1", session.media_source_id)

    def test_unknown_device_maps_to_none(self):
        self.assertIsNone(find_monitored_session([{"DeviceId": "phone"}], "lg-tv"))

    def test_builds_playback_intent_from_session_snapshot(self):
        session = MediaServerSession(
            device_id="lg-tv",
            device_name="LG TV",
            user_id="user-1",
            client_session_id="session-1",
            now_playing=MediaServerNowPlaying(item_id="11136"),
            media_source_id="source-1",
            position_ticks=120_000_000,
            audio_stream_index=2,
            subtitle_stream_index=4,
        )

        intent = playback_intent_from_session(session)

        self.assertEqual("11136", intent.media_item_id)
        self.assertEqual("source-1", intent.media_source_id)
        self.assertEqual("session-1", intent.source_client_session_id)
        self.assertEqual("LG TV", intent.source_device_name)
        self.assertEqual(12, intent.start_position_seconds)
        self.assertEqual(2, intent.selected_audio_track_id)
        self.assertEqual(4, intent.selected_subtitle_track_id)

    def test_builds_playback_intent_from_saved_position_when_session_has_none(self):
        session = MediaServerSession(
            device_id="lg-tv",
            user_id="user-1",
            now_playing=MediaServerNowPlaying(item_id="11136"),
            position_ticks=None,
        )

        intent = playback_intent_from_session(
            session,
            saved_position_ticks=420_000_000,
        )

        self.assertEqual(42, intent.start_position_seconds)

    def test_describes_session_playback_source_for_diagnostics(self):
        session = MediaServerSession(
            device_id="lg-tv",
            now_playing=MediaServerNowPlaying(
                item_id="11136",
                name="Aquaman",
                item_type="Movie",
                container="blurayiso",
            ),
            media_source_id="source-1",
            position_ticks=0,
            audio_stream_index=1,
            subtitle_stream_index=-1,
        )

        item_playback_info = MediaServerItemPlaybackInfo.from_item_response(
            {
                "UserData": {
                    "PlaybackPositionTicks": 420_000_000,
                    "Played": False,
                    "PlayCount": 2,
                    "PlayedPercentage": 44.0,
                },
                "MediaSources": [
                    {
                        "Id": "source-1",
                        "Container": "iso",
                        "VideoType": "Bluray",
                    }
                ],
            },
            media_source_id="source-1",
        )

        source = describe_session_playback_source(
            session,
            item_playback_info=item_playback_info,
        )

        self.assertEqual("11136", source["item_id"])
        self.assertEqual("blurayiso", source["item_container"])
        self.assertEqual("iso", source["media_source_container"])
        self.assertEqual("Bluray", source["media_source_video_type"])
        self.assertTrue(source["session_position_ticks_present"])
        self.assertEqual(0, source["session_position_ticks"])
        self.assertEqual(420_000_000, source["saved_position_ticks"])
        self.assertFalse(source["played"])


class MediaServerItemPlaybackInfoTest(unittest.TestCase):
    def test_maps_item_response_to_domain(self):
        info = MediaServerItemPlaybackInfo.from_item_response(
            {
                "UserData": {
                    "PlaybackPositionTicks": 420_000_000,
                    "Played": True,
                    "PlayCount": 3,
                    "PlayedPercentage": 91.5,
                },
                "MediaSources": [
                    {"Id": "other-source", "Container": "mp4"},
                    {"Id": "source-1", "Container": "mkv", "VideoType": "BluRay"},
                ],
            },
            media_source_id="source-1",
        )

        self.assertEqual(420_000_000, info.saved_position_ticks)
        self.assertTrue(info.played)
        self.assertEqual(3, info.play_count)
        self.assertEqual(91.5, info.playback_percentage)
        self.assertEqual("mkv", info.media_source_container)
        self.assertEqual("BluRay", info.media_source_video_type)

    def test_falls_back_to_first_media_source_when_id_unmatched(self):
        info = MediaServerItemPlaybackInfo.from_item_response(
            {"MediaSources": [{"Id": "other-source", "Container": "mp4"}]},
            media_source_id="missing-source",
        )

        self.assertEqual("mp4", info.media_source_container)

    def test_missing_response_maps_to_empty_domain(self):
        info = MediaServerItemPlaybackInfo.from_item_response(
            None, media_source_id="source-1"
        )

        self.assertIsNone(info.saved_position_ticks)
        self.assertIsNone(info.played)
        self.assertIsNone(info.media_source_container)


if __name__ == "__main__":
    unittest.main()
