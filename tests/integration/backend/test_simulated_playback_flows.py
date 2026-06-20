import pytest

from home_cinema_control.devices.oppo.playback_state import (
    OppoPlaybackCategory,
    OppoPlaybackStatus,
)
from home_cinema_control.devices.tv.models import TvInputTarget
from home_cinema_control.media_servers.emby.constants import EMBY_TICKS_PER_SECOND
from home_cinema_control.media_servers.emby.session_monitor import EmbySessionMonitor
from home_cinema_control.playback.diagnostics import diagnose_startup_result
from home_cinema_control.playback.intent import PlaybackIntent, PlaybackOrigin
from home_cinema_control.playback.request_preparation import prepare_playback_requests
from home_cinema_control.playback.startup.models import (
    DeviceCommandResult,
    OppoPlaybackPosition,
    OppoPlaybackStartResult,
    OppoPlaybackState,
    PlaybackStartupRequest,
)
from home_cinema_control.playback.startup.orchestrator import PlaybackStartupOrchestrator
from home_cinema_control.playback.state import BridgePlaybackState


pytestmark = pytest.mark.integration


def test_movies_nfs_protocol_reaches_oppo_startup_even_when_smb_exists():
    harness = ScenarioTestHarness(config=_playback_config(oppo_use_smb=True))

    prepared, result = harness.start_item("/volume1/Video/Movies/Movie.mkv")

    assert prepared.media_location.network_protocol == "nfs"
    assert prepared.oppo_playback_start_request.network_protocol == "nfs"
    assert harness.oppo.requests[0].network_protocol == "nfs"
    assert result.oppo_start_result.mount_protocol == "nfs"
    assert result.successful


def test_trailers_cifs_protocol_reaches_oppo_startup_when_global_smb_is_off():
    harness = ScenarioTestHarness(config=_playback_config(oppo_use_smb=False))

    prepared, result = harness.start_item("/volume1/Video/Trailers/Trailer.mkv")

    assert prepared.media_location.network_protocol == "cifs"
    assert prepared.oppo_playback_start_request.network_protocol == "cifs"
    assert harness.oppo.requests[0].network_protocol == "cifs"
    assert result.oppo_start_result.mount_protocol == "cifs"
    assert result.successful


def test_mount_failure_diagnostic_uses_selected_mapping_protocol():
    harness = ScenarioTestHarness(
        config=_playback_config(oppo_use_smb=False),
        oppo_result=OppoPlaybackStartResult(
            media_mounted=False,
            playback_command_accepted=False,
            playback_started_on_device=False,
            detail="id_error",
            mount_protocol="cifs",
        ),
    )

    _, result = harness.start_item("/volume1/Video/Trailers/Trailer.mkv")
    diagnostic = diagnose_startup_result(result, harness.config)

    assert diagnostic is not None
    assert diagnostic.code == "OPPO_MOUNT_FAILED"
    assert diagnostic.operation == "oppo_mount_startup"
    assert "SMB/CIFS" in diagnostic.reason
    assert "SMB credentials" in diagnostic.suggestion


def test_verified_but_not_intercepted_library_does_not_dispatch():
    session = FakeEmbySession(library_membership={"lib-movies": True})
    dispatcher = RecordingDispatcher()
    config = _monitor_config(
        libraries=[{"id": "lib-movies", "name": "Movies", "active": False}],
        path_mappings=[
            {
                "source_path": "/volume1/Video/Movies",
                "player_path": "/NAS/Movies",
                "protocol": "nfs",
                "verified": True,
            }
        ],
    )

    monitor = EmbySessionMonitor(
        emby_session=session,
        playback_state=BridgePlaybackState(),
        config_provider=lambda: config,
        dispatcher=dispatcher,
    )

    monitor.on_sessions_update([_session_update(path="/volume1/Video/Movies/Movie.mkv")])

    assert dispatcher.calls == []


def test_intercepted_library_without_verified_mapping_does_not_dispatch():
    session = FakeEmbySession(library_membership={"lib-movies": True})
    dispatcher = RecordingDispatcher()
    config = _monitor_config(
        libraries=[{"id": "lib-movies", "name": "Movies", "active": True}],
        path_mappings=[
            {
                "source_path": "/volume1/Video/Movies",
                "player_path": "/NAS/Movies",
                "protocol": "nfs",
                "verified": False,
            }
        ],
    )

    monitor = EmbySessionMonitor(
        emby_session=session,
        playback_state=BridgePlaybackState(),
        config_provider=lambda: config,
        dispatcher=dispatcher,
    )

    monitor.on_sessions_update([_session_update(path="/volume1/Video/Movies/Movie.mkv")])

    assert dispatcher.calls == []


def test_intercepted_library_with_verified_mapping_dispatches():
    session = FakeEmbySession(library_membership={"lib-movies": True})
    dispatcher = RecordingDispatcher()
    config = _monitor_config(
        libraries=[{"id": "lib-movies", "name": "Movies", "active": True}],
        path_mappings=[
            {
                "source_path": "/volume1/Video/Movies",
                "player_path": "/NAS/Movies",
                "protocol": "nfs",
                "verified": True,
            }
        ],
    )

    monitor = EmbySessionMonitor(
        emby_session=session,
        playback_state=BridgePlaybackState(),
        config_provider=lambda: config,
        dispatcher=dispatcher,
    )

    monitor.on_sessions_update([_session_update(path="/volume1/Video/Movies/Movie.mkv")])

    assert len(dispatcher.calls) == 1
    assert dispatcher.calls[0]["origin"] == PlaybackOrigin.OBSERVED_TV_CLIENT
    assert dispatcher.calls[0]["intent"].media_item_id == "item-1"


