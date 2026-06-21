import unittest

from home_cinema_control.devices.oppo.playback_state import (
    OppoPlaybackCategory,
    OppoPlaybackStatus,
)
from home_cinema_control.devices.oppo.verbose_events import parse_verbose_event
from home_cinema_control.playback.during import (
    PlaybackMonitoringRequest,
    PlaybackMonitoringStopReason,
    VerbosePlaybackObservationStrategy,
)
from home_cinema_control.playback.observed_events import ObservedPlaybackEventType


class SVM3PlaybackObservationStrategyTest(unittest.TestCase):
    def test_monitors_svm3_until_stop_without_qpl_polling(self):
        source = RecordingEventSource(
            [
                "@UPL PLAY",
                "@UTC 000 015 C 00:00:10",
                "@UTC 000 015 C 00:00:20",
                "@UPL STOP",
            ]
        )
        reporter = RecordingObservedReporter()
        orchestrator = VerbosePlaybackObservationStrategy(
            event_source=source,
            observed_event_reporter=reporter,
        )

        result = orchestrator.monitor_until_stopped(
            PlaybackMonitoringRequest(initial_position_seconds=5)
        )

        self.assertEqual(20, result.position_seconds)
        self.assertEqual(0, result.duration_seconds)
        self.assertEqual(OppoPlaybackStatus.STOP, result.final_state.status)
        self.assertEqual(OppoPlaybackCategory.TRANSITION, result.final_state.category)
        self.assertEqual(PlaybackMonitoringStopReason.PLAYER_IDLE, result.stop_reason)
        self.assertEqual(3, source.listen_kwargs["verbose_mode"])
        self.assertFalse(source.listen_kwargs["restore_verbose_mode"])
        self.assertEqual(30.0, source.listen_kwargs["utc_idle_timeout_seconds"])
        self.assertEqual(
            [
                ObservedPlaybackEventType.PLAYBACK_STATE_CHANGED,
                ObservedPlaybackEventType.POSITION_UPDATED,
                ObservedPlaybackEventType.POSITION_UPDATED,
            ],
            reporter.event_types,
        )

    def test_does_not_treat_format_burst_and_position_reset_as_stop(self):
        source = RecordingEventSource(
            [
                "@UTC 000 015 C 00:01:40",
                "@U3D 2D",
                "@UAR 16AW",
                "@UTC 000 001 C 00:00:03",
                "@UPL STOP",
            ]
        )
        orchestrator = VerbosePlaybackObservationStrategy(event_source=source)

        result = orchestrator.monitor_until_stopped(
            PlaybackMonitoringRequest(expected_duration_seconds=7760)
        )

        self.assertEqual(3, result.position_seconds)
        self.assertEqual(PlaybackMonitoringStopReason.PLAYER_IDLE, result.stop_reason)
        self.assertEqual(OppoPlaybackStatus.STOP, result.final_state.status)

    def test_finishes_when_live_position_reaches_oppo_total(self):
        source = RecordingEventSource(
            [
                "@UTC 000 010 C 02:00:00",
                "@UTC 000 024 C 02:09:16",
                "@UTC 000 000 C 00:00:00",
            ]
        )
        reporter = RecordingObservedReporter()
        orchestrator = VerbosePlaybackObservationStrategy(
            event_source=source,
            observed_event_reporter=reporter,
            oppo_total_provider=lambda: 7760,
        )

        result = orchestrator.monitor_until_stopped(PlaybackMonitoringRequest())

        self.assertEqual(7756, result.position_seconds)
        self.assertEqual(7760, result.duration_seconds)
        self.assertEqual(
            PlaybackMonitoringStopReason.NATURAL_END,
            result.stop_reason,
        )
        self.assertEqual(OppoPlaybackStatus.PLAY, result.final_state.status)
        self.assertNotIn("stopped", reporter.playback_states)
        self.assertEqual(
            [ObservedPlaybackEventType.POSITION_UPDATED],
            reporter.event_types,
        )

    def test_does_not_treat_position_reset_as_natural_end_without_expected_duration(self):
        source = RecordingEventSource(
            [
                "@UTC 000 024 C 02:09:16",
                "@UTC 000 000 C 00:00:00",
                "@UTC 000 001 C 00:00:01",
            ]
        )
        orchestrator = VerbosePlaybackObservationStrategy(event_source=source)

        result = orchestrator.monitor_until_stopped(PlaybackMonitoringRequest())

        self.assertEqual(1, result.position_seconds)
        self.assertEqual(0, result.duration_seconds)
        self.assertEqual(
            PlaybackMonitoringStopReason.EVENT_WATCHDOG_EXPIRED,
            result.stop_reason,
        )

    def test_disc_intro_and_menu_resets_do_not_finish_until_main_title_duration(self):
        source = RecordingEventSource(
            [
                "@UTC 000 001 C 00:00:23",
                "@UTC 000 000 C 00:00:00",
                "@UTC 000 002 C 00:02:27",
                "@UTC 000 000 C 00:00:00",
                "@UTC 000 002 C 00:00:01",
                "@UTC 000 003 C 02:09:08",
                "@UTC 000 000 C 00:00:00",
            ]
        )
        orchestrator = VerbosePlaybackObservationStrategy(
            event_source=source,
            oppo_total_provider=lambda: 7748,
        )

        result = orchestrator.monitor_until_stopped(PlaybackMonitoringRequest())

        self.assertEqual(7748, result.position_seconds)
        self.assertEqual(7748, result.duration_seconds)
        self.assertEqual(
            PlaybackMonitoringStopReason.NATURAL_END,
            result.stop_reason,
        )

    def test_confirms_stop_when_pending_stop_is_followed_by_media_center(self):
        source = RecordingEventSource(
            [
                "@UTC 000 001 C 00:00:06",
                "@UTC 000 000 C 00:00:00",
                "@UPL STOP",
                "@UPL MCTR",
            ]
        )
        reporter = RecordingObservedReporter()
        orchestrator = VerbosePlaybackObservationStrategy(
            event_source=source,
            observed_event_reporter=reporter,
        )

        result = orchestrator.monitor_until_stopped(PlaybackMonitoringRequest())

        self.assertEqual(6, result.position_seconds)
        self.assertEqual(PlaybackMonitoringStopReason.PLAYER_IDLE, result.stop_reason)
        self.assertEqual(OppoPlaybackStatus.MEDIA_CENTER, result.final_state.status)
        self.assertNotIn("stopped", reporter.playback_states)

    def test_reports_progress_when_no_observed_event_reporter_is_configured(self):
        source = RecordingEventSource(
            [
                "@UPL PLAY",
                "@UTC 000 015 C 00:00:01",
                "@UTC 000 015 C 00:00:02",
                "@UPL PAUS",
                "@UTC 000 015 C 00:00:03",
                "@UPL STOP",
            ]
        )
        progress = RecordingProgressReporter()
        orchestrator = VerbosePlaybackObservationStrategy(
            event_source=source,
            progress_reporter=progress,
        )

        orchestrator.monitor_until_stopped(
            PlaybackMonitoringRequest(
                progress_interval_seconds=2,
                is_muted=True,
            )
        )

        self.assertEqual(
            [
                {
                    "position_seconds": 2,
                    "duration_seconds": 0,
                    "is_paused": False,
                    "is_muted": True,
                },
            ],
            progress.calls,
        )

    def test_observed_position_update_report_is_debug_log_noise(self):
        source = RecordingEventSource(
            [
                "@UTC 000 015 C 00:00:01",
                "@UPL STOP",
            ]
        )
        reporter = RecordingObservedReporter(event_name="PositionUpdate")
        orchestrator = VerbosePlaybackObservationStrategy(
            event_source=source,
            observed_event_reporter=reporter,
        )

        with self.assertLogs(
            "home_cinema_control.playback.during.verbose_observation_strategy",
            level="DEBUG",
        ) as logs:
            orchestrator.monitor_until_stopped(PlaybackMonitoringRequest())

        self.assertTrue(
            any(
                "Observed OPPO event report result" in message
                and "event=PositionUpdate" in message
                for message in logs.output
            )
        )

    def test_returns_watchdog_result_when_event_stream_ends_without_stop(self):
        source = RecordingEventSource(["@UPL PLAY", "@UTC 000 015 C 00:00:07"])
        orchestrator = VerbosePlaybackObservationStrategy(event_source=source)

        result = orchestrator.monitor_until_stopped(
            PlaybackMonitoringRequest(event_watchdog_seconds=12)
        )

        self.assertEqual(7, result.position_seconds)
        self.assertEqual(
            PlaybackMonitoringStopReason.EVENT_WATCHDOG_EXPIRED,
            result.stop_reason,
        )
        self.assertEqual(12, source.listen_kwargs["utc_idle_timeout_seconds"])

    def test_reports_unknown_state_when_watchdog_expires_with_no_events_at_all(self):
        # A retried SVM3 attempt that observes literally nothing before its
        # own watchdog timeout must not claim PLAY/ACTIVE — that would mask a
        # still-paused session as "confirmed playing" for whoever reads this
        # result next (see DuringPlaybackOrchestrator._request_from_result).
        source = RecordingEventSource([])
        orchestrator = VerbosePlaybackObservationStrategy(event_source=source)

        result = orchestrator.monitor_until_stopped(PlaybackMonitoringRequest())

        self.assertEqual(
            PlaybackMonitoringStopReason.EVENT_WATCHDOG_EXPIRED,
            result.stop_reason,
        )
        self.assertEqual(OppoPlaybackStatus.UNKNOWN, result.final_state.status)
        self.assertEqual(OppoPlaybackCategory.UNKNOWN, result.final_state.category)


