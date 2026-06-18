import unittest

from home_cinema_control.media_servers.emby.session import EmbySession
from home_cinema_control.playback.state import BridgePlaybackState


class FakeResponse:
    status_code = 204
    text = ""


class RecordingEmbyClient:
    def __init__(self):
        self.calls = []

    def stop_session_playback(self, session_id, payload):
        self.calls.append(("stop_session_playback", session_id, payload))
        return FakeResponse()


class EmbySessionTest(unittest.TestCase):
    def test_stop_session_playback_does_not_send_seek_to_zero(self):
        emby_session = _emby_session()

        emby_session.stop_session_playback("session-1")

        self.assertEqual(
            [("stop_session_playback", "session-1", {"Command": "Stop"})],
            emby_session.client.calls,
        )


def _emby_session(playback_state=None):
    emby_session = object.__new__(EmbySession)
    emby_session.config = {"app": {"log_level": 0}}
    emby_session.user_info = {
        "User": {"Id": "auth-user"},
        "SessionInfo": {"Id": "bridge-session"},
    }
    emby_session.client = RecordingEmbyClient()
    emby_session._state = playback_state or BridgePlaybackState()
    return emby_session


if __name__ == "__main__":
    unittest.main()
