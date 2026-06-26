import unittest

from home_cinema_control.playback.player_state import (
    PlayerPlaybackLifecyclePhase,
    PlayerPlaybackState,
    PlayerPlaybackStatus,
)
from home_cinema_control.playback.finish import (
    FinishPlaybackOrchestrator,
    PlaybackFinishRequest,
)
from home_cinema_control.playback.startup.models import (
    DeviceCommandResult,
    DeviceCommandStatus,
)


class RecordingStopReporter:
    def __init__(self):
        self.calls = []

    def stopped(self, **kwargs):
        self.calls.append(kwargs)
        return "stopped-response"


class RecordingTelevision:
    def __init__(self):
        self.returned_app_ids = []

    def launch_app(self, app_id=None):
        self.returned_app_ids.append(app_id)
        return DeviceCommandResult.success("tv returned")


class RecordingAvReceiver:
    def __init__(self):
        self.restore_calls = 0

    def restore_tv_audio(self):
        self.restore_calls += 1
        return DeviceCommandResult.success("av restored")


class RecordingOppoPlayback:
    def __init__(self, states, stop_result=None, cleanup_result=None):
        self.states = list(states)
        self.state_calls = 0
        self.stop_calls = 0
        self.cleanup_calls = 0
        self.stop_result = stop_result or DeviceCommandResult.success("stopped")
        self.cleanup_result = cleanup_result or DeviceCommandResult.skipped(
            "no cleanup"
        )

    def get_playback_state(self):
        self.state_calls += 1
        if not self.states:
            raise AssertionError("Unexpected extra playback-state request")
        next_state = self.states.pop(0)
        if isinstance(next_state, Exception):
            raise next_state
        return next_state

    def stop(self):
        self.stop_calls += 1
        return self.stop_result

    def cleanup_after_playback_finish(self):
        self.cleanup_calls += 1
        return self.cleanup_result


