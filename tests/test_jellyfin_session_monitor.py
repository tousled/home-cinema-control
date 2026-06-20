import unittest
from unittest.mock import MagicMock

from home_cinema_control.media_servers.jellyfin.session_monitor import (
    JellyfinSessionMonitor,
)
from home_cinema_control.playback.intent import PlaybackOrigin
from home_cinema_control.playback.state import BridgePlaybackState


def _make_session(
    device_id="device-1",
    device_name="LG TV",
    user_id="user-1",
    item_id="42",
    item_name="Blade Runner 2049",
    item_path="/movies/blade_runner.mkv",
    audio_index=1,
    subtitle_index=-1,
    position_ticks=0,
):
    return {
        "DeviceId": device_id,
        "DeviceName": device_name,
        "UserId": user_id,
        "NowPlayingItem": {
            "Id": item_id,
            "Name": item_name,
            "Type": "Movie",
            "Path": item_path,
            "Container": "mkv",
        },
        "PlayState": {
            "AudioStreamIndex": audio_index,
            "SubtitleStreamIndex": subtitle_index,
            "PositionTicks": position_ticks,
            "MediaSourceId": "source-1",
        },
    }


def _make_item_info(item_id="42", user_data=None):
    return {
        "Id": item_id,
        "UserData": user_data or {"Played": False, "PlayCount": 0},
        "MediaSources": [{"Id": "source-1", "Container": "mkv"}],
    }


def _config(
    device_id="device-1",
    use_all_libraries=False,
    libraries=None,
    path_mappings=None,
):
    if libraries is None:
        libraries = [{"id": "lib-1", "name": "Movies", "active": True}]
    if path_mappings is None:
        path_mappings = [
            {
                "source_path": "/movies",
                "player_path": "/NAS/Movies",
                "protocol": "nfs",
                "verified": True,
            }
        ]
    return {
        "playback": {
            "hcc_controlled_device": device_id,
            "use_all_libraries": use_all_libraries,
            "libraries": libraries,
            "path_mappings": path_mappings,
        }
    }


class JellyfinSessionMonitorTest(unittest.TestCase):
    def setUp(self):
        self.jellyfin_session = MagicMock()
        self.jellyfin_session.get_item_info.return_value = _make_item_info()
        self.jellyfin_session.is_item_path_in_library.return_value = True
        self.playback_state = BridgePlaybackState()
        self.dispatcher = MagicMock()
        self.config = _config()

    def _monitor(self, config=None):
        return JellyfinSessionMonitor(
            jellyfin_session=self.jellyfin_session,
            playback_state=self.playback_state,
            config_provider=lambda: config or self.config,
            dispatcher=self.dispatcher,
        )

    def test_no_matching_session_does_nothing(self):
        monitor = self._monitor()

        monitor.on_sessions_update([_make_session(device_id="other-device")])

        self.dispatcher.dispatch.assert_not_called()

    def test_item_not_in_library_does_not_dispatch(self):
        self.jellyfin_session.is_item_path_in_library.return_value = False
        monitor = self._monitor()

        monitor.on_sessions_update([_make_session()])

        self.dispatcher.dispatch.assert_not_called()

    def test_item_without_verified_path_mapping_does_not_dispatch(self):
        monitor = self._monitor(
            config=_config(
                path_mappings=[
                    {
                        "source_path": "/movies",
                        "player_path": "/NAS/Movies",
                        "protocol": "nfs",
                        "verified": False,
                    }
                ]
            )
        )

        monitor.on_sessions_update([_make_session()])

        self.dispatcher.dispatch.assert_not_called()

    def test_new_item_in_library_dispatches_intent(self):
        monitor = self._monitor()

        monitor.on_sessions_update([_make_session(item_id="99", audio_index=2)])

        self.dispatcher.dispatch.assert_called_once()
        intent = self.dispatcher.dispatch.call_args[0][0]
        kwargs = self.dispatcher.dispatch.call_args.kwargs
        self.assertEqual("99", intent.media_item_id)
        self.assertEqual("source-1", intent.media_source_id)
        self.assertEqual(2, intent.selected_audio_track_id)
        self.assertEqual(PlaybackOrigin.OBSERVED_TV_CLIENT, kwargs["origin"])

    def test_uppercase_library_shape_is_supported(self):
        monitor = self._monitor(
            config=_config(libraries=[{"Id": "lib-1", "Name": "Movies", "Active": True}])
        )

        monitor.on_sessions_update([_make_session()])

        self.jellyfin_session.is_item_path_in_library.assert_called_once_with(
            "lib-1",
            "/movies/blade_runner.mkv",
        )
        self.dispatcher.dispatch.assert_called_once()

    def test_same_item_on_second_update_does_not_dispatch_again(self):
        monitor = self._monitor()
        session = _make_session()

        monitor.on_sessions_update([session])
        monitor.on_sessions_update([session])

        self.dispatcher.dispatch.assert_called_once()

    def test_item_stopped_resets_monitored_state_when_bridge_inactive(self):
        monitor = self._monitor()
        monitor.on_sessions_update([_make_session()])

        monitor.on_sessions_update([{"DeviceId": "device-1", "DeviceName": "LG TV"}])

        self.assertEqual("", monitor._monitored_state)


if __name__ == "__main__":
    unittest.main()
