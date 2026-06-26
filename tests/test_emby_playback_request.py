import unittest

from home_cinema_control.media_servers.emby.playback_request import (
    build_playback_intent_from_play_command,
    parse_playback_request_payload,
)


class EmbyPlaybackRequestTest(unittest.TestCase):
    def test_uses_explicit_start_position_when_present(self):
        loaded_items = []

        params = parse_playback_request_payload(
            {
                "ItemIds": ["item-1"],
                "StartPositionTicks": 120,
                "SavedPlaybackPositionTicks": 500,
                "MediaSourceId": "source-1",
                "AudioStreamIndex": 2,
                "SubtitleStreamIndex": 4,
                "ControllingUserId": "user-1",
                "SessionID": "session-1",
                "PlaySessionId": "play-session-1",
                "DeviceName": "LG TV",
                "Device_Id": "device-1",
            },

            load_item_info=lambda user_id, item_id: loaded_items.append(
                (user_id, item_id)
            ),
        )

        self.assertEqual("item-1", params["item_id"])
        self.assertEqual(120, params["auto_resume"])
        self.assertEqual("source-1", params["media_source_id"])
        self.assertEqual(2, params["audio_stream_index"])
        self.assertEqual(4, params["subtitle_stream_index"])
        self.assertEqual("user-1", params["ControllingUserId"])
        self.assertEqual("session-1", params["Session_id"])
        self.assertEqual("play-session-1", params["play_session_id"])
        self.assertEqual("LG TV", params["DeviceName"])
        self.assertEqual("device-1", params["Device_Id"])
        self.assertEqual([], loaded_items)

    def test_uses_saved_position_when_start_position_is_absent(self):
        params = parse_playback_request_payload(
            {
                "ItemIds": ["item-1"],
                "SavedPlaybackPositionTicks": 500,
            },

            load_item_info=lambda user_id, item_id: {},
        )

        self.assertEqual(500, params["auto_resume"])

    def test_loads_user_item_position_when_no_position_is_present(self):
        params = parse_playback_request_payload(
            {
                "ItemIds": ["item-1"],
                "ControllingUserId": "user-1",
            },

            load_item_info=lambda user_id, item_id: {
                "UserData": {"PlaybackPositionTicks": 900}
            },
        )

        self.assertEqual(900, params["auto_resume"])

    def test_uses_id_as_session_fallback_for_remote_commands(self):
        params = parse_playback_request_payload(
            {
                "ItemIds": ["item-1"],
                "StartPositionTicks": 0,
                "Id": "remote-session",
            },

            load_item_info=lambda user_id, item_id: {},
        )

        self.assertEqual("remote-session", params["Session_id"])


class BuildPlaybackIntentFromPlayCommandTest(unittest.TestCase):
    def test_uses_session_id_when_emby_provides_it(self):
        intent = build_playback_intent_from_play_command(
            {
                "PlayCommand": "PlayNow",
                "ItemIds": ["item-1"],
                "StartPositionTicks": 0,
                "SessionID": "real-controller-session",
                "Id": "bridge-own-session",
            },
            load_item_info=lambda user_id, item_id: {},
        )

        self.assertEqual("real-controller-session", intent.source_client_session_id)

    def test_does_not_fall_back_to_the_bridge_own_session_id(self):
        intent = build_playback_intent_from_play_command(
            {
                "PlayCommand": "PlayNow",
                "ItemIds": ["item-1"],
                "StartPositionTicks": 0,
                "Id": "bridge-own-session",
            },
            load_item_info=lambda user_id, item_id: {},
        )

        self.assertIsNone(intent.source_client_session_id)


if __name__ == "__main__":
    unittest.main()