class ScenarioTestHarness:
    def __init__(self, *, config, oppo_result=None):
        self.config = config
        self.oppo = FakeOppoPlayback(result=oppo_result)
        self.television = FakeTelevision()
        self.av_receiver = FakeAvReceiver()
        self.orchestrator = PlaybackStartupOrchestrator(
            television=self.television,
            av_receiver=self.av_receiver,
            oppo_playback=self.oppo,
        )

    def start_item(self, path):
        prepared = prepare_playback_requests(
            config=self.config,
            intent=_intent(),
            item_info={
                "Path": path,
                "Container": "mkv",
                "RunTimeTicks": 7200 * EMBY_TICKS_PER_SECOND,
            },
            previous_tv_app_id_override="com.emby.app",
        )
        result = self.orchestrator.start_playback(
            PlaybackStartupRequest(
                output_switch_request=prepared.output_switch_request,
                oppo_start_request=prepared.oppo_playback_start_request,
            )
        )
        return prepared, result


class FakeOppoPlayback:
    def __init__(self, *, result=None):
        self._result = result
        self.requests = []

    def start_playback(self, request, *, on_waiting=None):
        self.requests.append(request)
        if self._result is not None:
            return self._result
        return OppoPlaybackStartResult(
            media_mounted=True,
            playback_command_accepted=True,
            playback_started_on_device=True,
            mount_protocol=request.network_protocol,
            mounted_path=f"/mnt/{request.network_protocol or 'auto'}1",
            playback_state=OppoPlaybackState(
                status=OppoPlaybackStatus.PLAY,
                category=OppoPlaybackCategory.ACTIVE,
                raw_response="PLAY",
                ok=True,
            ),
        )

    def get_playback_position(self):
        return OppoPlaybackPosition(current_seconds=10, total_seconds=7200)

    def get_playback_state(self):
        return OppoPlaybackState(
            status=OppoPlaybackStatus.PLAY,
            category=OppoPlaybackCategory.ACTIVE,
            raw_response="PLAY",
            ok=True,
        )

    def seek_to(self, position_ticks):
        return DeviceCommandResult.success()

    def select_audio_track(self, audio_index):
        return DeviceCommandResult.success()

    def select_subtitle_track(self, subtitle_index):
        return DeviceCommandResult.success()


class FakeTelevision:
    def __init__(self):
        self.inputs = []

    def get_current_app_id(self):
        return "com.webos.app.hdmi1"

    def switch_to_input(self, target: TvInputTarget):
        self.inputs.append(target.input_id)
        return DeviceCommandResult.success()

    def launch_app(self, app_id=None):
        return DeviceCommandResult.success()


class FakeAvReceiver:
    def __init__(self):
        self.powered_on = False
        self.inputs = []

    def power_on(self):
        self.powered_on = True
        return DeviceCommandResult.success()

    def switch_to_input(self, input_id):
        self.inputs.append(input_id)
        return DeviceCommandResult.success()

    def restore_tv_audio(self):
        return DeviceCommandResult.success()


class FakeEmbySession:
    def __init__(self, *, library_membership):
        self._library_membership = library_membership

    def get_item_info(self, user_id, item_id):
        return {
            "Id": item_id,
            "UserData": {"Played": False, "PlayCount": 0},
            "MediaSources": [],
        }

    def is_item_path_in_library(self, library_id, item_path):
        return self._library_membership.get(library_id, False)


class RecordingDispatcher:
    def __init__(self):
        self.calls = []

    def dispatch(self, intent, *, origin):
        self.calls.append({"intent": intent, "origin": origin})


def _playback_config(*, oppo_use_smb):
    return {
        "playback": {
            "path_mappings": [
                {
                    "source_path": "/volume1/Video/Movies",
                    "player_path": "/NAS-NFS/Video/Movies",
                    "protocol": "nfs",
                    "verified": True,
                },
                {
                    "source_path": "/volume1/Video/Series",
                    "player_path": "/NAS-NFS/Video/Series",
                    "protocol": "nfs",
                    "verified": True,
                },
                {
                    "source_path": "/volume1/Video/Trailers",
                    "player_path": "/NAS-SMB/Trailers",
                    "protocol": "cifs",
                    "verified": True,
                },
            ],
        },
        "oppo": {
            "always_on": False,
            "use_smb": oppo_use_smb,
            "playback_start_timeout_seconds": 30,
        },
        "smb": {"username": "nas-user", "password": "nas-pass"},
        "tv": {
            "enabled": True,
            "player_hdmi_input_id": 0,
            "available_hdmi_inputs": [{"id": "HDMI_3", "appId": "hdmi3"}],
        },
        "av": {"enabled": True, "player_hdmi_input": "BD"},
    }


def _monitor_config(*, libraries, path_mappings):
    return {
        "playback": {
            "hcc_controlled_device": "device-1",
            "use_all_libraries": False,
            "libraries": libraries,
            "path_mappings": path_mappings,
        }
    }


def _intent():
    return PlaybackIntent(
        media_item_id="item-1",
        media_source_id="source-1",
        source_user_id="user-1",
        source_client_session_id="session-1",
        source_device_id="device-1",
        source_device_name="Living Room TV",
        start_position_seconds=0,
        selected_audio_track_id=1,
        selected_subtitle_track_id=-1,
    )


def _session_update(*, path):
    return {
        "DeviceId": "device-1",
        "DeviceName": "Living Room TV",
        "UserId": "user-1",
        "NowPlayingItem": {
            "Id": "item-1",
            "Name": "Movie",
            "Type": "Movie",
            "Path": path,
            "Container": "mkv",
        },
        "PlayState": {
            "AudioStreamIndex": 1,
            "SubtitleStreamIndex": -1,
            "PositionTicks": 0,
        },
    }
