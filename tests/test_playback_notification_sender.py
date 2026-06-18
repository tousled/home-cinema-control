import unittest

from home_cinema_control.playback.intent import PlaybackOrigin
from home_cinema_control.playback.notification_sender import (
    PlaybackStartupWaitNotifier,
    playback_start_messages,
    send_playback_message,
)


class PlaybackNotificationSenderTest(unittest.TestCase):
    def test_builds_playback_start_messages_from_language_config(self):
        messages = playback_start_messages(
            {
                "msg-playback-starting": "init",
                "msg-playback-waiting-mount": "mount",
                "msg-playback-waiting-play": "play",
                "msg-playback-timeout": "timeout",
                "msg-playback-error-mount": "error mount",
                "msg-playback-error-play": "error play",
                "msg-playback-error-no-oppo": "no oppo",
            }
        )

        self.assertEqual("init", messages.init_oppo)
        self.assertEqual("mount", messages.wait_for_mount)
        self.assertEqual("play", messages.wait_for_play)
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

    def test_skips_playback_message_when_source_session_is_absent(self):
        playback_session = RecordingPlaybackSession()

        send_playback_message(
            playback_session,
            PlaybackOrigin.REMOTE_CONTROL_COMMAND,
            None,
            "message",
        )

        self.assertEqual([], playback_session.notifications)

    def test_startup_wait_notifier_emits_one_notification_per_elapsed_second(self):
        playback_session = RecordingPlaybackSession()
        notifier = PlaybackStartupWaitNotifier(
            playback_session=playback_session,
            origin=PlaybackOrigin.OBSERVED_TV_CLIENT,
            session_id="session-1",
            wait_for_play_message="waiting ",
            poll_interval_seconds=0.5,
        )

        for attempt in range(1, 5):
            notifier.notify_waiting(attempt)

        self.assertEqual(
            [
                ("session-1", "waiting 1s", 999),
                ("session-1", "waiting 2s", 999),
            ],
            playback_session.notifications,
        )


class RecordingPlaybackSession:
    def __init__(self):
        self.notifications = []

    def notify_session(self, session_id, message, timeout_ms=None):
        self.notifications.append((session_id, message, timeout_ms))


if __name__ == "__main__":
    unittest.main()
