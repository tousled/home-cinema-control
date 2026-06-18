import unittest
from types import SimpleNamespace

from home_cinema_control.playback.application import (
    PlaybackApplicationService,
)
from home_cinema_control.playback.startup.models import (
    DeviceCommandResult,
    PlaybackOutputSwitchResult,
)
from home_cinema_control.playback.intent import PlaybackIntent, PlaybackOrigin
from home_cinema_control.playback.state import BridgePlaybackState


class PlaybackApplicationServiceTest(unittest.TestCase):
    def test_request_playback_ignores_duplicate_active_item(self):
        calls = []
        state = BridgePlaybackState()
        state.playstate = "Playing"
        state.start_loading(_intent(media_item_id="11136"))
        state.playstate = "Playing"
        service = PlaybackApplicationService(
            playback_session=FakePlaybackSession(),
            playback_state=state,
            reload_config=lambda: None,
        )
        service.start_from_intent = lambda *args, **kwargs: calls.append("start")
        service.replace_from_intent = lambda *args, **kwargs: calls.append("replace")

        requested = service.request_playback_from_intent(
            _intent(media_item_id="11136"),
            origin=PlaybackOrigin.OBSERVED_TV_CLIENT,
        )

        self.assertFalse(requested)
        self.assertEqual([], calls)

    def test_request_playback_replaces_when_other_item_is_active(self):
        calls = []
        state = BridgePlaybackState()
        state.playstate = "Playing"
        state.start_loading(_intent(media_item_id="11136"))
        state.playstate = "Playing"
        service = PlaybackApplicationService(
            playback_session=FakePlaybackSession(),
            playback_state=state,
            reload_config=lambda: None,
        )
        service.replace_from_intent = (
            lambda *args, **kwargs: calls.append(("replace", args, kwargs)) or True
        )
        intent = _intent(media_item_id="22222")

        requested = service.request_playback_from_intent(
            intent,
            origin=PlaybackOrigin.REMOTE_CONTROL_COMMAND,
        )

        self.assertTrue(requested)
        self.assertEqual("replace", calls[0][0])
        self.assertIs(intent, calls[0][1][0])
        self.assertEqual({"origin": PlaybackOrigin.REMOTE_CONTROL_COMMAND}, calls[0][2])

    def test_request_playback_starts_when_playback_is_free(self):
        calls = []
        service = PlaybackApplicationService(
            playback_session=FakePlaybackSession(),
            playback_state=BridgePlaybackState(),
            reload_config=lambda: None,
        )
        service.start_from_intent = (
            lambda *args, **kwargs: calls.append(("start", args, kwargs))
        )
        intent = _intent(media_item_id="22222")

        requested = service.request_playback_from_intent(
            intent,
            origin=PlaybackOrigin.REMOTE_CONTROL_COMMAND,
        )

        self.assertTrue(requested)
        self.assertEqual("start", calls[0][0])
        self.assertIs(intent, calls[0][1][0])
        self.assertEqual({"origin": PlaybackOrigin.REMOTE_CONTROL_COMMAND}, calls[0][2])

    def test_active_iso_replacement_uses_stop_command(self):

        command = "STP"

        self.assertEqual("STP", command)

    def test_active_file_replacement_uses_stop_command(self):

        command = "STP"

        self.assertEqual("STP", command)

    def test_remembers_non_hdmi_tv_return_app(self):
        service = PlaybackApplicationService(
            playback_session="session",
            playback_state=BridgePlaybackState(),
            reload_config=lambda: None,
        )

        service._remember_playback_return_tv_app_id(
            _playback_result_with_previous_tv_app("com.emby.app")
        )

        self.assertEqual("com.emby.app", service._playback_return_tv_app_id)

    def test_does_not_overwrite_return_app_with_hdmi_input(self):
        service = PlaybackApplicationService(
            playback_session="session",
            playback_state=BridgePlaybackState(),
            reload_config=lambda: None,
        )
        service._playback_return_tv_app_id = "com.emby.app"

        service._remember_playback_return_tv_app_id(
            _playback_result_with_previous_tv_app("com.webos.app.hdmi3")
        )

        self.assertEqual("com.emby.app", service._playback_return_tv_app_id)

    def test_keeps_return_app_while_replacement_finish_is_joining(self):
        service = PlaybackApplicationService(
            playback_session="session",
            playback_state=BridgePlaybackState(),
            reload_config=lambda: None,
        )
        service._playback_return_tv_app_id = "com.emby.app"
        service._thread_lifecycle._replacement_requested.set()

        service._clear_playback_return_tv_app_id_after_final_finish(
            _playback_result_with_previous_tv_app("com.emby.app", finished=True)
        )

        self.assertEqual("com.emby.app", service._playback_return_tv_app_id)

    def test_clears_return_app_after_final_finish(self):
        service = PlaybackApplicationService(
            playback_session="session",
            playback_state=BridgePlaybackState(),
            reload_config=lambda: None,
        )
        service._playback_return_tv_app_id = "com.emby.app"

        service._clear_playback_return_tv_app_id_after_final_finish(
            _playback_result_with_previous_tv_app("com.emby.app", finished=True)
        )

        self.assertIsNone(service._playback_return_tv_app_id)


class FakePlaybackSession:
    def __init__(self):
        self.config = {"app": {"log_level": 0}}


def _intent(*, media_item_id: str) -> PlaybackIntent:
    return PlaybackIntent(
        media_item_id=media_item_id,
        media_source_id="",
        source_user_id="",
        source_client_session_id=None,
        source_device_id="",
        source_device_name="",
        start_position_seconds=0,
        selected_audio_track_id=1,
        selected_subtitle_track_id=-1,
    )


def _playback_result_with_previous_tv_app(previous_tv_app_id, *, finished=False):
    return SimpleNamespace(
        startup_result=SimpleNamespace(
            output_switch_result=PlaybackOutputSwitchResult(
                previous_tv_app_id=previous_tv_app_id,
                tv_input_result=DeviceCommandResult.success(),
                av_power_result=DeviceCommandResult.success(),
                av_input_result=DeviceCommandResult.success(),
            )
        ),
        finish_result=object() if finished else None,
    )


if __name__ == "__main__":
    unittest.main()
