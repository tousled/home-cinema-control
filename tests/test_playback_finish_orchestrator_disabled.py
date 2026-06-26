import unittest
from unittest.mock import MagicMock

from home_cinema_control.playback.finish.orchestrator import FinishPlaybackOrchestrator
from home_cinema_control.playback.startup.models import (
    DeviceCommandResult,
    DeviceCommandStatus,
)
from home_cinema_control.playback.player_state import (
    PlayerPlaybackLifecyclePhase,
    PlayerPlaybackState,
    PlayerPlaybackStatus,
)
from home_cinema_control.playback.finish.models import PlaybackFinishRequest


def _idle_state():
    return PlayerPlaybackState(
        status=PlayerPlaybackStatus.HOME_MENU,
        lifecycle_phase=PlayerPlaybackLifecyclePhase.IDLE,
        raw_response="@OK HMN",
        ok=True,
    )


def _finish_request(*, tv_enabled, av_enabled, previous_tv_app_id="com.emby.app"):
    return PlaybackFinishRequest(
        previous_tv_app_id=previous_tv_app_id,
        position_seconds=120,
        duration_seconds=5400,
        is_paused=False,
        is_muted=False,
        media_ended=False,
        final_player_state=_idle_state(),
        tv_enabled=tv_enabled,
        av_enabled=av_enabled,
    )


def _orchestrator(*, television, av_receiver):
    stopped_reporter = MagicMock()
    stopped_reporter.stopped.return_value = None
    return FinishPlaybackOrchestrator(
        stopped_reporter=stopped_reporter,
        television=television,
        av_receiver=av_receiver,
    )


class TestFinishOrchestratorDisabled(unittest.TestCase):
    def test_tv_disabled_tv_result_is_skipped(self):
        result = _orchestrator(television=None, av_receiver=None).finish(
            _finish_request(tv_enabled=False, av_enabled=False)
        )
        self.assertEqual(DeviceCommandStatus.SKIPPED, result.tv_app_result.status)

    def test_av_disabled_av_result_is_skipped(self):
        result = _orchestrator(television=None, av_receiver=None).finish(
            _finish_request(tv_enabled=False, av_enabled=False)
        )
        self.assertEqual(DeviceCommandStatus.SKIPPED, result.av_audio_result.status)

    def test_tv_disabled_av_enabled_av_restore_runs(self):
        av = _RecordingAv()
        result = _orchestrator(television=None, av_receiver=av).finish(
            _finish_request(tv_enabled=False, av_enabled=True)
        )
        self.assertEqual(DeviceCommandStatus.SKIPPED, result.tv_app_result.status)
        self.assertEqual(DeviceCommandStatus.SUCCESS, result.av_audio_result.status)
        self.assertEqual(1, av.restore_calls)

    def test_none_television_with_tv_enabled_returns_skipped(self):
        result = _orchestrator(television=None, av_receiver=None).finish(
            _finish_request(tv_enabled=True, av_enabled=False)
        )
        self.assertEqual(DeviceCommandStatus.SKIPPED, result.tv_app_result.status)

    def test_tv_enabled_television_launch_app_called(self):
        tv = _RecordingTv()
        _orchestrator(television=tv, av_receiver=None).finish(
            _finish_request(tv_enabled=True, av_enabled=False)
        )
        self.assertEqual(1, tv.launch_calls)


class _RecordingTv:
    def __init__(self):
        self.launch_calls = 0

    def get_current_app_id(self):
        return "com.webos.app.livetv"

    def switch_to_input(self, target):
        return DeviceCommandResult.success()

    def launch_app(self, app_id=None):
        self.launch_calls += 1
        return DeviceCommandResult.success()


class _RecordingAv:
    def __init__(self):
        self.restore_calls = 0

    def power_on(self):
        return DeviceCommandResult.success()

    def switch_to_input(self, input_id):
        return DeviceCommandResult.success()

    def restore_tv_audio(self):
        self.restore_calls += 1
        return DeviceCommandResult.success()
