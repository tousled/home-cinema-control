import unittest

from home_cinema_control.playback.error_handling import (
    PlaybackErrorHandler,
    PlaybackErrorRecoveryRequest,
)
from home_cinema_control.playback.startup.models import (
    DeviceCommandResult,
    DeviceCommandStatus,
)


def _request(*, tv_enabled, av_enabled):
    return PlaybackErrorRecoveryRequest(
        reason="test error",
        previous_tv_app_id="com.emby.app",
        tv_enabled=tv_enabled,
        av_enabled=av_enabled,
    )


def _handler(*, television, av_receiver):
    return PlaybackErrorHandler(television=television, av_receiver=av_receiver)


class TestErrorHandlerDisabled(unittest.TestCase):
    def test_tv_disabled_tv_result_is_skipped(self):
        result = _handler(television=None, av_receiver=None).recover(
            _request(tv_enabled=False, av_enabled=False)
        )
        self.assertEqual(DeviceCommandStatus.SKIPPED, result.tv_app_result.status)

    def test_av_disabled_av_result_is_skipped(self):
        result = _handler(television=None, av_receiver=None).recover(
            _request(tv_enabled=False, av_enabled=False)
        )
        self.assertEqual(DeviceCommandStatus.SKIPPED, result.av_audio_result.status)

    def test_tv_disabled_av_enabled_av_restore_runs(self):
        av = _RecordingAv()
        result = _handler(television=None, av_receiver=av).recover(
            _request(tv_enabled=False, av_enabled=True)
        )
        self.assertEqual(DeviceCommandStatus.SKIPPED, result.tv_app_result.status)
        self.assertEqual(DeviceCommandStatus.SUCCESS, result.av_audio_result.status)
        self.assertEqual(1, av.restore_calls)

    def test_none_television_with_tv_enabled_returns_skipped(self):
        """None adapter with tv_enabled=True should not crash; returns skipped."""
        result = _handler(television=None, av_receiver=None).recover(
            _request(tv_enabled=True, av_enabled=False)
        )
        self.assertEqual(DeviceCommandStatus.SKIPPED, result.tv_app_result.status)

    def test_tv_enabled_with_adapter_calls_launch_app(self):
        tv = _RecordingTv()
        _handler(television=tv, av_receiver=None).recover(
            _request(tv_enabled=True, av_enabled=False)
        )
        self.assertEqual(1, tv.launch_calls)

    def test_both_disabled_recovery_is_successful(self):
        result = _handler(television=None, av_receiver=None).recover(
            _request(tv_enabled=False, av_enabled=False)
        )
        self.assertTrue(result.successful)


class _RecordingTv:
    def __init__(self):
        self.launch_calls = 0

    def get_current_app_id(self):
        return None

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