class DeferredAudioSelectorTest(unittest.TestCase):
    def test_applies_deferred_audio_selector_on_first_play_event(self):
        source = RecordingEventSource(
            ["@UPL PLAY", "@UPL PAUS", "@UPL PLAY", "@UPL STOP", "@UPL MCTR"]
        )
        orchestrator = VerbosePlaybackObservationStrategy(event_source=source)
        calls = []
        from home_cinema_control.playback.startup.models import DeviceCommandResult

        orchestrator.set_deferred_audio_selector(
            lambda: calls.append(True) or DeviceCommandResult.success("applied")
        )

        orchestrator.monitor_until_stopped(PlaybackMonitoringRequest())

        self.assertEqual(1, len(calls))

    def test_deferred_audio_selector_not_called_without_play_event(self):
        source = RecordingEventSource(["@UTC 000 015 C 00:00:05"])
        orchestrator = VerbosePlaybackObservationStrategy(event_source=source)
        calls = []
        from home_cinema_control.playback.startup.models import DeviceCommandResult

        orchestrator.set_deferred_audio_selector(
            lambda: calls.append(True) or DeviceCommandResult.success("applied")
        )

        orchestrator.monitor_until_stopped(PlaybackMonitoringRequest())

        self.assertEqual(0, len(calls))


