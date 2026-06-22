import unittest

from home_cinema_control.playback.intent import PlaybackOrigin
from home_cinema_control.playback.notification_sender import (
    playback_start_messages,
    send_playback_message,
)


class PlaybackNotificationSenderTest(unittest.TestCase):
    def test_builds_playback_start_messages_from_language_config(self):
        messages = playback_start_messages(
            {
                "msg-playback-timeout": "timeout",
                "msg-playback-error-mount": "error mount",
                "msg-playback-error-play": "error play",
                "msg-playback-error-no-oppo": "no oppo",
            }
        )

        self.assertEqual("timeout", messages.timeout_play)
        self.assertEqual("error mount", messages.error_mount)
        self.assertEqual("error play", messages.error_play)
        self.assertEqual("no oppo", messages.error_no_oppo)

    def test_sends_playback_message_to_source_session(self):
        playback_session = RecordingPlaybackSession()

        send_playback_message(
            playback_session,
            PlaybackOrigin.OBSERVED_TV_CLIENT,
            "session-1",
            "message",
            timeout_ms=5000,
        )

        self.assertEqual(
            [("session-1", "message", 5000)],
            playback_session.notifications,
        )

    def test_does_not_raise_when_notify_session_fails(self):
        playback_session = RaisingPlaybackSession()

        send_playback_message(
            playback_session,
            PlaybackOrigin.REMOTE_CONTROL_COMMAND,
            "session-1",
            "message",
        )

    def test_skips_playback_message_when_source_session_is_absent(self):
        playback_session = RecordingPlaybackSession()

        send_playback_message(
            playback_session,
            PlaybackOrigin.REMOTE_CONTROL_COMMAND,
            None,
            "message",
        )

        self.assertEqual([], playback_session.notifications)


class RecordingPlaybackSession:
    def __init__(self):
        self.notifications = []

    def notify_session(self, session_id, message, timeout_ms=None):
        self.notifications.append((session_id, message, timeout_ms))


class RaisingPlaybackSession:
    def notify_session(self, session_id, message, timeout_ms=None):
        raise RuntimeError("network error")


if __name__ == "__main__":
    unittest.main()
