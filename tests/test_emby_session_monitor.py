import unittest
from unittest.mock import MagicMock

from home_cinema_control.media_servers.emby.session_monitor import EmbySessionMonitor
from home_cinema_control.playback.intent import PlaybackOrigin
from home_cinema_control.playback.state import BridgePlaybackState


def _make_session(
    device_id="device-1",
    device_name="LG TV",
    user_id="user-1",
    item_id="42",
    item_name="Blade Runner 2049",
    item_type="Movie",
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
            "Type": item_type,
            "Path": item_path,
            "Container": "mkv",
        },
        "PlayState": {
            "AudioStreamIndex": audio_index,
            "SubtitleStreamIndex": subtitle_index,
            "PositionTicks": position_ticks,
        },
    }


def _make_item_info(item_id="42", user_data=None):
    return {
        "Id": item_id,
        "UserData": user_data or {"Played": False, "PlayCount": 0},
        "MediaSources": [],
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


class EmbySessionMonitorTest(unittest.TestCase):
    def setUp(self):
        self.emby_session = MagicMock()
        self.emby_session.get_item_info.return_value = _make_item_info()
        self.emby_session.is_item_path_in_library.return_value = True
        self.playback_state = BridgePlaybackState()

        self.dispatcher = MagicMock()
        self.config = _config()

    def _monitor(self, config=None):
        return EmbySessionMonitor(
            emby_session=self.emby_session,
            playback_state=self.playback_state,
            config_provider=lambda: config or self.config,
            dispatcher=self.dispatcher,
        )

    # -------------------------------------------------------------------------
    # No-op cases
    # -------------------------------------------------------------------------

    def test_no_controlled_device_does_nothing(self):
        monitor = self._monitor(config=_config(device_id=""))
        monitor.on_sessions_update([_make_session()])
        self.dispatcher.dispatch.assert_not_called()

    def test_no_matching_session_does_nothing(self):
        monitor = self._monitor()
        monitor.on_sessions_update([_make_session(device_id="other-device")])
        self.dispatcher.dispatch.assert_not_called()

    def test_item_not_in_library_does_not_dispatch(self):
        self.emby_session.is_item_path_in_library.return_value = False
        monitor = self._monitor()
        monitor.on_sessions_update([_make_session()])
        self.dispatcher.dispatch.assert_not_called()

    def test_item_in_active_library_without_verified_path_mapping_does_not_dispatch(self):
        monitor = self._monitor(config=_config(path_mappings=[
            {
                "source_path": "/movies",
                "player_path": "/NAS/Movies",
                "protocol": "nfs",
                "verified": False,
            }
        ]))

        monitor.on_sessions_update([_make_session()])

        self.dispatcher.dispatch.assert_not_called()

    # -------------------------------------------------------------------------
    # Dispatch cases
    # -------------------------------------------------------------------------

    def test_new_item_in_library_dispatches_intent(self):
        monitor = self._monitor()
        monitor.on_sessions_update([_make_session()])
        self.dispatcher.dispatch.assert_called_once()
        _intent, kwargs = self.dispatcher.dispatch.call_args
        self.assertEqual(kwargs["origin"], PlaybackOrigin.OBSERVED_TV_CLIENT)

    def test_dispatched_intent_has_correct_item_id(self):
        monitor = self._monitor()
        monitor.on_sessions_update([_make_session(item_id="99")])
        intent = self.dispatcher.dispatch.call_args[0][0]
        self.assertEqual("99", intent.media_item_id)

    def test_dispatched_intent_has_correct_audio_and_subtitle(self):
        monitor = self._monitor()
        monitor.on_sessions_update([_make_session(audio_index=2, subtitle_index=3)])
        intent = self.dispatcher.dispatch.call_args[0][0]
        self.assertEqual(2, intent.selected_audio_track_id)
        self.assertEqual(3, intent.selected_subtitle_track_id)

    def test_use_all_libraries_dispatches_without_library_check(self):
        monitor = self._monitor(config=_config(use_all_libraries=True))
        monitor.on_sessions_update([_make_session()])
        self.emby_session.is_item_path_in_library.assert_not_called()
        self.dispatcher.dispatch.assert_called_once()

    def test_inactive_library_is_skipped(self):
        libraries = [
            {"id": "lib-1", "name": "Movies", "active": False},
            {"id": "lib-2", "name": "TV", "active": True},
        ]
        self.emby_session.is_item_path_in_library.side_effect = (
            lambda view_id, path: view_id == "lib-2"
        )
        monitor = self._monitor(config=_config(libraries=libraries))
        monitor.on_sessions_update([_make_session()])
        self.emby_session.is_item_path_in_library.assert_called_once_with("lib-2", "/movies/blade_runner.mkv")
        self.dispatcher.dispatch.assert_called_once()

    # -------------------------------------------------------------------------
    # State tracking
    # -------------------------------------------------------------------------

    def test_same_item_on_second_update_does_not_dispatch_again(self):
        monitor = self._monitor()
        session = _make_session()
        monitor.on_sessions_update([session])
        monitor.on_sessions_update([session])
        self.dispatcher.dispatch.assert_called_once()

    def test_different_item_on_second_update_logs_but_does_not_dispatch(self):
        monitor = self._monitor()
        monitor.on_sessions_update([_make_session(item_name="Movie A")])
        self.dispatcher.dispatch.assert_called_once()

        self.dispatcher.reset_mock()
        monitor.on_sessions_update([_make_session(item_name="Movie B")])
        self.dispatcher.dispatch.assert_not_called()

    def test_item_stopped_resets_monitored_state(self):
        monitor = self._monitor()
        monitor.on_sessions_update([_make_session()])
        self.assertEqual("Blade Runner 2049", monitor._monitored_state)

        monitor.on_sessions_update([{"DeviceId": "device-1", "DeviceName": "LG TV"}])
        self.assertEqual("", monitor._monitored_state)

    # -------------------------------------------------------------------------
    # Bridge playback guard
    # -------------------------------------------------------------------------

    def test_bridge_active_preserves_monitored_state(self):
        monitor = self._monitor()
        monitor.on_sessions_update([_make_session()])
        self.assertEqual("Blade Runner 2049", monitor._monitored_state)

        self.playback_state.playstate = "Playing"
        monitor.on_sessions_update([{"DeviceId": "device-1"}])
        self.assertEqual("Blade Runner 2049", monitor._monitored_state)

    def test_bridge_inactive_clears_monitored_state(self):
        monitor = self._monitor()
        monitor.on_sessions_update([_make_session()])
        self.playback_state.playstate = "Free"
        monitor.on_sessions_update([{"DeviceId": "device-1"}])
        self.assertEqual("", monitor._monitored_state)


if __name__ == "__main__":
    unittest.main()
