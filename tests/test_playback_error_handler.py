import unittest

from home_cinema_control.playback.error_handling import (
    PlaybackErrorHandler,
    PlaybackErrorRecoveryRequest,
)
from home_cinema_control.playback.startup.models import (
    DeviceCommandResult,
    DeviceCommandStatus,
)


class RecordingTelevisionOutput:
    def __init__(self):
        self.calls = []

    def get_current_app_id(self):
        self.calls.append("get_current_app_id")
        return "com.emby.app"

    def switch_to_input(self, input_id):
        self.calls.append(("switch_to_input", input_id))
        return DeviceCommandResult.success("tv input switched")

    def launch_app(self, app_id=None):
        self.calls.append(("launch_app", app_id))
        return DeviceCommandResult.success("tv app restored")


class RecordingAvReceiverOutput:
    def __init__(self):
        self.calls = []

    def power_on(self):
        self.calls.append("power_on")
        return DeviceCommandResult.success("av powered")

    def switch_to_input(self, input_id):
        self.calls.append(("switch_to_input", input_id))
        return DeviceCommandResult.success("av input switched")

    def restore_tv_audio(self):
        self.calls.append("restore_tv_audio")
        return DeviceCommandResult.success("tv audio restored")


class RecordingOppoPlayback:
    def __init__(self, result=None, cleanup_result=None, stop_exception=None):
        self.calls = []
        self.result = result or DeviceCommandResult.success("oppo stopped")
        self.cleanup_result = cleanup_result or DeviceCommandResult.skipped(
            "no cleanup"
        )
        self.stop_exception = stop_exception

    def stop_playback(self):
        self.calls.append("stop_playback")
        if self.stop_exception is not None:
            raise self.stop_exception
        return self.result

    def cleanup_after_playback_finish(self):
        self.calls.append("cleanup_after_playback_finish")
        return self.cleanup_result


class PlaybackErrorHandlerTest(unittest.TestCase):
    def test_stops_player_and_recovers_tv_app_and_av_audio(self):
        television = RecordingTelevisionOutput()
        av_receiver = RecordingAvReceiverOutput()
        oppo = RecordingOppoPlayback()
        handler = PlaybackErrorHandler(
            television=television,
            av_receiver=av_receiver,
            oppo_playback=oppo,
        )

        result = handler.recover(
            PlaybackErrorRecoveryRequest(
                reason="oppo_startup_failed",
                previous_tv_app_id="com.emby.app",
                tv_enabled=True,
                av_enabled=True,
            )
        )

        self.assertTrue(result.successful)
        self.assertEqual(["stop_playback", "cleanup_after_playback_finish"], oppo.calls)
        self.assertEqual([("launch_app", "com.emby.app")], television.calls)
        self.assertEqual(["restore_tv_audio"], av_receiver.calls)

    def test_recovery_skips_disabled_outputs(self):
        television = RecordingTelevisionOutput()
        av_receiver = RecordingAvReceiverOutput()
        oppo = RecordingOppoPlayback()
        handler = PlaybackErrorHandler(
            television=television,
            av_receiver=av_receiver,
            oppo_playback=oppo,
        )

        result = handler.recover(
            PlaybackErrorRecoveryRequest(
                reason="oppo_startup_failed",
                previous_tv_app_id="com.emby.app",
                tv_enabled=False,
                av_enabled=False,
            )
        )

        self.assertTrue(result.successful)
        self.assertEqual(["stop_playback", "cleanup_after_playback_finish"], oppo.calls)
        self.assertEqual([], television.calls)
        self.assertEqual([], av_receiver.calls)

    def test_recovery_runs_player_cleanup_after_stop_success(self):
        oppo = RecordingOppoPlayback(
            cleanup_result=DeviceCommandResult.success("verbose disabled")
        )
        handler = PlaybackErrorHandler(
            television=RecordingTelevisionOutput(),
            av_receiver=RecordingAvReceiverOutput(),
            oppo_playback=oppo,
        )

        result = handler.recover(
            PlaybackErrorRecoveryRequest(
                reason="oppo_startup_failed",
                previous_tv_app_id="com.emby.app",
            )
        )

        self.assertTrue(result.successful)
        self.assertEqual(DeviceCommandStatus.SUCCESS, result.player_stop_result.status)
        self.assertIn("verbose disabled", result.player_stop_result.detail)

    def test_recovery_runs_player_cleanup_when_stop_raises(self):
        oppo = RecordingOppoPlayback(
            cleanup_result=DeviceCommandResult.success("verbose disabled"),
            stop_exception=RuntimeError("stop failed"),
        )
        handler = PlaybackErrorHandler(
            television=RecordingTelevisionOutput(),
            av_receiver=RecordingAvReceiverOutput(),
            oppo_playback=oppo,
        )

        result = handler.recover(
            PlaybackErrorRecoveryRequest(
                reason="oppo_startup_failed",
                previous_tv_app_id="com.emby.app",
            )
        )

        self.assertFalse(result.successful)
        self.assertEqual(
            ["stop_playback", "cleanup_after_playback_finish"],
            oppo.calls,
        )
        self.assertEqual(DeviceCommandStatus.FAILED, result.player_stop_result.status)

    def test_recovery_reports_player_cleanup_failure(self):
        oppo = RecordingOppoPlayback(
            cleanup_result=DeviceCommandResult.failed("svm restore failed")
        )
        handler = PlaybackErrorHandler(
            television=RecordingTelevisionOutput(),
            av_receiver=RecordingAvReceiverOutput(),
            oppo_playback=oppo,
        )

        result = handler.recover(
            PlaybackErrorRecoveryRequest(
                reason="oppo_startup_failed",
                previous_tv_app_id="com.emby.app",
            )
        )

        self.assertFalse(result.successful)
        self.assertEqual(DeviceCommandStatus.FAILED, result.player_stop_result.status)
        self.assertEqual("svm restore failed", result.player_stop_result.detail)

    def test_logs_recovery_result_at_error_level_when_recovery_fails(self):
        oppo = RecordingOppoPlayback(
            cleanup_result=DeviceCommandResult.failed("svm restore failed")
        )
        handler = PlaybackErrorHandler(
            television=RecordingTelevisionOutput(),
            av_receiver=RecordingAvReceiverOutput(),
            oppo_playback=oppo,
        )

        with self.assertLogs(
                "home_cinema_control.playback.error_handling", level="ERROR"
        ) as captured:
            handler.recover(
                PlaybackErrorRecoveryRequest(
                    reason="oppo_startup_failed",
                    previous_tv_app_id="com.emby.app",
                )
            )

        self.assertTrue(
            any("Playback error recovery result" in line for line in captured.output)
        )

    def test_logs_recovery_result_at_info_level_when_recovery_succeeds(self):
        handler = PlaybackErrorHandler(
            television=RecordingTelevisionOutput(),
            av_receiver=RecordingAvReceiverOutput(),
            oppo_playback=RecordingOppoPlayback(),
        )

        with self.assertLogs(
                "home_cinema_control.playback.error_handling", level="INFO"
        ) as captured:
            handler.recover(
                PlaybackErrorRecoveryRequest(
                    reason="oppo_startup_failed",
                    previous_tv_app_id="com.emby.app",
                )
            )

        result_logs = [
            r for r in captured.records if "Playback error recovery result" in r.getMessage()
        ]
        self.assertEqual(1, len(result_logs))
        self.assertEqual("INFO", result_logs[0].levelname)


if __name__ == "__main__":
    unittest.main()
