import unittest

from home_cinema_control.playback.player_state import (
    PlayerPlaybackLifecyclePhase,
    PlayerPlaybackState,
    PlayerPlaybackStatus,
)
from home_cinema_control.playback.restoration import (
    PlaybackOutputRestorationRequest,
    PlaybackRestorationService,
)
from home_cinema_control.playback.startup.models import (
    DeviceCommandResult,
    DeviceCommandStatus,
)


class RecordingTelevision:
    def __init__(self, *, launch_exception=None):
        self.calls = []
        self.launch_exception = launch_exception

    def get_current_app_id(self):
        return None

    def switch_to_input(self, target):
        return DeviceCommandResult.success("tv input switched")

    def launch_app(self, app_id=None):
        self.calls.append(("launch_app", app_id))
        if self.launch_exception is not None:
            raise self.launch_exception
        return DeviceCommandResult.success("tv app restored")


class RecordingAvReceiver:
    def __init__(self, *, restore_exception=None):
        self.calls = []
        self.restore_exception = restore_exception

    def power_on(self):
        return DeviceCommandResult.success("av powered")

    def switch_to_input(self, input_id):
        return DeviceCommandResult.success("av input switched")

    def restore_tv_audio(self):
        self.calls.append("restore_tv_audio")
        if self.restore_exception is not None:
            raise self.restore_exception
        return DeviceCommandResult.success("tv audio restored")


class RecordingMediaPlayer:
    def __init__(self, cleanup_result=None, cleanup_exception=None):
        self.calls = []
        self.cleanup_result = cleanup_result or DeviceCommandResult.skipped(
            "no cleanup"
        )
        self.cleanup_exception = cleanup_exception

    def cleanup_after_playback_finish(self):
        self.calls.append("cleanup_after_playback_finish")
        if self.cleanup_exception is not None:
            raise self.cleanup_exception
        return self.cleanup_result


