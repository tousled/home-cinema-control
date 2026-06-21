import unittest

from home_cinema_control.devices.oppo.playback_state import (
    OppoPlaybackCategory,
    OppoPlaybackStatus,
)
from home_cinema_control.playback.during import (
    PollingPlaybackObservationStrategy,
    PlaybackMonitoringRequest,
    PlaybackMonitoringStopReason,
)
from home_cinema_control.playback.startup.models import (
    OppoPlaybackPosition,
    OppoPlaybackState,
)


class RecordingOppoPlayback:
    def __init__(self, *, states, positions):
        self.states = list(states)
        self.positions = list(positions)
        self.state_calls = 0
        self.position_calls = 0

    def get_playback_state(self):
        self.state_calls += 1
        if not self.states:
            raise AssertionError("Unexpected extra playback-state request")
        return self.states.pop(0)

    def get_playback_position(self):
        self.position_calls += 1
        if not self.positions:
            raise AssertionError("Unexpected extra playback-position request")
        return self.positions.pop(0)


class RecordingProgressPublisher:
    def __init__(self):
        self.calls = []

    def progress(self, **kwargs):
        self.calls.append(kwargs)


class PollingPlaybackObservationStrategyTest(unittest.TestCase):
    def test_monitors_qpl_until_idle_and_preserves_last_valid_position(self):
        oppo = RecordingOppoPlayback(
            states=[
                _state(OppoPlaybackStatus.PLAY, OppoPlaybackCategory.ACTIVE),
                _state(OppoPlaybackStatus.PLAY, OppoPlaybackCategory.ACTIVE),
                _state(OppoPlaybackStatus.PLAY, OppoPlaybackCategory.ACTIVE),
                _state(OppoPlaybackStatus.MEDIA_CENTER, OppoPlaybackCategory.IDLE),
            ],
            positions=[
                OppoPlaybackPosition(current_seconds=12, total_seconds=120),
                OppoPlaybackPosition(current_seconds=0, total_seconds=0),
            ],
        )
        progress = RecordingProgressPublisher()
        orchestrator = PollingPlaybackObservationStrategy(
            oppo_playback=oppo,
            progress_reporter=progress,
            sleep=lambda seconds: None,
        )

        result = orchestrator.monitor_until_stopped(
            PlaybackMonitoringRequest(
                initial_position_seconds=0,
                progress_interval_seconds=1,
            )
        )

        self.assertEqual(12, result.position_seconds)
        self.assertEqual(120, result.duration_seconds)
        self.assertEqual(OppoPlaybackStatus.MEDIA_CENTER, result.final_state.status)
        self.assertEqual(
            PlaybackMonitoringStopReason.PLAYER_IDLE,
            result.stop_reason,
        )
        self.assertEqual(2, oppo.position_calls)
        self.assertEqual(1, len(progress.calls))
        self.assertEqual(12, progress.calls[0]["position_seconds"])

    def test_reports_progress_no_more_often_than_configured_interval(self):
        oppo = RecordingOppoPlayback(
            states=[
                _state(OppoPlaybackStatus.PLAY, OppoPlaybackCategory.ACTIVE),
                _state(OppoPlaybackStatus.PLAY, OppoPlaybackCategory.ACTIVE),
                _state(OppoPlaybackStatus.PLAY, OppoPlaybackCategory.ACTIVE),
                _state(OppoPlaybackStatus.MEDIA_CENTER, OppoPlaybackCategory.IDLE),
            ],
            positions=[
                OppoPlaybackPosition(current_seconds=1, total_seconds=120),
                OppoPlaybackPosition(current_seconds=2, total_seconds=120),
            ],
        )
        progress = RecordingProgressPublisher()
        orchestrator = PollingPlaybackObservationStrategy(
            oppo_playback=oppo,
            progress_reporter=progress,
            sleep=lambda seconds: None,
        )

        orchestrator.monitor_until_stopped(
            PlaybackMonitoringRequest(
                initial_position_seconds=0,
                poll_interval_seconds=1,
                progress_interval_seconds=10,
            )
        )

        self.assertEqual([], progress.calls)

    def test_keeps_initial_position_when_no_valid_position_is_reported(self):
        oppo = RecordingOppoPlayback(
            states=[
                _state(OppoPlaybackStatus.PLAY, OppoPlaybackCategory.ACTIVE),
                _state(OppoPlaybackStatus.PLAY, OppoPlaybackCategory.ACTIVE),
                _state(OppoPlaybackStatus.MEDIA_CENTER, OppoPlaybackCategory.IDLE),
            ],
            positions=[
                OppoPlaybackPosition(current_seconds=0, total_seconds=0),
            ],
        )
        orchestrator = PollingPlaybackObservationStrategy(
            oppo_playback=oppo,
            sleep=lambda seconds: None,
        )

        result = orchestrator.monitor_until_stopped(
            PlaybackMonitoringRequest(initial_position_seconds=42)
        )

        self.assertEqual(42, result.position_seconds)
        self.assertEqual(0, result.duration_seconds)

    def test_keeps_monitoring_when_paused_playback_enters_screen_saver(self):
        oppo = RecordingOppoPlayback(
            states=[
                _state(OppoPlaybackStatus.PAUSE, OppoPlaybackCategory.ACTIVE),
                _state(OppoPlaybackStatus.SCREEN_SAVER, OppoPlaybackCategory.IDLE),
                _state(OppoPlaybackStatus.SCREEN_SAVER, OppoPlaybackCategory.IDLE),
                _state(OppoPlaybackStatus.PLAY, OppoPlaybackCategory.ACTIVE),
                _state(OppoPlaybackStatus.MEDIA_CENTER, OppoPlaybackCategory.IDLE),
            ],
            positions=[
                OppoPlaybackPosition(current_seconds=45, total_seconds=120),
            ],
        )
        progress = RecordingProgressPublisher()
        orchestrator = PollingPlaybackObservationStrategy(
            oppo_playback=oppo,
            progress_reporter=progress,
            sleep=lambda seconds: None,
        )

        result = orchestrator.monitor_until_stopped(
            PlaybackMonitoringRequest(
                initial_position_seconds=42,
                progress_interval_seconds=1,
            )
        )

        self.assertEqual(OppoPlaybackStatus.MEDIA_CENTER, result.final_state.status)
        self.assertEqual(45, result.position_seconds)
        self.assertEqual(120, result.duration_seconds)
        self.assertEqual(1, oppo.position_calls)

    def test_keeps_monitoring_when_playing_jumps_directly_to_screen_saver(self):
        # OPPO cannot enter screen saver from active playback — the bridge may
        # miss the PAUSE poll between PLAY and SCREEN_SAVER
        oppo = RecordingOppoPlayback(
            states=[
                _state(OppoPlaybackStatus.PLAY, OppoPlaybackCategory.ACTIVE),
                _state(OppoPlaybackStatus.SCREEN_SAVER, OppoPlaybackCategory.IDLE),
                _state(OppoPlaybackStatus.SCREEN_SAVER, OppoPlaybackCategory.IDLE),
                _state(OppoPlaybackStatus.PLAY, OppoPlaybackCategory.ACTIVE),
                _state(OppoPlaybackStatus.MEDIA_CENTER, OppoPlaybackCategory.IDLE),
            ],
            positions=[
                OppoPlaybackPosition(current_seconds=60, total_seconds=120),
            ],
        )
        progress = RecordingProgressPublisher()
        orchestrator = PollingPlaybackObservationStrategy(
            oppo_playback=oppo,
            progress_reporter=progress,
            sleep=lambda seconds: None,
        )

        result = orchestrator.monitor_until_stopped(
            PlaybackMonitoringRequest(
                initial_position_seconds=55,
                progress_interval_seconds=1,
            )
        )

        self.assertEqual(OppoPlaybackStatus.MEDIA_CENTER, result.final_state.status)
        self.assertEqual(60, result.position_seconds)

    def test_reports_last_known_paused_position_during_paused_screen_saver(self):
        oppo = RecordingOppoPlayback(
            states=[
                _state(OppoPlaybackStatus.PAUSE, OppoPlaybackCategory.ACTIVE),
                _state(OppoPlaybackStatus.PAUSE, OppoPlaybackCategory.ACTIVE),
                _state(OppoPlaybackStatus.SCREEN_SAVER, OppoPlaybackCategory.IDLE),
                _state(OppoPlaybackStatus.HOME_MENU, OppoPlaybackCategory.IDLE),
            ],
            positions=[
                OppoPlaybackPosition(current_seconds=100, total_seconds=200),
            ],
        )
        progress = RecordingProgressPublisher()
        orchestrator = PollingPlaybackObservationStrategy(
            oppo_playback=oppo,
            progress_reporter=progress,
            sleep=lambda seconds: None,
        )

        orchestrator.monitor_until_stopped(
            PlaybackMonitoringRequest(
                initial_position_seconds=90,
                poll_interval_seconds=1,
                progress_interval_seconds=1,
            )
        )

        self.assertEqual(2, len(progress.calls))
        self.assertEqual(100, progress.calls[0]["position_seconds"])
        self.assertTrue(progress.calls[0]["is_paused"])
        self.assertEqual(100, progress.calls[1]["position_seconds"])
        self.assertTrue(progress.calls[1]["is_paused"])

    def test_seeds_last_active_state_from_request_on_a_cold_start_in_screen_saver(self):
        # This is the case after an SVM3 watchdog timeout: this is a fresh
        # monitor_until_stopped() call, and the OPPO is already sitting in
        # SCREEN_SAVER by the time it starts (that's exactly why SVM3 went
        # quiet). Without the request hint, last_active_state would be None
        # and the carve-out below could never engage.
        oppo = RecordingOppoPlayback(
            states=[
                _state(OppoPlaybackStatus.SCREEN_SAVER, OppoPlaybackCategory.IDLE),
                _state(OppoPlaybackStatus.SCREEN_SAVER, OppoPlaybackCategory.IDLE),
                _state(OppoPlaybackStatus.PLAY, OppoPlaybackCategory.ACTIVE),
                _state(OppoPlaybackStatus.MEDIA_CENTER, OppoPlaybackCategory.IDLE),
            ],
            positions=[],
        )
        orchestrator = PollingPlaybackObservationStrategy(
            oppo_playback=oppo,
            sleep=lambda seconds: None,
        )

        result = orchestrator.monitor_until_stopped(
            PlaybackMonitoringRequest(
                initial_position_seconds=42,
                last_active_state=_state(
                    OppoPlaybackStatus.PAUSE, OppoPlaybackCategory.ACTIVE
                ),
            )
        )

        self.assertEqual(OppoPlaybackStatus.MEDIA_CENTER, result.final_state.status)
        self.assertEqual(42, result.position_seconds)

    def test_cold_start_without_a_paused_hint_reports_idle_immediately(self):
        oppo = RecordingOppoPlayback(
            states=[
                _state(OppoPlaybackStatus.SCREEN_SAVER, OppoPlaybackCategory.IDLE),
            ],
            positions=[],
        )
        orchestrator = PollingPlaybackObservationStrategy(
            oppo_playback=oppo,
            sleep=lambda seconds: None,
        )

        result = orchestrator.monitor_until_stopped(
            PlaybackMonitoringRequest(initial_position_seconds=42)
        )

        self.assertEqual(
            PlaybackMonitoringStopReason.PLAYER_IDLE,
            result.stop_reason,
        )
        self.assertEqual(OppoPlaybackStatus.SCREEN_SAVER, result.final_state.status)

    def test_stops_after_bounded_transition_grace(self):
        oppo = RecordingOppoPlayback(
            states=[
                _state(OppoPlaybackStatus.STOP, OppoPlaybackCategory.TRANSITION),
                _state(OppoPlaybackStatus.STOP, OppoPlaybackCategory.TRANSITION),
                _state(OppoPlaybackStatus.STOP, OppoPlaybackCategory.TRANSITION),
                _state(OppoPlaybackStatus.STOP, OppoPlaybackCategory.TRANSITION),
            ],
            positions=[],
        )
        orchestrator = PollingPlaybackObservationStrategy(
            oppo_playback=oppo,
            sleep=lambda seconds: None,
        )

        result = orchestrator.monitor_until_stopped(
            PlaybackMonitoringRequest(
                initial_position_seconds=42,
                max_transition_polls=3,
            )
        )

        self.assertEqual(42, result.position_seconds)
        self.assertEqual(OppoPlaybackStatus.STOP, result.final_state.status)
        self.assertEqual(
            PlaybackMonitoringStopReason.TRANSITION_GRACE_EXCEEDED,
            result.stop_reason,
        )
        self.assertEqual(0, oppo.position_calls)

    def test_keeps_monitoring_after_transient_unknown_state_when_playback_was_active(self):
        oppo = RecordingOppoPlayback(
            states=[
                _state(OppoPlaybackStatus.PLAY, OppoPlaybackCategory.ACTIVE),
                _state(OppoPlaybackStatus.PLAY, OppoPlaybackCategory.ACTIVE),
                _state(OppoPlaybackStatus.UNKNOWN, OppoPlaybackCategory.UNKNOWN),
                _state(OppoPlaybackStatus.PLAY, OppoPlaybackCategory.ACTIVE),
                _state(OppoPlaybackStatus.MEDIA_CENTER, OppoPlaybackCategory.IDLE),
            ],
            positions=[
                OppoPlaybackPosition(current_seconds=10, total_seconds=120),
                OppoPlaybackPosition(current_seconds=20, total_seconds=120),
            ],
        )
        progress = RecordingProgressPublisher()
        orchestrator = PollingPlaybackObservationStrategy(
            oppo_playback=oppo,
            progress_reporter=progress,
            sleep=lambda seconds: None,
        )

        result = orchestrator.monitor_until_stopped(
            PlaybackMonitoringRequest(
                initial_position_seconds=0,
                progress_interval_seconds=1,
            )
        )

        self.assertEqual(OppoPlaybackStatus.MEDIA_CENTER, result.final_state.status)
        self.assertEqual(20, result.position_seconds)
        self.assertEqual(120, result.duration_seconds)
        self.assertEqual(
            PlaybackMonitoringStopReason.PLAYER_IDLE,
            result.stop_reason,
        )
        self.assertEqual(2, oppo.position_calls)

    def test_stops_after_confirmed_natural_end_even_when_qpl_remains_playing(self):
        oppo = RecordingOppoPlayback(
            states=[
                _state(OppoPlaybackStatus.PLAY, OppoPlaybackCategory.ACTIVE),
                _state(OppoPlaybackStatus.PLAY, OppoPlaybackCategory.ACTIVE),
                _state(OppoPlaybackStatus.PLAY, OppoPlaybackCategory.ACTIVE),
                _state(OppoPlaybackStatus.PLAY, OppoPlaybackCategory.ACTIVE),
            ],
            positions=[
                OppoPlaybackPosition(current_seconds=3528, total_seconds=3529),
                OppoPlaybackPosition(current_seconds=3533, total_seconds=3529),
                OppoPlaybackPosition(current_seconds=3533, total_seconds=3529),
            ],
        )
        progress = RecordingProgressPublisher()
        orchestrator = PollingPlaybackObservationStrategy(
            oppo_playback=oppo,
            progress_reporter=progress,
            sleep=lambda seconds: None,
        )

        result = orchestrator.monitor_until_stopped(
            PlaybackMonitoringRequest(
                expected_duration_seconds=3529,
                progress_interval_seconds=1,
                max_end_of_media_polls=2,
            )
        )

        self.assertEqual(3529, result.position_seconds)
        self.assertEqual(3529, result.duration_seconds)
        self.assertEqual(OppoPlaybackStatus.PLAY, result.final_state.status)
        self.assertEqual(
            PlaybackMonitoringStopReason.NATURAL_END,
            result.stop_reason,
        )
        self.assertEqual(3, oppo.position_calls)
        self.assertEqual(3529, progress.calls[-1]["position_seconds"])

    def test_does_not_stop_at_menu_end_without_expected_duration(self):
        oppo = RecordingOppoPlayback(
            states=[
                _state(OppoPlaybackStatus.PLAY, OppoPlaybackCategory.ACTIVE),
                _state(OppoPlaybackStatus.PLAY, OppoPlaybackCategory.ACTIVE),
                _state(OppoPlaybackStatus.PLAY, OppoPlaybackCategory.ACTIVE),
                _state(OppoPlaybackStatus.PLAY, OppoPlaybackCategory.ACTIVE),
                _state(OppoPlaybackStatus.HOME_MENU, OppoPlaybackCategory.IDLE),
            ],
            positions=[
                OppoPlaybackPosition(current_seconds=145, total_seconds=145),
                OppoPlaybackPosition(current_seconds=145, total_seconds=145),
                OppoPlaybackPosition(current_seconds=145, total_seconds=145),
            ],
        )
        orchestrator = PollingPlaybackObservationStrategy(
            oppo_playback=oppo,
            sleep=lambda seconds: None,
        )

        result = orchestrator.monitor_until_stopped(
            PlaybackMonitoringRequest(
                expected_duration_seconds=0,
                progress_interval_seconds=1,
                max_end_of_media_polls=2,
            )
        )

        self.assertEqual(PlaybackMonitoringStopReason.PLAYER_IDLE, result.stop_reason)
        self.assertEqual(OppoPlaybackStatus.HOME_MENU, result.final_state.status)
        self.assertEqual(3, oppo.position_calls)

    def test_stops_when_polling_detects_next_file_after_expected_media_end(self):
        oppo = RecordingOppoPlayback(
            states=[
                _state(OppoPlaybackStatus.PLAY, OppoPlaybackCategory.ACTIVE),
                _state(OppoPlaybackStatus.PLAY, OppoPlaybackCategory.ACTIVE),
                _state(OppoPlaybackStatus.PLAY, OppoPlaybackCategory.ACTIVE),
            ],
            positions=[
                OppoPlaybackPosition(current_seconds=7754, total_seconds=7756),
                OppoPlaybackPosition(current_seconds=6, total_seconds=5813),
            ],
        )
        progress = RecordingProgressPublisher()
        orchestrator = PollingPlaybackObservationStrategy(
            oppo_playback=oppo,
            progress_reporter=progress,
            sleep=lambda seconds: None,
        )

        result = orchestrator.monitor_until_stopped(
            PlaybackMonitoringRequest(
                expected_duration_seconds=7756,
                progress_interval_seconds=1,
            )
        )

        self.assertEqual(7754, result.position_seconds)
        self.assertEqual(7756, result.duration_seconds)
        self.assertEqual(PlaybackMonitoringStopReason.NATURAL_END, result.stop_reason)
        self.assertEqual(2, oppo.position_calls)
        self.assertEqual([7754], [call["position_seconds"] for call in progress.calls])

    def test_stops_at_transition_when_expected_media_end_was_reached(self):
        oppo = RecordingOppoPlayback(
            states=[
                _state(OppoPlaybackStatus.PLAY, OppoPlaybackCategory.ACTIVE),
                _state(OppoPlaybackStatus.PLAY, OppoPlaybackCategory.ACTIVE),
                _state(OppoPlaybackStatus.STOP, OppoPlaybackCategory.TRANSITION),
            ],
            positions=[
                OppoPlaybackPosition(current_seconds=7751, total_seconds=7756),
            ],
        )
        progress = RecordingProgressPublisher()
        orchestrator = PollingPlaybackObservationStrategy(
            oppo_playback=oppo,
            progress_reporter=progress,
            sleep=lambda seconds: None,
        )

        result = orchestrator.monitor_until_stopped(
            PlaybackMonitoringRequest(
                expected_duration_seconds=7756,
                progress_interval_seconds=1,
            )
        )

        self.assertEqual(7751, result.position_seconds)
        self.assertEqual(7756, result.duration_seconds)
        self.assertEqual(OppoPlaybackStatus.STOP, result.final_state.status)
        self.assertEqual(PlaybackMonitoringStopReason.NATURAL_END, result.stop_reason)
        self.assertEqual(1, oppo.position_calls)

    def test_returns_observation_window_expired_when_timeout_reaches_active_playback(self):
        oppo = RecordingOppoPlayback(
            states=[
                _state(OppoPlaybackStatus.PLAY, OppoPlaybackCategory.ACTIVE),
                _state(OppoPlaybackStatus.PLAY, OppoPlaybackCategory.ACTIVE),
                _state(OppoPlaybackStatus.PLAY, OppoPlaybackCategory.ACTIVE),
                _state(OppoPlaybackStatus.PLAY, OppoPlaybackCategory.ACTIVE),
            ],
            positions=[
                OppoPlaybackPosition(current_seconds=10, total_seconds=120),
                OppoPlaybackPosition(current_seconds=20, total_seconds=120),
            ],
        )
        progress = RecordingProgressPublisher()
        orchestrator = PollingPlaybackObservationStrategy(
            oppo_playback=oppo,
            progress_reporter=progress,
            sleep=lambda seconds: None,
        )

        result = orchestrator.monitor_until_stopped(
            PlaybackMonitoringRequest(
                poll_interval_seconds=1,
                progress_interval_seconds=1,
                monitoring_timeout_seconds=2,
            )
        )

        self.assertEqual(20, result.position_seconds)
        self.assertEqual(120, result.duration_seconds)
        self.assertEqual(
            PlaybackMonitoringStopReason.OBSERVATION_WINDOW_EXPIRED,
            result.stop_reason,
        )
        self.assertEqual(2, oppo.position_calls)

    def test_observation_window_expires_in_menu_without_expected_duration(self):
        oppo = RecordingOppoPlayback(
            states=[
                _state(OppoPlaybackStatus.PLAY, OppoPlaybackCategory.ACTIVE),
                _state(OppoPlaybackStatus.PLAY, OppoPlaybackCategory.ACTIVE),
                _state(OppoPlaybackStatus.PLAY, OppoPlaybackCategory.ACTIVE),
                _state(OppoPlaybackStatus.PLAY, OppoPlaybackCategory.ACTIVE),
            ],
            positions=[
                OppoPlaybackPosition(current_seconds=145, total_seconds=145),
                OppoPlaybackPosition(current_seconds=145, total_seconds=145),
            ],
        )
        orchestrator = PollingPlaybackObservationStrategy(
            oppo_playback=oppo,
            sleep=lambda seconds: None,
        )

        result = orchestrator.monitor_until_stopped(
            PlaybackMonitoringRequest(
                expected_duration_seconds=0,
                poll_interval_seconds=1,
                progress_interval_seconds=1,
                monitoring_timeout_seconds=2,
                max_end_of_media_polls=2,
            )
        )

        self.assertEqual(
            PlaybackMonitoringStopReason.OBSERVATION_WINDOW_EXPIRED,
            result.stop_reason,
        )
        self.assertEqual(145, result.position_seconds)
        self.assertEqual(2, oppo.position_calls)


def _state(status, category):
    return OppoPlaybackState(
        status=status,
        category=category,
        raw_response=f"@OK {status.value}",
        ok=True,
    )


if __name__ == "__main__":
    unittest.main()
