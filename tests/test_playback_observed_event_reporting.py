import unittest
from types import SimpleNamespace

from home_cinema_control.playback.observed_event_adapter import (
    ObservedPlaybackSessionSink,
    configure_oppo_observed_event_reporting,
)
from home_cinema_control.playback.state import BridgePlaybackState


class PlaybackObservedEventReportingTest(unittest.TestCase):
    def test_configures_reporter_on_during_playback_orchestrator(self):
        wiring = FakePlaybackWiring()

        configured = configure_oppo_observed_event_reporting(
            playback_state=BridgePlaybackState(),
            playback_wiring=wiring,
            track_mapper=FakeTrackMapper(),
        )

        self.assertTrue(configured)
        self.assertIsNone(wiring.startup_wiring.oppo_playback.reporter)
        self.assertIsNotNone(wiring.during_playback_orchestrator.reporter)

    def test_observed_playback_sink_updates_playstate(self):
        state = BridgePlaybackState()
        state.playstate = "Playing"
        sink = ObservedPlaybackSessionSink(
            playback_state=state,
            publisher=RecordingPublisher(),
        )

        sink.report_event("Pause", position_ticks=10, is_paused=True)
        self.assertEqual("Paused", state.playstate)

        sink.report_event("Unpause", position_ticks=20, is_paused=False)
        self.assertEqual("Playing", state.playstate)

        sink.stopped(position_seconds=2)
        self.assertEqual("Free", state.playstate)


class FakePlaybackWiring:
    def __init__(self):
        self.startup_wiring = SimpleNamespace(oppo_playback=FakeOppoPlayback())
        self.playback_event_publisher = RecordingPublisher()
        self.during_playback_orchestrator = FakeDuringPlaybackOrchestrator()


class FakeOppoPlayback:
    def __init__(self):
        self.reporter = None

    def set_observed_event_reporter(self, reporter):
        self.reporter = reporter


class FakeDuringPlaybackOrchestrator:
    def __init__(self):
        self.reporter = None

    def set_observed_event_reporter(self, reporter):
        self.reporter = reporter


class FakeTrackMapper:
    def player_audio_to_source_track_id(self, player_track_index):
        return player_track_index

    def player_subtitle_to_source_track_id(self, player_track_index):
        return player_track_index


class RecordingPublisher:
    def __init__(self):
        self.calls = []
        self.last_position_ticks = 0

    def report_event(self, event_name, **kwargs):
        self.calls.append(("event", event_name, kwargs))

    def stopped(self, **kwargs):
        self.calls.append(("stopped", kwargs))

    def progress(self, **kwargs):
        self.calls.append(("progress", kwargs))


if __name__ == "__main__":
    unittest.main()
