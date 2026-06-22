import time
import unittest

from home_cinema_control.media_servers.emby.playback import MediaContentKind
from home_cinema_control.playback.intent import PlaybackOrigin
from home_cinema_control.playback.startup.messaging import PlaybackStartupMessagingService

_LANG = {
    "msg-startup-received": "received",
    "msg-startup-locating": "locating",
    "msg-startup-starting": "starting",
    "msg-startup-fine-tuning": "fine tuning",
    "msg-startup-still-with-you": "still with you",
    "msg-startup-action-movie": "movie",
    "msg-startup-action-episode": "episode",
    "msg-startup-action-concert": "concert",
    "msg-startup-action-live-tv": "live tv",
    "msg-startup-action-generic": "generic",
}


def _service(playback_session, **kwargs):
    return PlaybackStartupMessagingService(
        playback_session=playback_session,
        origin=PlaybackOrigin.REMOTE_CONTROL_COMMAND,
        session_id="session-1",
        lang=_LANG,
        **kwargs,
    )


class PlaybackStartupMessagingServiceTest(unittest.TestCase):
    def test_received_sends_the_received_message(self):
        session = RecordingPlaybackSession()
        _service(session).received()

        self.assertEqual([("session-1", "received", None)], session.notifications)

    def test_locating_sends_the_locating_message(self):
        session = RecordingPlaybackSession()
        _service(session).locating()

        self.assertEqual([("session-1", "locating", None)], session.notifications)

    def test_tracks_applying_sends_the_fine_tuning_message(self):
        session = RecordingPlaybackSession()
        _service(session).tracks_applying()

        self.assertEqual([("session-1", "fine tuning", None)], session.notifications)

    def test_collision_guard_skips_a_second_touchpoint_sent_immediately_after(self):
        session = RecordingPlaybackSession()
        service = _service(session)

        service.received()
        service.locating()
        service.tracks_applying()

        self.assertEqual([("session-1", "received", None)], session.notifications)

    def test_collision_guard_allows_a_touchpoint_after_the_interval_elapses(self):
        session = RecordingPlaybackSession()
        service = _service(session)
        service._gate._min_interval_seconds = 0.05

        service.received()
        time.sleep(0.06)
        service.locating()

        self.assertEqual(
            [("session-1", "received", None), ("session-1", "locating", None)],
            session.notifications,
        )

    def test_notify_waiting_sends_starting_on_first_call_regardless_of_attempt(self):
        session = RecordingPlaybackSession()
        service = _service(session)

        service.notify_waiting(999)

        self.assertEqual([("session-1", "starting", None)], session.notifications)

    def test_notify_waiting_does_not_repeat_starting_message(self):
        session = RecordingPlaybackSession()
        service = _service(session)

        for attempt in range(1, 10):
            service.notify_waiting(attempt)

        self.assertEqual([("session-1", "starting", None)], session.notifications)

    def test_notify_waiting_sends_still_with_you_once_real_time_crosses_threshold(self):
        session = RecordingPlaybackSession()
        service = _service(session, still_with_you_threshold_seconds=0.05)

        service.notify_waiting(1)
        time.sleep(0.06)
        service.notify_waiting(2)
        service.notify_waiting(3)

        self.assertEqual(
            [
                ("session-1", "starting", None),
                ("session-1", "still with you", None),
            ],
            session.notifications,
        )

    def test_action_bypasses_the_collision_guard(self):
        session = RecordingPlaybackSession()
        service = _service(session)

        service.received()
        service.action(MediaContentKind.MOVIE)

        self.assertEqual(
            [("session-1", "received", None), ("session-1", "movie", None)],
            session.notifications,
        )

    def test_action_selects_message_by_content_kind(self):
        session = RecordingPlaybackSession()
        service = _service(session)

        service.action(MediaContentKind.EPISODE)
        service.action(MediaContentKind.CONCERT)
        service.action(MediaContentKind.LIVE_TV)
        service.action(MediaContentKind.OTHER)

        self.assertEqual(
            [
                ("session-1", "episode", None),
                ("session-1", "concert", None),
                ("session-1", "live tv", None),
                ("session-1", "generic", None),
            ],
            session.notifications,
        )


class PlaybackStartupMessagingServiceNeverRaisesTest(unittest.TestCase):
    """HCC-TASK-027: a notification bug must never be able to look like a
    playback failure to the orchestrator. These tests force an internal
    failure (not a network failure — that path was already covered) in each
    public method and assert nothing escapes."""

    def test_received_does_not_raise_when_lang_key_is_missing(self):
        session = RecordingPlaybackSession()
        service = PlaybackStartupMessagingService(
            playback_session=session,
            origin=PlaybackOrigin.REMOTE_CONTROL_COMMAND,
            session_id="session-1",
            lang={},  # missing every key
        )

        service.received()  # must not raise

        self.assertEqual([], session.notifications)

    def test_locating_does_not_raise_when_lang_key_is_missing(self):
        session = RecordingPlaybackSession()
        service = PlaybackStartupMessagingService(
            playback_session=session,
            origin=PlaybackOrigin.REMOTE_CONTROL_COMMAND,
            session_id="session-1",
            lang={},
        )

        service.locating()

        self.assertEqual([], session.notifications)

    def test_tracks_applying_does_not_raise_when_lang_key_is_missing(self):
        session = RecordingPlaybackSession()
        service = PlaybackStartupMessagingService(
            playback_session=session,
            origin=PlaybackOrigin.REMOTE_CONTROL_COMMAND,
            session_id="session-1",
            lang={},
        )

        service.tracks_applying()

        self.assertEqual([], session.notifications)

    def test_notify_waiting_does_not_raise_when_lang_key_is_missing(self):
        session = RecordingPlaybackSession()
        service = PlaybackStartupMessagingService(
            playback_session=session,
            origin=PlaybackOrigin.REMOTE_CONTROL_COMMAND,
            session_id="session-1",
            lang={},
        )

        service.notify_waiting(1)

        self.assertEqual([], session.notifications)

    def test_action_does_not_raise_when_lang_key_is_missing(self):
        session = RecordingPlaybackSession()
        service = PlaybackStartupMessagingService(
            playback_session=session,
            origin=PlaybackOrigin.REMOTE_CONTROL_COMMAND,
            session_id="session-1",
            lang={},  # missing even the generic fallback key
        )

        service.action(MediaContentKind.MOVIE)  # must not raise

        self.assertEqual([], session.notifications)

    def test_action_does_not_raise_on_an_unexpected_content_kind_value(self):
        session = RecordingPlaybackSession()
        service = _service(session)

        service.action("not-a-real-content-kind")  # must not raise

        self.assertEqual([("session-1", "generic", None)], session.notifications)


class RecordingPlaybackSession:
    def __init__(self):
        self.notifications = []

    def notify_session(self, session_id, message, timeout_ms=None):
        self.notifications.append((session_id, message, timeout_ms))


if __name__ == "__main__":
    unittest.main()
