import json
import unittest

from home_cinema_control.media_servers.common.models import MediaServerCommandKind
from home_cinema_control.media_servers.common.websocket_events import (
    MediaServerWebsocketEventKind,
)
from home_cinema_control.media_servers.emby.websocket_event_mapper import (
    EmbyWebsocketEventMapper,
    command_from_emby_general_command_message,
    command_from_emby_playstate_message,
)


class EmbyWebsocketEventMapperTest(unittest.TestCase):
    def test_maps_playstate_payload_to_domain_command(self):
        command = command_from_emby_playstate_message({"Command": "Pause"})

        self.assertEqual(MediaServerCommandKind.PAUSE, command.kind)

    def test_maps_general_command_payload_to_domain_command(self):
        command = command_from_emby_general_command_message(
            {"Name": "SetAudioStreamIndex", "Arguments": {"Index": "2"}}
        )

        self.assertEqual(MediaServerCommandKind.SET_AUDIO_TRACK, command.kind)
        self.assertEqual(2, command.track_index)

    def test_maps_play_payload_to_intent_and_resolves_missing_controller_session(self):
        mapper = EmbyWebsocketEventMapper(
            emby_session=RecordingSession(controlling_session_id="resolved-session")
        )

        event = mapper.map(
            json.dumps(
                {
                    "MessageType": "Play",
                    "Data": {
                        "PlayCommand": "PlayNow",
                        "ItemIds": ["item-1"],
                        "ControllingUserId": "user-1",
                    },
                }
            )
        )

        self.assertEqual(MediaServerWebsocketEventKind.PLAYBACK_INTENT, event.kind)
        self.assertEqual("item-1", event.playback_intent.media_item_id)
        self.assertEqual(
            "resolved-session",
            event.playback_intent.source_client_session_id,
        )

    def test_keeps_controller_session_when_payload_provides_one(self):
        session = RecordingSession(controlling_session_id="should-not-be-used")
        mapper = EmbyWebsocketEventMapper(emby_session=session)

        event = mapper.map_play_payload(
            {
                "PlayCommand": "PlayNow",
                "ItemIds": ["item-1"],
                "ControllingUserId": "user-1",
                "SessionID": "real-session",
            }
        )

        self.assertEqual("real-session", event.playback_intent.source_client_session_id)
        self.assertEqual([], session.resolve_calls)

    def test_maps_sessions_payload_to_sessions_update(self):
        mapper = EmbyWebsocketEventMapper(emby_session=RecordingSession())
        sessions = [{"DeviceId": "tv-1"}]

        event = mapper.map(
            json.dumps({"MessageType": "Sessions", "Data": sessions})
        )

        self.assertEqual(MediaServerWebsocketEventKind.SESSIONS_UPDATE, event.kind)
        self.assertEqual(sessions, event.sessions)


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
