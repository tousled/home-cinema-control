import unittest
from types import SimpleNamespace

from home_cinema_control.playback.diagnostics import (
    PlaybackDiagnostic,
    diagnose_error_recovery_result,
    diagnose_finish_result,
    diagnose_oppo_unavailable,
    diagnose_orchestration_result,
    diagnose_path_error,
    diagnose_path_test_failed,
    diagnose_startup_result,
)
from home_cinema_control.playback.finish.models import PlaybackFinishResult
from home_cinema_control.playback.startup.models import (
    DeviceCommandResult,
    DeviceCommandStatus,
    PlayerPlaybackStartResult,
    PlaybackOutputSwitchResult,
    PlaybackStartupResult,
)


def _make_startup_result(
    *,
    tv_status=DeviceCommandStatus.SKIPPED,
    tv_detail=None,
    av_power_status=DeviceCommandStatus.SKIPPED,
    av_power_detail=None,
    av_input_status=DeviceCommandStatus.SKIPPED,
    av_input_detail=None,
    media_mounted=True,
    playback_command_accepted=True,
    playback_started_on_device=True,
    oppo_detail=None,
    mount_protocol=None,
):
    output_switch = PlaybackOutputSwitchResult(
        previous_tv_app_id=None,
        tv_input_result=DeviceCommandResult(status=tv_status, detail=tv_detail),
        av_power_result=DeviceCommandResult(status=av_power_status, detail=av_power_detail),
        av_input_result=DeviceCommandResult(status=av_input_status, detail=av_input_detail),
    )
    oppo = PlayerPlaybackStartResult(
        media_mounted=media_mounted,
        playback_command_accepted=playback_command_accepted,
        playback_started_on_device=playback_started_on_device,
        detail=oppo_detail,
        mount_protocol=mount_protocol,
    )
    return PlaybackStartupResult(
        output_switch_result=output_switch,
        media_player_start_result=oppo,
    )


def _successful_startup_result():
    return _make_startup_result()


