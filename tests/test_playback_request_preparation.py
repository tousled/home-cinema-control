import unittest

from home_cinema_control.devices.tv.models import TvInputTarget
from home_cinema_control.media_servers.emby.constants import EMBY_TICKS_PER_SECOND
from home_cinema_control.playback.intent import PlaybackIntent
from home_cinema_control.playback.request_preparation import (
    PLAYBACK_START_POLL_INTERVAL_SECONDS,
    prepare_playback_requests,
)


class PlaybackRequestPreparationTest(unittest.TestCase):
    def test_prepares_playback_requests_from_config_intent_and_item_info(self):
        prepared = prepare_playback_requests(
            config={
                "playback": {
                    "path_mappings": [
                        {"source_path": "/emby", "player_path": "/nas", "protocol": "nfs"}
                    ]
                },
                "tv": {
                    "enabled": True,
                    "player_hdmi_input_id": 2,
                    "available_hdmi_inputs": [
                        {"id": "com.webos.app.hdmi1", "appId": "app1"},
                        {"id": "com.webos.app.hdmi2", "appId": "app2"},
                        {"id": "com.webos.app.hdmi3", "appId": "app3"},
                    ],
                },
                "av": {
                    "enabled": True,
                    "player_hdmi_input": "BD",
                },
                "oppo": {
                    "always_on": False,
                    "playback_start_timeout_seconds": 42,
                },
            },
            intent=_intent(),
            item_info={
                "Path": "/emby/Movies/Movie.mkv",
                "Container": "mkv",
                "RunTimeTicks": 456 * EMBY_TICKS_PER_SECOND,
            },
            previous_tv_app_id_override="com.emby.app",
        )

        self.assertEqual("nas", prepared.media_location.content_server)
        self.assertEqual("Movies", prepared.media_location.content_directory)
        self.assertEqual("Movie.mkv", prepared.media_location.playback_file_name)
        self.assertEqual("mkv", prepared.media_location.playback_file_format)
        self.assertEqual("nfs", prepared.media_location.network_protocol)
        self.assertEqual("/emby/Movies/Movie.mkv", prepared.movie_path)

        output_request = prepared.output_switch_request
        self.assertEqual(
            TvInputTarget(input_id="com.webos.app.hdmi3", confirmation_app_id="app3"),
            output_request.tv_input,
        )
        self.assertEqual("BD", output_request.av_input_id)
        self.assertTrue(output_request.tv_enabled)
        self.assertTrue(output_request.av_enabled)
        self.assertEqual("com.emby.app", output_request.previous_tv_app_id_override)

        oppo_request = prepared.oppo_playback_start_request
        self.assertFalse(oppo_request.assume_player_already_on)
        self.assertEqual("nfs", oppo_request.network_protocol)
        self.assertEqual(42, oppo_request.startup_timeout_seconds)
        self.assertEqual(
            PLAYBACK_START_POLL_INTERVAL_SECONDS,
            oppo_request.poll_interval_seconds,
        )

        completion_request = prepared.startup_completion_request
        self.assertEqual(12, completion_request.start_position_seconds)
        self.assertEqual(456, completion_request.expected_duration_seconds)
        self.assertEqual("user-1", completion_request.source_user_id)
        self.assertEqual("media-1", completion_request.media_item_id)
        self.assertEqual(2, completion_request.selected_source_audio_track_id)
        self.assertEqual(-1, completion_request.selected_source_subtitle_track_id)

    def test_uses_safe_defaults_for_optional_output_devices(self):
        prepared = prepare_playback_requests(
            config={
                "playback": {"path_mappings": []},
                "oppo": {
                    "always_on": True,
                    "playback_start_timeout_seconds": 30,
                },
            },
            intent=_intent(),
            item_info={
                "Path": "/nas/Movies/Movie.mkv",
                "Container": "mkv",
                "RunTimeTicks": "not-a-number",
            },
            previous_tv_app_id_override=None,
        )

        output_request = prepared.output_switch_request
        self.assertEqual(TvInputTarget(input_id=""), output_request.tv_input)
        self.assertIsNone(output_request.av_input_id)
        self.assertFalse(output_request.tv_enabled)
        self.assertFalse(output_request.av_enabled)
        self.assertEqual(0, prepared.startup_completion_request.expected_duration_seconds)


def _intent() -> PlaybackIntent:
    return PlaybackIntent(
        media_item_id="media-1",
        media_source_id="source-1",
        source_user_id="user-1",
        source_client_session_id="session-1",
        source_device_id="device-1",
        source_device_name="Living Room TV",
        start_position_seconds=12,
        selected_audio_track_id=2,
        selected_subtitle_track_id=-1,
    )


if __name__ == "__main__":
    unittest.main()
