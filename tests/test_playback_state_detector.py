import unittest

from home_cinema_control.playback.events import (
    PlaybackEventContext,
    PlaybackEventType,
    PlaybackObservation,
    PlaybackObservedState,
)
from home_cinema_control.playback.state_detector import PlaybackStateDetector


class PlaybackStateDetectorTest(unittest.TestCase):
    def setUp(self):
        ids = iter(("event-1", "event-2", "event-3", "event-4"))
        self.detector = PlaybackStateDetector(event_id_factory=lambda: next(ids))
        self.context = PlaybackEventContext(
            session_id="session-1",
            media_type="movie",
            title="Example",
            source="emby",
            player="oppo",
        )

    def test_emits_started_and_suppresses_repeated_states(self):
        started = self.detector.start_session(self.context)

        self.assertEqual(PlaybackEventType.STARTED, started.event_type)
        self.assertEqual("event-1", started.event_id)
        self.assertIsNone(
            self.detector.observe(
                PlaybackObservation(PlaybackObservedState.PLAYING, source="polling")
            )
        )

    def test_emits_pause_and_resume_transitions(self):
        self.detector.start_session(self.context)

        paused = self.detector.observe(
            PlaybackObservation(PlaybackObservedState.PAUSED, source="svm3")
        )
        duplicate = self.detector.observe(
            PlaybackObservation(PlaybackObservedState.PAUSED, source="polling")
        )
        resumed = self.detector.observe(
            PlaybackObservation(PlaybackObservedState.PLAYING, source="command")
        )

        self.assertEqual(PlaybackEventType.PAUSED, paused.event_type)
        self.assertEqual(PlaybackEventType.RESUMED, resumed.event_type)
        self.assertIsNone(duplicate)

    def test_stop_resets_session(self):
        self.detector.start_session(self.context)

        stopped = self.detector.stop_session()

        self.assertEqual(PlaybackEventType.STOPPED, stopped.event_type)
        self.assertIsNone(self.detector.stop_session())
        self.assertIsNone(
            self.detector.observe(
                PlaybackObservation(PlaybackObservedState.PAUSED, source="svm3")
            )
        )

    def test_published_lifecycle_events_keep_session_order(self):
        published = []

        self.detector.start_session(self.context, publish=published.append)
        self.detector.observe(
            PlaybackObservation(PlaybackObservedState.PAUSED, source="svm3"),
            publish=published.append,
        )
        self.detector.observe(
            PlaybackObservation(PlaybackObservedState.PLAYING, source="command"),
            publish=published.append,
        )
        self.detector.stop_session(publish=published.append)

        self.assertEqual(
            [
                PlaybackEventType.STARTED,
                PlaybackEventType.PAUSED,
                PlaybackEventType.RESUMED,
                PlaybackEventType.STOPPED,
            ],
            [event.event_type for event in published],
        )


if __name__ == "__main__":
    unittest.main()