class DiagnoseStartupResultTest(unittest.TestCase):
    def test_returns_none_when_successful(self):
        result = _make_startup_result()
        self.assertIsNone(diagnose_startup_result(result))

    def test_tv_input_switch_failed(self):
        result = _make_startup_result(
            tv_status=DeviceCommandStatus.FAILED,
            tv_detail="Connection refused",
        )
        diag = diagnose_startup_result(result)
        self.assertIsNotNone(diag)
        self.assertEqual("TV_INPUT_SWITCH_FAILED", diag.code)
        self.assertEqual("tv", diag.component)
        self.assertEqual("warning", diag.severity)
        self.assertEqual("startup_output_switch", diag.operation)
        self.assertIn("Connection refused", diag.reason)

    def test_av_power_on_failed(self):
        result = _make_startup_result(
            av_power_status=DeviceCommandStatus.FAILED,
            av_power_detail="Timeout",
        )
        diag = diagnose_startup_result(result)
        self.assertIsNotNone(diag)
        self.assertEqual("AV_POWER_ON_FAILED", diag.code)
        self.assertEqual("av", diag.component)

    def test_av_input_switch_failed(self):
        result = _make_startup_result(
            av_input_status=DeviceCommandStatus.FAILED,
            av_input_detail="No response",
        )
        diag = diagnose_startup_result(result)
        self.assertIsNotNone(diag)
        self.assertEqual("AV_INPUT_SWITCH_FAILED", diag.code)

    def test_oppo_mount_failed(self):
        result = _make_startup_result(media_mounted=False, oppo_detail="NAS unreachable")
        diag = diagnose_startup_result(result)
        self.assertIsNotNone(diag)
        self.assertEqual("OPPO_MOUNT_FAILED", diag.code)
        self.assertEqual("oppo", diag.component)
        self.assertEqual("error", diag.severity)
        self.assertIn("NAS unreachable", diag.reason)

    def test_oppo_mount_failure_with_stale_evidence_is_classified(self):
        result = _make_startup_result(
            media_mounted=False,
            oppo_detail="Timeout in Mount Request while mount point busy",
        )
        diag = diagnose_startup_result(result)
        self.assertIsNotNone(diag)
        self.assertEqual("OPPO_STALE_MOUNT_SUSPECTED", diag.code)
        self.assertEqual("warning", diag.severity)
        self.assertEqual("suspected_stale_mount", diag.details["classification"])

    def test_oppo_mount_failed_suggests_enabling_smb_when_only_nfs_was_tried(self):
        result = _make_startup_result(
            media_mounted=False, oppo_detail="NAS unreachable", mount_protocol="nfs"
        )
        diag = diagnose_startup_result(result, {"oppo": {"use_smb": False}, "smb": {}})
        self.assertIn("SMB was not attempted", diag.suggestion)

    def test_oppo_mount_failed_does_not_suggest_smb_when_already_tried(self):
        result = _make_startup_result(
            media_mounted=False, oppo_detail="NAS unreachable", mount_protocol="nfs"
        )
        config = {
            "oppo": {"use_smb": True},
            "smb": {"username": "user", "password": "pass"},
        }
        diag = diagnose_startup_result(result, config)
        self.assertNotIn("SMB was not attempted", diag.suggestion)

    def test_oppo_mount_failed_without_config_omits_smb_hint(self):
        result = _make_startup_result(
            media_mounted=False, oppo_detail="NAS unreachable", mount_protocol="nfs"
        )
        diag = diagnose_startup_result(result)
        self.assertNotIn("SMB was not attempted", diag.suggestion)

    def test_oppo_play_failed(self):
        result = _make_startup_result(
            playback_command_accepted=False,
            oppo_detail="Unsupported format",
        )
        diag = diagnose_startup_result(result)
        self.assertIsNotNone(diag)
        self.assertEqual("OPPO_PLAY_FAILED", diag.code)

    def test_oppo_playback_timeout(self):
        result = _make_startup_result(playback_started_on_device=False)
        diag = diagnose_startup_result(result)
        self.assertIsNotNone(diag)
        self.assertEqual("OPPO_PLAYBACK_TIMEOUT", diag.code)


class DiagnoseFinishResultTest(unittest.TestCase):
    def test_player_idle_failure_is_reported(self):
        result = PlaybackFinishResult(
            media_server_stop_result=None,
            player_idle_result=DeviceCommandResult.failed("QPL timeout"),
            tv_app_result=DeviceCommandResult.skipped("TV disabled"),
            av_audio_result=DeviceCommandResult.skipped("AV disabled"),
            final_player_state=None,
        )

        diag = diagnose_finish_result(result)

        self.assertEqual("OPPO_FINISH_IDLE_FAILED", diag.code)
        self.assertEqual("oppo", diag.component)
        self.assertEqual("finish_cleanup", diag.operation)

    def test_disabled_restore_skips_are_not_failures(self):
        result = PlaybackFinishResult(
            media_server_stop_result=None,
            player_idle_result=DeviceCommandResult.success("Idle"),
            tv_app_result=DeviceCommandResult.skipped("TV disabled"),
            av_audio_result=DeviceCommandResult.skipped("AV disabled"),
            final_player_state=None,
        )

        self.assertIsNone(diagnose_finish_result(result))


class DiagnoseRecoveryResultTest(unittest.TestCase):
    def test_cleanup_failure_is_reported(self):
        result = SimpleNamespace(
            successful=False,
            player_stop_result=DeviceCommandResult.failed("Cleanup failed"),
            tv_app_result=DeviceCommandResult.skipped("TV disabled"),
            av_audio_result=DeviceCommandResult.skipped("AV disabled"),
        )

        diag = diagnose_error_recovery_result(result)

        self.assertEqual("OPPO_ERROR_RECOVERY_FAILED", diag.code)
        self.assertEqual("cleanup", diag.component)
        self.assertEqual("error_recovery", diag.operation)