class RecordingEventSource:
    def __init__(self, raw_events):
        self.raw_events = raw_events
        self.listen_kwargs = None

    def listen(self, **kwargs):
        self.listen_kwargs = kwargs
        for raw_event in self.raw_events:
            yield parse_verbose_event(raw_event)


class RecordingObservedReporter:
    def __init__(self, *, event_name=None):
        self.event_types = []
        self.playback_states = []
        self.event_name = event_name

    def report(self, event):
        self.event_types.append(event.event_type)
        if event.playback_state is not None:
            self.playback_states.append(event.playback_state.value)
        return type(
            "Result",
            (),
            {
                "reported": True,
                "event_name": self.event_name or event.event_type.value,
                "detail": "",
            },
        )()


class AudioTrackDeduplicationTest(unittest.TestCase):
    def test_skips_consecutive_duplicate_audio_track_events(self):
        source = RecordingEventSource(
            [
                "@UPL PLAY",
                "@UAT DD 01/02 UNK 0.0",
                "@UAT DD 01/02 UNK 0.0",  # same index — should be skipped
                "@UAT DD 02/02 UNK 0.0",  # different index — should be reported
                "@UAT DD 02/02 UNK 0.0",  # same index again — skipped
                "@UPL STOP",
            ]
        )
        reporter = RecordingObservedReporter()
        orchestrator = VerbosePlaybackObservationStrategy(
            event_source=source,
            observed_event_reporter=reporter,
        )

        orchestrator.monitor_until_stopped(PlaybackMonitoringRequest())

        audio_events = [
            t for t in reporter.event_types
            if t == ObservedPlaybackEventType.AUDIO_TRACK_CHANGED
        ]
        self.assertEqual(2, len(audio_events))

    def test_does_not_skip_audio_track_change_to_different_index(self):
        source = RecordingEventSource(
            [
                "@UAT DD 01/03 UNK 0.0",
                "@UAT DD 02/03 UNK 0.0",
                "@UAT DD 03/03 UNK 0.0",
                "@UPL STOP",
            ]
        )
        reporter = RecordingObservedReporter()
        orchestrator = VerbosePlaybackObservationStrategy(
            event_source=source,
            observed_event_reporter=reporter,
        )

        orchestrator.monitor_until_stopped(PlaybackMonitoringRequest())

        audio_events = [
            t for t in reporter.event_types
            if t == ObservedPlaybackEventType.AUDIO_TRACK_CHANGED
        ]
        self.assertEqual(3, len(audio_events))


class RecordingProgressReporter:
    def __init__(self):
        self.calls = []

    def progress(self, **kwargs):
        self.calls.append(kwargs)


if __name__ == "__main__":
    unittest.main()
