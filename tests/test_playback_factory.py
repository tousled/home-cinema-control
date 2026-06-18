import unittest

from home_cinema_control.playback.factory import (
    PlaybackSessionStateSyncProgressReporter,
    create_during_playback_orchestrator,
)
from home_cinema_control.playback.during import (
    DuringPlaybackOrchestrator,
    PollingPlaybackObservationStrategy,
)
from home_cinema_control.playback.state import BridgePlaybackState


class RecordingProgressReporter:
    def __init__(self):
        self.calls = []
        self.events = []

    def progress(self, **kwargs):
        self.calls.append(kwargs)
        return "reported"

    def report_event(self, event_name, **kwargs):
        self.events.append((event_name, kwargs))
        return "event-reported"


class PlaybackSessionStateSyncProgressReporterTest(unittest.TestCase):
    def test_syncs_session_playstate_from_progress_pause_state(self):
        playback_state = BridgePlaybackState()
        progress_reporter = RecordingProgressReporter()
        reporter = PlaybackSessionStateSyncProgressReporter(
            playback_state=playback_state,
            progress_reporter=progress_reporter,
        )

        paused_result = reporter.progress(
            position_seconds=10,
            duration_seconds=100,
            is_paused=True,
        )
        playing_result = reporter.progress(
            position_seconds=20,
            duration_seconds=100,
            is_paused=False,
        )

        self.assertEqual("reported", paused_result)
        self.assertEqual("reported", playing_result)
        self.assertEqual("Playing", playback_state.playstate)
        self.assertEqual(
            [
                {
                    "position_seconds": 10,
                    "duration_seconds": 100,
                    "is_paused": True,
                    "is_muted": False,
                    "force": False,
                },
                {
                    "position_seconds": 20,
                    "duration_seconds": 100,
                    "is_paused": False,
                    "is_muted": False,
                    "force": False,
                },
            ],
            progress_reporter.calls,
        )
        self.assertEqual(
            [
                (
                    "Unpause",
                    {
                        "position_ticks": 200_000_000,
                        "runtime_ticks": 1_000_000_000,
                        "is_paused": False,
                        "is_muted": False,
                    },
                )
            ],
            progress_reporter.events,
        )


class PlaybackDuringFactoryTest(unittest.TestCase):
    def test_auto_mode_uses_observation_fallback_orchestrator(self):
        orchestrator = create_during_playback_orchestrator(
            config=_config("auto"),
            oppo_playback=object(),
            progress_reporter=RecordingProgressReporter(),
        )

        self.assertIsInstance(orchestrator, DuringPlaybackOrchestrator)

    def test_polling_mode_uses_existing_polling_orchestrator(self):
        orchestrator = create_during_playback_orchestrator(
            config=_config("polling"),
            oppo_playback=object(),
            progress_reporter=RecordingProgressReporter(),
        )

        self.assertIsInstance(orchestrator, PollingPlaybackObservationStrategy)


def _config(observation_mode):
    return {
        "OPPO_Port": 23,
        "oppo": {
            "ip": "192.168.1.50",
            "observation_mode": observation_mode,
            "connection_timeout_seconds": 3,
        },
    }


if __name__ == "__main__":
    unittest.main()
