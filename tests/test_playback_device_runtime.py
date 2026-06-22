import unittest
from types import SimpleNamespace

from home_cinema_control.playback.device_runtime import (
    ensure_oppo_control_api_available,
    power_down_after_playback_if_configured,
    prepare_oppo_observation_mode,
    stop_active_player_playback_before_replacement,
)
from home_cinema_control.media_servers.emby.playback import (
    MediaContentKind,
    MediaServerPlaybackSource,
)
from home_cinema_control.playback.intent import PlaybackIntent
from home_cinema_control.playback.media_location import PlayerMediaFileLocation
from home_cinema_control.playback.state import BridgePlaybackState


class PlaybackDeviceRuntimeTest(unittest.TestCase):
    def test_prepares_oppo_observation_mode_by_restoring_svm0(self):
        calls = []

        prepare_oppo_observation_mode(
            {"oppo": {}},
            svm_mode_client_factory=lambda config, name: FakeSVMModeClient(
                calls,
                config=config,
                name=name,
                successful=True,
            ),
        )

        self.assertEqual(
            [("create_svm_client", {"oppo": {}}, "oppo-startup-svm-mode"), ("set", 0)],
            calls,
        )

    def test_ensure_oppo_control_api_available_uses_configured_timeout(self):
        calls = []

        available = ensure_oppo_control_api_available(
            {"oppo": {"connection_timeout_seconds": "7"}},
            activator_factory=lambda config: FakeActivator(calls, available=True),
        )

        self.assertTrue(available)
        self.assertEqual([("ensure", 7)], calls)

    def test_ensure_oppo_control_api_available_reports_unavailable(self):
        available = ensure_oppo_control_api_available(
            {"oppo": {"connection_timeout_seconds": 3}},
            activator_factory=lambda config: FakeActivator([], available=False),
        )

        self.assertFalse(available)

    def test_logs_unavailable_oppo_at_error_level(self):
        with self.assertLogs(
            "home_cinema_control.playback.device_runtime", level="ERROR"
        ) as captured:
            ensure_oppo_control_api_available(
                {"oppo": {"connection_timeout_seconds": 3}},
                activator_factory=lambda config: FakeActivator([], available=False),
            )

        self.assertTrue(
            any("Timeout waiting for OPPO control API" in line for line in captured.output)
        )

    def test_power_down_turns_off_configured_non_always_on_devices(self):
        calls = []

        power_down_after_playback_if_configured(
            {
                "av": {"enabled": True, "always_on": False},
                "oppo": {"always_on": False},
            },
            av_receiver_factory=lambda config: FakeAVReceiver(calls),
            control_client_factory=lambda config: FakeControlClient(calls),
        )

        self.assertEqual(["av_power_off", ("oppo_remote_key", "POF")], calls)

    def test_power_down_skips_always_on_devices(self):
        calls = []

        power_down_after_playback_if_configured(
            {
                "av": {"enabled": True, "always_on": True},
                "oppo": {"always_on": True},
            },
            av_receiver_factory=lambda config: FakeAVReceiver(calls),
            control_client_factory=lambda config: FakeControlClient(calls),
        )

        self.assertEqual([], calls)

    def test_stop_active_player_uses_stop_command(self):
        calls = []
        state = BridgePlaybackState()
        state.start_loading(_intent())
        state.set_active_media_location(
            media_location=PlayerMediaFileLocation(
                content_server="nas",
                content_directory="Movies",
                playback_file_name="Movie.mkv",
                playback_file_format="mkv",
            ),
            item_info=MediaServerPlaybackSource(
                path="/nas/Movies/Movie.mkv",
                container="mkv",
                duration_seconds=0,
                production_year=None,
                title="Movie",
                content_kind=MediaContentKind.MOVIE,
            ),
        )

        stop_active_player_playback_before_replacement(
            state,
            {"oppo": {}},
            control_client_factory=lambda config: FakeControlClient(calls),
        )

        self.assertEqual([("oppo_remote_key", "STP")], calls)


class FakeSVMModeClient:
    def __init__(self, calls, *, config, name, successful):
        self._calls = calls
        self._successful = successful
        calls.append(("create_svm_client", config, name))

    def set_mode(self, mode):
        self._calls.append(("set", mode))
        return SimpleNamespace(successful=self._successful, detail="detail")


class FakeActivator:
    def __init__(self, calls, *, available):
        self._calls = calls
        self._available = available

    def ensure_control_api_available(self, *, max_attempts):
        self._calls.append(("ensure", max_attempts))
        return SimpleNamespace(
            available=self._available,
            host="oppo",
            port=23,
            attempts=max_attempts,
            error=None,
        )


class FakeAVReceiver:
    def __init__(self, calls):
        self._calls = calls

    def power_off(self):
        self._calls.append("av_power_off")


class FakeControlClient:
    def __init__(self, calls):
        self._calls = calls

    def send_remote_key(self, key):
        self._calls.append(("oppo_remote_key", key))


def _intent() -> PlaybackIntent:
    return PlaybackIntent(
        media_item_id="media-1",
        media_source_id="source-1",
        source_user_id="user-1",
        source_client_session_id="session-1",
        source_device_id="device-1",
        source_device_name="Living Room TV",
        start_position_seconds=12,
        selected_audio_track_id=2,
        selected_subtitle_track_id=-1,
    )


if __name__ == "__main__":
    unittest.main()
