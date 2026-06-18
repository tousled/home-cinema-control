import unittest

from home_cinema_control.devices.tv.models import TvInputTarget
from home_cinema_control.playback.startup.models import (
    DeviceCommandResult,
    DeviceCommandStatus,
    PlaybackOutputSwitchRequest,
)
from home_cinema_control.playback.startup.orchestrator import (
    PlaybackStartupOrchestrator,
)


def _request(*, tv_enabled, av_enabled, av_input_id="HDMI_1"):
    return PlaybackOutputSwitchRequest(
        tv_input=TvInputTarget(input_id="HDMI_3"),
        av_input_id=av_input_id,
        tv_enabled=tv_enabled,
        av_enabled=av_enabled,
    )


def _orchestrator(*, television, av_receiver):
    return PlaybackStartupOrchestrator(
        television=television,
        av_receiver=av_receiver,
        oppo_playback=_UnusedOppoPlayback(),
    )


class TestDisabledMatrix(unittest.TestCase):
    # tv=False, av=False ─────────────────────────────────────────────────────

    def test_both_disabled_all_results_are_skipped(self):
        tv = _RecordingTv()
        av = _RecordingAv()
        result = _orchestrator(television=None, av_receiver=None).switch_playback_output_to_oppo(
            _request(tv_enabled=False, av_enabled=False)
        )
        self.assertEqual(DeviceCommandStatus.SKIPPED, result.tv_input_result.status)
        self.assertEqual(DeviceCommandStatus.SKIPPED, result.av_power_result.status)
        self.assertEqual(DeviceCommandStatus.SKIPPED, result.av_input_result.status)

    def test_both_disabled_result_is_successful(self):
        result = _orchestrator(television=None, av_receiver=None).switch_playback_output_to_oppo(
            _request(tv_enabled=False, av_enabled=False)
        )
        self.assertTrue(result.successful)

    def test_both_disabled_no_device_calls_made(self):
        tv = _RecordingTv()
        av = _RecordingAv()
        _orchestrator(television=tv, av_receiver=av).switch_playback_output_to_oppo(
            _request(tv_enabled=False, av_enabled=False)
        )
        self.assertEqual(0, tv.switch_calls)
        self.assertEqual(0, av.power_on_calls)
        self.assertEqual(0, av.switch_calls)

    def test_both_disabled_previous_tv_app_id_is_none(self):
        result = _orchestrator(television=None, av_receiver=None).switch_playback_output_to_oppo(
            _request(tv_enabled=False, av_enabled=False)
        )
        self.assertIsNone(result.previous_tv_app_id)

    # tv=False, av=True ──────────────────────────────────────────────────────

    def test_tv_disabled_av_enabled_tv_result_is_skipped(self):
        av = _RecordingAv()
        result = _orchestrator(television=None, av_receiver=av).switch_playback_output_to_oppo(
            _request(tv_enabled=False, av_enabled=True)
        )
        self.assertEqual(DeviceCommandStatus.SKIPPED, result.tv_input_result.status)

    def test_tv_disabled_av_enabled_av_steps_still_run(self):
        """Disabled TV must not block AV startup."""
        av = _RecordingAv()
        result = _orchestrator(television=None, av_receiver=av).switch_playback_output_to_oppo(
            _request(tv_enabled=False, av_enabled=True)
        )
        self.assertEqual(DeviceCommandStatus.SUCCESS, result.av_power_result.status)
        self.assertEqual(DeviceCommandStatus.SUCCESS, result.av_input_result.status)

    def test_tv_disabled_av_enabled_overall_successful(self):
        av = _RecordingAv()
        result = _orchestrator(television=None, av_receiver=av).switch_playback_output_to_oppo(
            _request(tv_enabled=False, av_enabled=True)
        )
        self.assertTrue(result.successful)

    def test_tv_disabled_av_enabled_tv_not_called(self):
        tv = _RecordingTv()
        av = _RecordingAv()
        _orchestrator(television=tv, av_receiver=av).switch_playback_output_to_oppo(
            _request(tv_enabled=False, av_enabled=True)
        )
        self.assertEqual(0, tv.switch_calls)

    def test_tv_disabled_av_enabled_previous_app_id_is_none(self):
        av = _RecordingAv()
        result = _orchestrator(television=None, av_receiver=av).switch_playback_output_to_oppo(
            _request(tv_enabled=False, av_enabled=True)
        )
        self.assertIsNone(result.previous_tv_app_id)

    # tv=True, av=False ──────────────────────────────────────────────────────

    def test_tv_enabled_av_disabled_tv_step_runs(self):
        tv = _RecordingTv()
        result = _orchestrator(television=tv, av_receiver=None).switch_playback_output_to_oppo(
            _request(tv_enabled=True, av_enabled=False)
        )
        self.assertEqual(DeviceCommandStatus.SUCCESS, result.tv_input_result.status)
        self.assertEqual(1, tv.switch_calls)

    def test_tv_enabled_av_disabled_av_results_are_skipped(self):
        tv = _RecordingTv()
        result = _orchestrator(television=tv, av_receiver=None).switch_playback_output_to_oppo(
            _request(tv_enabled=True, av_enabled=False)
        )
        self.assertEqual(DeviceCommandStatus.SKIPPED, result.av_power_result.status)
        self.assertEqual(DeviceCommandStatus.SKIPPED, result.av_input_result.status)

    def test_tv_enabled_av_disabled_overall_successful(self):
        tv = _RecordingTv()
        result = _orchestrator(television=tv, av_receiver=None).switch_playback_output_to_oppo(
            _request(tv_enabled=True, av_enabled=False)
        )
        self.assertTrue(result.successful)

    # tv=True, av=True (full path) ───────────────────────────────────────────

    def test_both_enabled_all_steps_run_and_succeed(self):
        tv = _RecordingTv()
        av = _RecordingAv()
        result = _orchestrator(television=tv, av_receiver=av).switch_playback_output_to_oppo(
            _request(tv_enabled=True, av_enabled=True)
        )
        self.assertEqual(DeviceCommandStatus.SUCCESS, result.tv_input_result.status)
        self.assertEqual(DeviceCommandStatus.SUCCESS, result.av_power_result.status)
        self.assertEqual(DeviceCommandStatus.SUCCESS, result.av_input_result.status)
        self.assertTrue(result.successful)
        self.assertEqual(1, tv.switch_calls)
        self.assertEqual(1, av.power_on_calls)
        self.assertEqual(1, av.switch_calls)

    # None adapter guards ────────────────────────────────────────────────────

    def test_none_television_with_tv_enabled_returns_skipped(self):
        """None adapter with enabled=True is a configuration error; treated as skipped."""
        result = _orchestrator(television=None, av_receiver=None).switch_playback_output_to_oppo(
            _request(tv_enabled=True, av_enabled=False)
        )
        self.assertEqual(DeviceCommandStatus.SKIPPED, result.tv_input_result.status)

    def test_failed_tv_blocks_av_when_tv_enabled(self):
        """A real FAILED TV result (not skipped) still blocks AV switching."""
        tv = _FailingTv()
        av = _RecordingAv()
        result = _orchestrator(television=tv, av_receiver=av).switch_playback_output_to_oppo(
            _request(tv_enabled=True, av_enabled=True)
        )
        self.assertEqual(DeviceCommandStatus.FAILED, result.tv_input_result.status)
        self.assertEqual(DeviceCommandStatus.SKIPPED, result.av_power_result.status)
        self.assertEqual(DeviceCommandStatus.SKIPPED, result.av_input_result.status)
        self.assertFalse(result.successful)


