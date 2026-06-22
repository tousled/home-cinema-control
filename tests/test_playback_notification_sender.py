import unittest

from home_cinema_control.playback.intent import PlaybackOrigin
from home_cinema_control.playback.notification_sender import (
    playback_start_messages,
    send_playback_message,
    send_stop_with_delivery_reliability,
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


class SendStopWithDeliveryReliabilityTest(unittest.TestCase):
    """Shared by both call sites that need the source client's screen to
    actually clear: handoff start (`playback/application.py`) and playback
    finish (`MediaServerPlaybackEventPublisher`). Sends twice in one call —
    callers must not assume a single internal send is enough, that gap is
    exactly what let the stale-screen freeze come back for the
    `REMOTE_CONTROL_COMMAND` origin. See
    `.agents/tasks/26-p2-emby-source-client-keeps-stale-paused-playback-screen.md`."""

    def test_sends_stop_to_the_given_session_twice(self):
        calls = []

        send_stop_with_delivery_reliability(calls.append, "session-1")

        self.assertEqual(["session-1", "session-1"], calls)

    def test_does_nothing_without_a_session_id(self):
        calls = []

        send_stop_with_delivery_reliability(calls.append, None)

        self.assertEqual([], calls)

    def test_returns_the_first_sends_response(self):
        responses = iter(["first-response", "second-response"])

        result = send_stop_with_delivery_reliability(
            lambda session_id: next(responses), "session-1"
        )

        self.assertEqual("first-response", result)

    def test_still_sends_a_second_time_when_the_first_send_fails(self):
        calls = []

        def _stop(session_id):
            calls.append(session_id)
            if len(calls) == 1:
                raise RuntimeError("network blip")

        send_stop_with_delivery_reliability(_stop, "session-1")

        self.assertEqual(["session-1", "session-1"], calls)

    def test_swallows_a_failure_from_the_second_send(self):
        calls = []

        def _stop(session_id):
            calls.append(session_id)
            if len(calls) == 2:
                raise RuntimeError("network blip")

        send_stop_with_delivery_reliability(_stop, "session-1")

        self.assertEqual(["session-1", "session-1"], calls)


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
