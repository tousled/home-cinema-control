import json
import unittest

from home_cinema_control.media_servers.common.models import MediaServerCommandKind
from home_cinema_control.media_servers.common.websocket_events import (
    MediaServerWebsocketEventKind,
)
from home_cinema_control.media_servers.jellyfin.websocket_event_mapper import (
    JellyfinWebsocketEventMapper,
    command_from_jellyfin_general_command_message,
    command_from_jellyfin_playstate_message,
)


class JellyfinWebsocketEventMapperTest(unittest.TestCase):
    def test_maps_playstate_payload_to_domain_command(self):
        command = command_from_jellyfin_playstate_message({"Command": "Stop"})

        self.assertEqual(MediaServerCommandKind.STOP, command.kind)

    def test_maps_general_command_payload_to_domain_command(self):
        command = command_from_jellyfin_general_command_message(
            {"Name": "SetSubtitleStreamIndex", "Arguments": {"Index": "-1"}}
        )

        self.assertEqual(MediaServerCommandKind.SET_SUBTITLE_TRACK, command.kind)
        self.assertEqual(-1, command.track_index)

    def test_maps_play_payload_to_intent_and_resolves_missing_controller_session(self):
        mapper = JellyfinWebsocketEventMapper(
            jellyfin_session=RecordingSession(controlling_session_id="resolved-session")
        )

        event = mapper.map(
            json.dumps(
                {
                    "MessageType": "Play",
                    "Data": {
                        "PlayCommand": "PlayNow",
                        "ItemIds": ["item-1"],
                        "ControllingUserId": "user-1",
                        "DeviceId": "phone-1",
                    },
                }
            )
        )

        self.assertEqual(MediaServerWebsocketEventKind.PLAYBACK_INTENT, event.kind)
        self.assertEqual("item-1", event.playback_intent.media_item_id)
        self.assertEqual("phone-1", event.playback_intent.source_device_id)
        self.assertEqual(
            "resolved-session",
            event.playback_intent.source_client_session_id,
        )

    def test_maps_unsupported_play_payload_to_unsupported_event(self):
        mapper = JellyfinWebsocketEventMapper(jellyfin_session=RecordingSession())

        event = mapper.map_play_payload({"PlayCommand": "PlayLast"})

        self.assertEqual(MediaServerWebsocketEventKind.UNSUPPORTED, event.kind)


class RecordingSession:
    def __init__(self, controlling_session_id=None):
        self._controlling_session_id = controlling_session_id
        self.resolve_calls = []

    def get_item_info(self, user_id, item_id):
        return {"UserData": {"PlaybackPositionTicks": 0}}

    def find_controlling_session_id(self, controlling_user_id):
        self.resolve_calls.append(controlling_user_id)
        return self._controlling_session_id


if __name__ == "__main__":
    unittest.main()