# ── Stubs ──────────────────────────────────────────────────────────────────

class _RecordingTv:
    def __init__(self):
        self.switch_calls = 0
        self.app_reads = 0

    def get_current_app_id(self):
        self.app_reads += 1
        return "com.webos.app.livetv"

    def switch_to_input(self, target):
        self.switch_calls += 1
        return DeviceCommandResult.success()

    def launch_app(self, app_id=None):
        return DeviceCommandResult.success()


class _FailingTv:
    def get_current_app_id(self):
        return None

    def switch_to_input(self, target):
        return DeviceCommandResult.failed("TV unreachable.")

    def launch_app(self, app_id=None):
        return DeviceCommandResult.failed("TV unreachable.")


class _RecordingAv:
    def __init__(self):
        self.power_on_calls = 0
        self.switch_calls = 0

    def power_on(self):
        self.power_on_calls += 1
        return DeviceCommandResult.success()

    def switch_to_input(self, input_id):
        self.switch_calls += 1
        return DeviceCommandResult.success()

    def restore_tv_audio(self):
        return DeviceCommandResult.success()


class _UnusedOppoPlayback:
    def start_playback(self, request, *, on_waiting=None):
        raise AssertionError("OPPO playback should not be called in these tests")

    def get_playback_position(self):
        raise AssertionError

    def get_playback_state(self):
        raise AssertionError