class DiagnoseOrchestrationResultTest(unittest.TestCase):
    def test_orchestration_prefers_startup_diagnostic(self):
        class Result:
            startup_result = _make_startup_result(media_mounted=False, oppo_detail="NAS down")
            finish_result = None
            error_recovery_result = None

        diag = diagnose_orchestration_result(Result())

        self.assertEqual("OPPO_MOUNT_FAILED", diag.code)


class DiagnosePathErrorTest(unittest.TestCase):
    def test_path_resolution_diagnostic(self):
        exc = ValueError("Player media path must include server, folder and file")
        diag = diagnose_path_error(exc)
        self.assertEqual("PATH_RESOLUTION_FAILED", diag.code)
        self.assertEqual("path", diag.component)
        self.assertEqual("error", diag.severity)
        self.assertIn("server, folder and file", diag.reason)


class DiagnosePathTestFailedTest(unittest.TestCase):
    def test_stale_mount_path_test_diagnostic(self):
        diag = diagnose_path_test_failed(
            "OPPO_MOUNT_FAILED: Timeout in Mount Request while resource busy"
        )

        self.assertEqual("OPPO_STALE_MOUNT_SUSPECTED", diag.code)
        self.assertEqual("oppo", diag.component)
        self.assertEqual("path_mount_test", diag.operation)

    def test_oppo_unavailable_path_test_diagnostic(self):
        diag = diagnose_path_test_failed("OPPO_UNAVAILABLE: OPPO socket is not reachable")

        self.assertEqual("OPPO_PATH_TEST_UNAVAILABLE", diag.code)
        self.assertEqual("oppo", diag.component)

    def test_generic_path_test_diagnostic(self):
        diag = diagnose_path_test_failed("INVALID PATH CONFIG: player_path is required.")

        self.assertEqual("PATH_TEST_FAILED", diag.code)
        self.assertEqual("path", diag.component)

    def test_generic_path_test_diagnostic_suggests_enabling_smb_when_disabled(self):
        diag = diagnose_path_test_failed(
            "INVALID PATH CONFIG: player_path is required.",
            {"oppo": {"use_smb": False}, "smb": {}},
        )

        self.assertIn("SMB was not attempted", diag.suggestion)

    def test_generic_path_test_diagnostic_omits_smb_hint_when_smb_enabled(self):
        diag = diagnose_path_test_failed(
            "INVALID PATH CONFIG: player_path is required.",
            {"oppo": {"use_smb": True}, "smb": {"username": "user", "password": "pass"}},
        )

        self.assertNotIn("SMB was not attempted", diag.suggestion)


class DiagnoseOppoUnavailableTest(unittest.TestCase):
    def test_oppo_unavailable_diagnostic(self):
        diag = diagnose_oppo_unavailable()
        self.assertEqual("OPPO_UNAVAILABLE", diag.code)
        self.assertEqual("oppo", diag.component)
        self.assertEqual("error", diag.severity)


class PlaybackDiagnosticToDictTest(unittest.TestCase):
    def test_to_dict_contains_all_fields(self):
        diag = PlaybackDiagnostic(
            code="TEST_CODE",
            severity="error",
            component="oppo",
            reason="Something failed",
            suggestion="Try this fix",
            operation="test_operation",
            details={"a": 1},
            timestamp=1234567890.0,
        )
        d = diag.to_dict()
        self.assertEqual("TEST_CODE", d["code"])
        self.assertEqual("error", d["severity"])
        self.assertEqual("oppo", d["component"])
        self.assertEqual("Something failed", d["reason"])
        self.assertEqual("Try this fix", d["suggestion"])
        self.assertEqual("test_operation", d["operation"])
        self.assertEqual({"a": 1}, d["details"])
        self.assertEqual(1234567890.0, d["timestamp"])


if __name__ == "__main__":
    unittest.main()