class FinishPlaybackOrchestratorTest(unittest.TestCase):
    def test_reports_stop_and_restores_outputs_after_idle_confirmation(self):
        stop_reporter = RecordingStopReporter()
        television = RecordingTelevision()
        av_receiver = RecordingAvReceiver()
        oppo = RecordingOppoPlayback(
            [
                _state(PlayerPlaybackStatus.OPEN, PlayerPlaybackLifecyclePhase.TRANSITION),
                _state(PlayerPlaybackStatus.MEDIA_CENTER, PlayerPlaybackLifecyclePhase.IDLE),
            ]
        )
        orchestrator = FinishPlaybackOrchestrator(
            stopped_reporter=stop_reporter,
            television=television,
            av_receiver=av_receiver,
            media_player=oppo,
            sleep=lambda seconds: None,
        )

        result = orchestrator.finish(
            PlaybackFinishRequest(
                position_seconds=53,
                duration_seconds=120,
                final_player_state=_state(
                    PlayerPlaybackStatus.STOP,
                    PlayerPlaybackLifecyclePhase.TRANSITION,
                ),
                previous_tv_app_id="com.emby.app",
            )
        )

        self.assertTrue(result.successful)
        self.assertEqual(DeviceCommandStatus.SUCCESS, result.player_idle_result.status)
        self.assertEqual(2, oppo.state_calls)
        self.assertEqual(
            PlayerPlaybackStatus.MEDIA_CENTER,
            result.final_player_state.status,
        )
        self.assertEqual(
            {
                "position_seconds": 53,
                "duration_seconds": 120,
                "is_paused": False,
                "is_muted": False,
                "played": False,
            },
            stop_reporter.calls[0],
        )
        self.assertEqual(["com.emby.app"], television.returned_app_ids)
        self.assertEqual(1, av_receiver.restore_calls)

    def test_does_not_poll_oppo_when_final_state_is_already_idle(self):
        stop_reporter = RecordingStopReporter()
        oppo = RecordingOppoPlayback([])
        orchestrator = FinishPlaybackOrchestrator(
            stopped_reporter=stop_reporter,
            television=RecordingTelevision(),
            av_receiver=RecordingAvReceiver(),
            media_player=oppo,
            sleep=lambda seconds: None,
        )

        result = orchestrator.finish(
            PlaybackFinishRequest(
                position_seconds=10,
                duration_seconds=100,
                final_player_state=_state(
                    PlayerPlaybackStatus.HOME_MENU,
                    PlayerPlaybackLifecyclePhase.IDLE,
                ),
                previous_tv_app_id="com.emby.app",
            )
        )

        self.assertTrue(result.successful)
        self.assertEqual(DeviceCommandStatus.SUCCESS, result.player_idle_result.status)
        self.assertEqual(0, oppo.state_calls)
        self.assertEqual(1, oppo.cleanup_calls)

    def test_closes_player_after_natural_end_even_when_player_is_transitioning(self):
        stop_reporter = RecordingStopReporter()
        oppo = RecordingOppoPlayback(
            [
                _state(PlayerPlaybackStatus.HOME_MENU, PlayerPlaybackLifecyclePhase.IDLE),
            ],
        )
        orchestrator = FinishPlaybackOrchestrator(
            stopped_reporter=stop_reporter,
            television=RecordingTelevision(),
            av_receiver=RecordingAvReceiver(),
            media_player=oppo,
            sleep=lambda seconds: None,
        )

        result = orchestrator.finish(
            PlaybackFinishRequest(
                position_seconds=7751,
                duration_seconds=7756,
                final_player_state=_state(
                    PlayerPlaybackStatus.STOP,
                    PlayerPlaybackLifecyclePhase.TRANSITION,
                ),
                previous_tv_app_id="com.emby.app",
                media_ended=True,
            )
        )

        self.assertTrue(result.successful)
        self.assertEqual(1, oppo.stop_calls)
        self.assertEqual(1, oppo.state_calls)

    def test_runs_player_finish_cleanup_when_final_state_is_already_idle(self):
        stop_reporter = RecordingStopReporter()
        oppo = RecordingOppoPlayback(
            [],
            cleanup_result=DeviceCommandResult.success("verbose disabled"),
        )
        orchestrator = FinishPlaybackOrchestrator(
            stopped_reporter=stop_reporter,
            television=RecordingTelevision(),
            av_receiver=RecordingAvReceiver(),
            media_player=oppo,
            sleep=lambda seconds: None,
        )

        result = orchestrator.finish(
            PlaybackFinishRequest(
                position_seconds=10,
                duration_seconds=100,
                final_player_state=_state(
                    PlayerPlaybackStatus.HOME_MENU,
                    PlayerPlaybackLifecyclePhase.IDLE,
                ),
                previous_tv_app_id="com.emby.app",
            )
        )

        self.assertTrue(result.successful)
        self.assertEqual(1, oppo.cleanup_calls)
        self.assertIn("verbose disabled", result.player_idle_result.detail)

    def test_reports_unsuccessful_finish_when_player_cleanup_fails(self):
        stop_reporter = RecordingStopReporter()
        oppo = RecordingOppoPlayback(
            [],
            cleanup_result=DeviceCommandResult.failed("svm restore failed"),
        )
        orchestrator = FinishPlaybackOrchestrator(
            stopped_reporter=stop_reporter,
            television=RecordingTelevision(),
            av_receiver=RecordingAvReceiver(),
            media_player=oppo,
            sleep=lambda seconds: None,
        )

        result = orchestrator.finish(
            PlaybackFinishRequest(
                position_seconds=10,
                duration_seconds=100,
                final_player_state=_state(
                    PlayerPlaybackStatus.HOME_MENU,
                    PlayerPlaybackLifecyclePhase.IDLE,
                ),
                previous_tv_app_id="com.emby.app",
            )
        )

        self.assertFalse(result.successful)
        self.assertEqual(DeviceCommandStatus.FAILED, result.player_idle_result.status)
        self.assertEqual("svm restore failed", result.player_idle_result.detail)

    def test_skips_tv_and_av_restore_when_final_state_is_screen_saver(self):
        # Defense in depth: a SCREEN_SAVER final state means monitoring gave
        # up while the OPPO was idle-from-the-screen-saver's-perspective, not
        # that the user actually stopped (see the polling carve-out in
        # polling_observation_strategy.py). Restoring the room here would
        # interrupt a session that is, in practice, still paused.
        stop_reporter = RecordingStopReporter()
        television = RecordingTelevision()
        av_receiver = RecordingAvReceiver()
        orchestrator = FinishPlaybackOrchestrator(
            stopped_reporter=stop_reporter,
            television=television,
            av_receiver=av_receiver,
            media_player=RecordingOppoPlayback([]),
            sleep=lambda seconds: None,
        )

        result = orchestrator.finish(
            PlaybackFinishRequest(
                position_seconds=53,
                duration_seconds=120,
                final_player_state=_state(
                    PlayerPlaybackStatus.SCREEN_SAVER,
                    PlayerPlaybackLifecyclePhase.IDLE,
                ),
                previous_tv_app_id="com.emby.app",
            )
        )

        self.assertEqual(DeviceCommandStatus.SKIPPED, result.tv_app_result.status)
        self.assertEqual(DeviceCommandStatus.SKIPPED, result.av_audio_result.status)
        self.assertEqual([], television.returned_app_ids)
        self.assertEqual(0, av_receiver.restore_calls)

    def test_skips_disabled_outputs(self):
        stop_reporter = RecordingStopReporter()
        television = RecordingTelevision()
        av_receiver = RecordingAvReceiver()
        orchestrator = FinishPlaybackOrchestrator(
            stopped_reporter=stop_reporter,
            television=television,
            av_receiver=av_receiver,
            sleep=lambda seconds: None,
        )

        result = orchestrator.finish(
            PlaybackFinishRequest(
                position_seconds=10,
                duration_seconds=100,
                final_player_state=_state(
                    PlayerPlaybackStatus.HOME_MENU,
                    PlayerPlaybackLifecyclePhase.IDLE,
                ),
                previous_tv_app_id="com.emby.app",
                tv_enabled=False,
                av_enabled=False,
            )
        )

        self.assertEqual(DeviceCommandStatus.SKIPPED, result.tv_app_result.status)
        self.assertEqual(DeviceCommandStatus.SKIPPED, result.av_audio_result.status)
        self.assertEqual(DeviceCommandStatus.SUCCESS, result.player_idle_result.status)
        self.assertEqual([], television.returned_app_ids)
        self.assertEqual(0, av_receiver.restore_calls)

    def test_reports_unsuccessful_finish_when_idle_confirmation_fails(self):
        stop_reporter = RecordingStopReporter()
        television = RecordingTelevision()
        orchestrator = FinishPlaybackOrchestrator(
            stopped_reporter=stop_reporter,
            television=television,
            av_receiver=RecordingAvReceiver(),
            media_player=RecordingOppoPlayback([TimeoutError("qpl timeout")]),
            sleep=lambda seconds: None,
        )

        result = orchestrator.finish(
            PlaybackFinishRequest(
                position_seconds=10,
                duration_seconds=100,
                final_player_state=_state(
                    PlayerPlaybackStatus.OPEN,
                    PlayerPlaybackLifecyclePhase.TRANSITION,
                ),
                previous_tv_app_id="com.emby.app",
            )
        )

        self.assertFalse(result.successful)
        self.assertEqual(DeviceCommandStatus.FAILED, result.player_idle_result.status)
        self.assertEqual(1, len(stop_reporter.calls))
        self.assertEqual(["com.emby.app"], television.returned_app_ids)

    def test_reports_unsuccessful_finish_when_oppo_never_reaches_idle(self):
        stop_reporter = RecordingStopReporter()
        orchestrator = FinishPlaybackOrchestrator(
            stopped_reporter=stop_reporter,
            television=RecordingTelevision(),
            av_receiver=RecordingAvReceiver(),
            media_player=RecordingOppoPlayback(
                [
                    _state(PlayerPlaybackStatus.OPEN, PlayerPlaybackLifecyclePhase.TRANSITION),
                    _state(PlayerPlaybackStatus.OPEN, PlayerPlaybackLifecyclePhase.TRANSITION),
                ]
            ),
            sleep=lambda seconds: None,
        )

        result = orchestrator.finish(
            PlaybackFinishRequest(
                position_seconds=10,
                duration_seconds=100,
                final_player_state=_state(
                    PlayerPlaybackStatus.OPEN,
                    PlayerPlaybackLifecyclePhase.TRANSITION,
                ),
                previous_tv_app_id="com.emby.app",
                max_idle_confirmation_polls=2,
            )
        )

        self.assertFalse(result.successful)
        self.assertEqual(DeviceCommandStatus.FAILED, result.player_idle_result.status)
        self.assertEqual(1, len(stop_reporter.calls))

    def test_closes_active_player_after_natural_media_end_before_idle_confirmation(self):
        stop_reporter = RecordingStopReporter()
        oppo = RecordingOppoPlayback(
            [_state(PlayerPlaybackStatus.HOME_MENU, PlayerPlaybackLifecyclePhase.IDLE)]
        )
        orchestrator = FinishPlaybackOrchestrator(
            stopped_reporter=stop_reporter,
            television=RecordingTelevision(),
            av_receiver=RecordingAvReceiver(),
            media_player=oppo,
            sleep=lambda seconds: None,
        )

        result = orchestrator.finish(
            PlaybackFinishRequest(
                position_seconds=3529,
                duration_seconds=3529,
                final_player_state=_state(
                    PlayerPlaybackStatus.PLAY,
                    PlayerPlaybackLifecyclePhase.ACTIVE,
                ),
                previous_tv_app_id="com.emby.app",
                media_ended=True,
                played=True,
            )
        )

        self.assertTrue(result.successful)
        self.assertEqual(1, oppo.stop_calls)
        self.assertEqual(1, oppo.state_calls)
        self.assertEqual(PlayerPlaybackStatus.HOME_MENU, result.final_player_state.status)
        self.assertEqual(3529, stop_reporter.calls[0]["position_seconds"])
        self.assertTrue(stop_reporter.calls[0]["played"])


def _state(status, lifecycle_phase):
    return PlayerPlaybackState(
        status=status,
        lifecycle_phase=lifecycle_phase,
        raw_response=f"@OK {status.value}",
        ok=True,
    )


if __name__ == "__main__":
    unittest.main()
