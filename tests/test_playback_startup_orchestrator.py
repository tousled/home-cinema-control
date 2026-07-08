import unittest

from home_cinema_control.devices.tv.models import TvInputTarget
from home_cinema_control.playback.startup.models import (
    DeviceCommandResult,
    PlaybackOutputSwitchRequest,
)
from home_cinema_control.playback.startup.orchestrator import (
    PlaybackStartupOrchestrator,
)


class PlaybackStartupOrchestratorTest(unittest.TestCase):
    def test_output_switch_uses_preserved_return_app_without_reading_current_tv_app(self):
        television = RecordingTelevisionOutput(current_app_id="com.webos.app.hdmi3")
        orchestrator = PlaybackStartupOrchestrator(
            television=television,
            av_receiver=RecordingAvReceiverOutput(),
            media_player=UnusedOppoPlayback(),
        )

        result = orchestrator.switch_playback_output_to_oppo(
            PlaybackOutputSwitchRequest(
                tv_input=TvInputTarget(input_id="HDMI_3"),
                av_input_id="SIMPLAY",
                previous_tv_app_id_override="com.emby.app",
            )
        )

        self.assertEqual("com.emby.app", result.previous_tv_app_id)
        self.assertEqual(0, television.current_app_reads)
        self.assertEqual(["HDMI_3"], television.input_switches)

    def test_output_switch_reads_current_tv_app_when_no_preserved_app_exists(self):
        television = RecordingTelevisionOutput(current_app_id="com.emby.app")
        orchestrator = PlaybackStartupOrchestrator(
            television=television,
            av_receiver=RecordingAvReceiverOutput(),
            media_player=UnusedOppoPlayback(),
        )

        result = orchestrator.switch_playback_output_to_oppo(
            PlaybackOutputSwitchRequest(
                tv_input=TvInputTarget(input_id="HDMI_3"),
                av_input_id="SIMPLAY",
            )
        )

        self.assertEqual("com.emby.app", result.previous_tv_app_id)
        self.assertEqual(1, television.current_app_reads)

    def test_output_switch_uses_provider_fallback_when_current_app_is_unavailable(self):
        television = RecordingTelevisionOutput(current_app_id=None)
        orchestrator = PlaybackStartupOrchestrator(
            television=television,
            av_receiver=RecordingAvReceiverOutput(),
            media_player=UnusedOppoPlayback(),
        )

        result = orchestrator.switch_playback_output_to_oppo(
            PlaybackOutputSwitchRequest(
                tv_input=TvInputTarget(input_id="HDMI_3"),
                av_input_id="SIMPLAY",
                active_media_server_provider_type="jellyfin",
            )
        )

        self.assertEqual("org.jellyfin.webos", result.previous_tv_app_id)
        self.assertEqual(1, television.current_app_reads)
        self.assertEqual(["jellyfin"], television.media_server_app_id_calls)

    def test_output_switch_keeps_none_when_current_app_and_fallback_are_unavailable(self):
        television = RecordingTelevisionOutput(current_app_id=None)
        orchestrator = PlaybackStartupOrchestrator(
            television=television,
            av_receiver=RecordingAvReceiverOutput(),
            media_player=UnusedOppoPlayback(),
        )

        result = orchestrator.switch_playback_output_to_oppo(
            PlaybackOutputSwitchRequest(
                tv_input=TvInputTarget(input_id="HDMI_3"),
                av_input_id="SIMPLAY",
                active_media_server_provider_type=None,
            )
        )

        self.assertIsNone(result.previous_tv_app_id)
        self.assertEqual(1, television.current_app_reads)
        self.assertEqual([], television.media_server_app_id_calls)

    def test_output_switch_does_not_read_current_app_when_tv_is_disabled(self):
        television = RecordingTelevisionOutput(current_app_id="com.emby.app")
        orchestrator = PlaybackStartupOrchestrator(
            television=television,
            av_receiver=RecordingAvReceiverOutput(),
            media_player=UnusedOppoPlayback(),
        )

        result = orchestrator.switch_playback_output_to_oppo(
            PlaybackOutputSwitchRequest(
                tv_input=TvInputTarget(input_id="HDMI_3"),
                av_input_id="SIMPLAY",
                tv_enabled=False,
                active_media_server_provider_type="emby",
            )
        )

        self.assertIsNone(result.previous_tv_app_id)
        self.assertEqual(0, television.current_app_reads)
        self.assertEqual([], television.media_server_app_id_calls)


class RecordingTelevisionOutput:
    def __init__(self, *, current_app_id):
        self._current_app_id = current_app_id
        self.current_app_reads = 0
        self.input_switches = []
        self.media_server_app_id_calls = []

    def get_current_app_id(self):
        self.current_app_reads += 1
        return self._current_app_id

    def switch_to_input(self, target):
        self.input_switches.append(target.input_id)
        return DeviceCommandResult.success()

    def media_server_app_id(self, provider_type):
        self.media_server_app_id_calls.append(provider_type)
        return {
            "emby": "com.emby.app",
            "jellyfin": "org.jellyfin.webos",
        }.get(provider_type)

    def launch_app(self, app_id=None):
        return DeviceCommandResult.success()


class RecordingAvReceiverOutput:
    def power_on(self):
        return DeviceCommandResult.success()

    def switch_to_input(self, input_id):
        return DeviceCommandResult.success()

    def restore_tv_audio(self):
        return DeviceCommandResult.success()


class UnusedOppoPlayback:
    pass


if __name__ == "__main__":
    unittest.main()