class PlaybackRestorationServiceTest(unittest.TestCase):
    def test_cleanup_after_confirmed_player_state_keeps_result_when_cleanup_skips(self):
        media_player = RecordingMediaPlayer(
            cleanup_result=DeviceCommandResult.skipped("no cleanup")
        )
        service = _service(media_player=media_player)

        result = service.cleanup_after_confirmed_player_state(
            DeviceCommandResult.success("OPPO idle state confirmed.")
        )

        self.assertEqual(DeviceCommandStatus.SUCCESS, result.status)
        self.assertEqual("OPPO idle state confirmed.", result.detail)
        self.assertEqual(["cleanup_after_playback_finish"], media_player.calls)

    def test_cleanup_after_confirmed_player_state_appends_cleanup_success(self):
        service = _service(
            media_player=RecordingMediaPlayer(
                cleanup_result=DeviceCommandResult.success("verbose disabled")
            )
        )

        result = service.cleanup_after_confirmed_player_state(
            DeviceCommandResult.success("OPPO idle state confirmed.")
        )

        self.assertEqual(DeviceCommandStatus.SUCCESS, result.status)
        self.assertEqual(
            "OPPO idle state confirmed.; verbose disabled",
            result.detail,
        )

    def test_cleanup_after_confirmed_player_state_reports_cleanup_failure(self):
        service = _service(
            media_player=RecordingMediaPlayer(
                cleanup_result=DeviceCommandResult.failed("svm restore failed")
            )
        )

        result = service.cleanup_after_confirmed_player_state(
            DeviceCommandResult.success("OPPO idle state confirmed.")
        )

        self.assertEqual(DeviceCommandStatus.FAILED, result.status)
        self.assertEqual("svm restore failed", result.detail)

    def test_cleanup_after_confirmed_player_state_keeps_idle_failure_precedence(self):
        service = _service(
            media_player=RecordingMediaPlayer(
                cleanup_result=DeviceCommandResult.success("verbose disabled")
            )
        )

        result = service.cleanup_after_confirmed_player_state(
            DeviceCommandResult.failed("idle confirmation failed")
        )

        self.assertEqual(DeviceCommandStatus.FAILED, result.status)
        self.assertEqual("idle confirmation failed", result.detail)

    def test_cleanup_after_player_stop_keeps_stop_failure_precedence(self):
        service = _service(
            media_player=RecordingMediaPlayer(
                cleanup_result=DeviceCommandResult.success("verbose disabled")
            )
        )

        result = service.cleanup_after_player_stop(
            DeviceCommandResult.failed("stop failed")
        )

        self.assertEqual(DeviceCommandStatus.FAILED, result.status)
        self.assertEqual("stop failed", result.detail)

    def test_cleanup_after_player_stop_reports_cleanup_exception(self):
        service = _service(
            media_player=RecordingMediaPlayer(cleanup_exception=RuntimeError("boom"))
        )

        result = service.cleanup_after_player_stop(
            DeviceCommandResult.success("oppo stopped")
        )

        self.assertEqual(DeviceCommandStatus.FAILED, result.status)
        self.assertEqual(
            "OPPO playback error cleanup failed: RuntimeError: boom",
            result.detail,
        )

    def test_restore_outputs_restores_tv_and_av(self):
        television = RecordingTelevision()
        av_receiver = RecordingAvReceiver()
        service = _service(television=television, av_receiver=av_receiver)

        result = service.restore_outputs(
            PlaybackOutputRestorationRequest(previous_tv_app_id="com.emby.app")
        )

        self.assertTrue(result.successful)
        self.assertEqual([("launch_app", "com.emby.app")], television.calls)
        self.assertEqual(["restore_tv_audio"], av_receiver.calls)

    def test_restore_outputs_skips_disabled_outputs(self):
        television = RecordingTelevision()
        av_receiver = RecordingAvReceiver()
        service = _service(television=television, av_receiver=av_receiver)

        result = service.restore_outputs(
            PlaybackOutputRestorationRequest(
                previous_tv_app_id="com.emby.app",
                tv_enabled=False,
                av_enabled=False,
            )
        )

        self.assertTrue(result.successful)
        self.assertEqual(DeviceCommandStatus.SKIPPED, result.tv_app_result.status)
        self.assertEqual(DeviceCommandStatus.SKIPPED, result.av_audio_result.status)
        self.assertEqual([], television.calls)
        self.assertEqual([], av_receiver.calls)

    def test_restore_outputs_skips_missing_adapters(self):
        service = _service(television=None, av_receiver=None)

        result = service.restore_outputs(
            PlaybackOutputRestorationRequest(previous_tv_app_id="com.emby.app")
        )

        self.assertTrue(result.successful)
        self.assertEqual(DeviceCommandStatus.SKIPPED, result.tv_app_result.status)
        self.assertEqual(DeviceCommandStatus.SKIPPED, result.av_audio_result.status)

    def test_restore_outputs_skips_screen_saver_state(self):
        television = RecordingTelevision()
        av_receiver = RecordingAvReceiver()
        service = _service(television=television, av_receiver=av_receiver)

        result = service.restore_outputs(
            PlaybackOutputRestorationRequest(
                previous_tv_app_id="com.emby.app",
                final_player_state=_state(
                    PlayerPlaybackStatus.SCREEN_SAVER,
                    PlayerPlaybackLifecyclePhase.IDLE,
                ),
            )
        )

        self.assertTrue(result.successful)
        self.assertEqual(DeviceCommandStatus.SKIPPED, result.tv_app_result.status)
        self.assertEqual(DeviceCommandStatus.SKIPPED, result.av_audio_result.status)
        self.assertEqual([], television.calls)
        self.assertEqual([], av_receiver.calls)

    def test_restore_outputs_converts_tv_exception_to_failed_result(self):
        service = _service(
            television=RecordingTelevision(launch_exception=RuntimeError("tv boom")),
            av_receiver=RecordingAvReceiver(),
        )

        result = service.restore_outputs(
            PlaybackOutputRestorationRequest(previous_tv_app_id="com.emby.app")
        )

        self.assertFalse(result.successful)
        self.assertEqual(DeviceCommandStatus.FAILED, result.tv_app_result.status)
        self.assertEqual(
            "TV app restore failed: RuntimeError: tv boom",
            result.tv_app_result.detail,
        )

    def test_restore_outputs_converts_av_exception_to_failed_result(self):
        service = _service(
            television=RecordingTelevision(),
            av_receiver=RecordingAvReceiver(restore_exception=RuntimeError("av boom")),
        )

        result = service.restore_outputs(
            PlaybackOutputRestorationRequest(previous_tv_app_id="com.emby.app")
        )

        self.assertFalse(result.successful)
        self.assertEqual(DeviceCommandStatus.FAILED, result.av_audio_result.status)
        self.assertEqual(
            "AV TV audio restore failed: RuntimeError: av boom",
            result.av_audio_result.detail,
        )


def _service(
    *,
    television=None,
    av_receiver=None,
    media_player=None,
):
    return PlaybackRestorationService(
        television=television,
        av_receiver=av_receiver,
        media_player=media_player,
    )


def _state(status, lifecycle_phase):
    return PlayerPlaybackState(
        status=status,
        lifecycle_phase=lifecycle_phase,
        raw_response=f"@OK {status.value}",
        ok=True,
    )


if __name__ == "__main__":
    unittest.main()
