import unittest

from home_cinema_control.devices.oppo.media_control_playback import (
    OppoMediaControlPlayback,
)
from home_cinema_control.devices.oppo.mounted_share import OppoMountedShare
from home_cinema_control.devices.oppo.network_mount_service import (
    OppoMountResult,
    OppoNetworkFolderProtocol,
)
from home_cinema_control.devices.oppo.playback_state import (
    OppoPlaybackCategory,
    OppoPlaybackStatus,
)
from home_cinema_control.playback.startup.models import (
    OppoPlaybackStartRequest,
    PlayerMediaFileLocation,
)
from home_cinema_control.devices.oppo.models import OppoCommandResponse
from home_cinema_control.devices.oppo.playback_state_waiter import PlaybackStartupWaitResult


class RecordingMediaControlClient:
    def __init__(
        self,
        *,
        audio_menu_responses=None,
        audio_selection_response='{"success":false,"msg":""}',
        subtitle_menu_responses=None,
    ):
        self.calls = []
        self.audio_menu_responses = list(
            audio_menu_responses
            or ['{"audio_list":[{"index":1,"selected":true}]}']
        )
        self.audio_selection_response = audio_selection_response
        self.subtitle_menu_responses = list(
            subtitle_menu_responses
            or ['{"subtitle_list":[{"index":1,"selected":true}]}']
        )

    def play_normal_file(self, *, mounted_share, filename, index, timeout):
        self.calls.append(
            (
                "play_normal_file",
                mounted_share.mount_path,
                mounted_share.server,
                filename,
                index,
                timeout,
            )
        )
        return OppoCommandResponse.from_text('{"success":true}')

    def mounted_folder_contains_blu_ray_structure(
        self, *, mounted_share, relative_folder_path, timeout
    ):
        self.calls.append(
            (
                "mounted_folder_contains_blu_ray_structure",
                mounted_share.mount_path,
                relative_folder_path,
                timeout,
            )
        )
        return OppoCommandResponse.from_text('{"success":true}')

    def get_setup_menu(self):
        self.calls.append("get_setup_menu")
        return OppoCommandResponse.from_text("{}")

    def send_remote_key(self, key):
        self.calls.append(("send_remote_key", key))
        return OppoCommandResponse.from_text("{}")

    def get_playing_time(self):
        self.calls.append("get_playing_time")
        return OppoCommandResponse.from_text('{"cur_time":12,"total_time":120}')

    def set_play_time(self, position_ticks):
        self.calls.append(("set_play_time", position_ticks))
        return OppoCommandResponse.from_text('{"success":false,"msg":""}')

    def select_audio_track(self, audio_index):
        self.calls.append(("select_audio_track", audio_index))
        return OppoCommandResponse.from_text(self.audio_selection_response)

    def get_audio_menu(self, *, timeout=None):
        self.calls.append(("get_audio_menu", timeout))
        if len(self.audio_menu_responses) > 1:
            return OppoCommandResponse.from_text(self.audio_menu_responses.pop(0))

        return OppoCommandResponse.from_text(self.audio_menu_responses[0])

    def get_subtitle_menu(self, *, timeout=None):
        self.calls.append(("get_subtitle_menu", timeout))
        if len(self.subtitle_menu_responses) > 1:
            return OppoCommandResponse.from_text(self.subtitle_menu_responses.pop(0))

        return OppoCommandResponse.from_text(self.subtitle_menu_responses[0])

    def select_subtitle_track(self, subtitle_index):
        self.calls.append(("select_subtitle_track", subtitle_index))
        return OppoCommandResponse.from_text('{"success":true,"msg":""}')


class FakeNetworkMountService:
    """Stands in for OppoNetworkMountService: playback only needs to know
    what mount() returned, not how it got there (that's tested against the
    service directly, in test_oppo_network_mount_service.py)."""

    def __init__(self, result: OppoMountResult):
        self.calls = []
        self._result = result

    def mount(self, network_folder):
        self.calls.append(network_folder)
        return self._result


def _mounted(*, mount_path, server, folder, is_nfs) -> OppoMountResult:
    return OppoMountResult(
        successful=True,
        mounted_share=OppoMountedShare(
            server=server, folder=folder, mount_path=mount_path, is_nfs=is_nfs
        ),
        failure_stage=None,
        detail="",
    )


def _mount_failed(detail: str, *, failure_stage="mount") -> OppoMountResult:
    return OppoMountResult(
        successful=False,
        mounted_share=None,
        failure_stage=failure_stage,
        detail=detail,
    )


class OppoMediaControlPlaybackTest(unittest.TestCase):
    def test_starts_nfs_playback_without_legacy_refresh_or_remote_key(self):
        client = RecordingMediaControlClient()
        mount_service = FakeNetworkMountService(
            _mounted(mount_path="/mnt/nfs1", server="NAS", folder="Movies", is_nfs=True)
        )
        playback = OppoMediaControlPlayback(
            {
                "oppo": {
                    "use_smb": False,
                    "nfs_mount_timeout_seconds": 30,
                    "playback_start_timeout_seconds": 30,
                }
            },
            client=client,
            playback_state_waiter=_started_playback,
            network_mount_service=mount_service,
        )

        result = playback.start_playback(
            OppoPlaybackStartRequest(
                media_location=PlayerMediaFileLocation(
                    content_server="NAS",
                    content_directory="Movies",
                    playback_file_name="Movie.mkv",
                    playback_file_format="mkv",
                )
            )
        )

        self.assertTrue(result.successful)
        self.assertEqual("/mnt/nfs1", result.mounted_path)
        self.assertEqual(
            [("play_normal_file", "/mnt/nfs1", "NAS", "Movie.mkv", "0", 30)],
            client.calls,
        )
        self.assertEqual(1, len(mount_service.calls))
        self.assertEqual("NAS", mount_service.calls[0].server_name)
        self.assertEqual("Movies", mount_service.calls[0].folder_path)
        self.assertEqual(OppoNetworkFolderProtocol.NFS, mount_service.calls[0].protocol)
        self.assertNotIn("get_setup_menu", client.calls)
        self.assertNotIn(("send_remote_key", "EJT"), client.calls)
        self.assertNotIn(("send_remote_key", "QPW"), client.calls)

    def test_starts_samba_playback_when_smb_is_active(self):
        client = RecordingMediaControlClient()
        mount_service = FakeNetworkMountService(
            _mounted(mount_path="/mnt/cifs1", server="NAS", folder="Movies", is_nfs=False)
        )
        playback = OppoMediaControlPlayback(
            {
                "oppo": {
                    "use_smb": True,
                    "nfs_mount_timeout_seconds": 30,
                    "playback_start_timeout_seconds": 30,
                },
                "smb": {"username": "user", "password": "pass"},
            },
            client=client,
            playback_state_waiter=_started_playback,
            network_mount_service=mount_service,
        )

        result = playback.start_playback(
            OppoPlaybackStartRequest(
                media_location=PlayerMediaFileLocation(
                    content_server="NAS",
                    content_directory="Movies",
                    playback_file_name="Movie.mkv",
                    playback_file_format="mkv",
                )
            )
        )

        self.assertTrue(result.successful)
        self.assertEqual("/mnt/cifs1", result.mounted_path)
        self.assertEqual(OppoNetworkFolderProtocol.CIFS, mount_service.calls[0].protocol)

    def test_mapping_protocol_can_use_samba_when_global_default_is_nfs(self):
        client = RecordingMediaControlClient()
        mount_service = FakeNetworkMountService(
            _mounted(mount_path="/mnt/cifs1", server="NAS", folder="Trailers", is_nfs=False)
        )
        playback = OppoMediaControlPlayback(
            {
                "oppo": {
                    "use_smb": False,
                    "nfs_mount_timeout_seconds": 30,
                    "playback_start_timeout_seconds": 30,
                },
                "smb": {"username": "user", "password": "pass"},
            },
            client=client,
            playback_state_waiter=_started_playback,
            network_mount_service=mount_service,
        )

        result = playback.start_playback(
            OppoPlaybackStartRequest(
                network_protocol="cifs",
                media_location=PlayerMediaFileLocation(
                    content_server="NAS",
                    content_directory="Trailers",
                    playback_file_name="Trailer.mkv",
                    playback_file_format="mkv",
                ),
            )
        )

        self.assertTrue(result.successful)
        self.assertEqual(OppoNetworkFolderProtocol.CIFS, mount_service.calls[0].protocol)

    def test_mount_failure_reports_selected_protocol_without_retrying(self):
        # mount() is one call for one protocol; there is no fallback path to
        # assert against any more (see HCC-TASK-019: NFS/SMB don't share an
        # addressing scheme, so retrying under a different protocol would
        # attempt a structurally invalid path anyway).
        client = RecordingMediaControlClient()
        mount_service = FakeNetworkMountService(_mount_failed("failed"))
        playback = OppoMediaControlPlayback(
            {
                "oppo": {
                    "use_smb": True,
                    "nfs_mount_timeout_seconds": 30,
                    "playback_start_timeout_seconds": 30,
                },
                "smb": {"username": "user", "password": "pass"},
            },
            client=client,
            playback_state_waiter=_started_playback,
            network_mount_service=mount_service,
        )

        result = playback.start_playback(
            OppoPlaybackStartRequest(
                media_location=PlayerMediaFileLocation(
                    content_server="NAS",
                    content_directory="Movies",
                    playback_file_name="Movie.mkv",
                    playback_file_format="mkv",
                )
            )
        )

        self.assertFalse(result.successful)
        self.assertFalse(result.media_mounted)
        self.assertEqual("cifs", result.mount_protocol)
        self.assertEqual("failed", result.detail)
        self.assertEqual([], client.calls)

    def test_treats_optical_mount_failure_as_success_when_oppo_reports_active(self):
        client = RecordingMediaControlClient()
        mount_service = FakeNetworkMountService(_mount_failed("failed"))
        playback = OppoMediaControlPlayback(
            {
                "oppo": {
                    "use_smb": False,
                    "nfs_mount_timeout_seconds": 30,
                    "playback_start_timeout_seconds": 30,
                }
            },
            client=client,
            playback_state_waiter=_started_playback,
            network_mount_service=mount_service,
        )

        result = playback.start_playback(
            OppoPlaybackStartRequest(
                media_location=PlayerMediaFileLocation(
                    content_server="NAS",
                    content_directory="Movies",
                    playback_file_name="Movie.iso",
                    playback_file_format="blurayiso",
                )
            )
        )

        self.assertTrue(result.successful)
        self.assertIsNone(result.mounted_path)
        self.assertEqual(
            "Mount request failed, but OPPO reported active playback.",
            result.detail,
        )
        self.assertEqual([], client.calls)

    def test_keeps_non_optical_mount_failure_as_failure(self):
        client = RecordingMediaControlClient()
        mount_service = FakeNetworkMountService(_mount_failed("Timeout in Mount Request"))
        playback = OppoMediaControlPlayback(
            {
                "oppo": {
                    "use_smb": False,
                    "nfs_mount_timeout_seconds": 30,
                    "playback_start_timeout_seconds": 30,
                }
            },
            client=client,
            playback_state_waiter=_started_playback,
            network_mount_service=mount_service,
        )

        result = playback.start_playback(
            OppoPlaybackStartRequest(
                media_location=PlayerMediaFileLocation(
                    content_server="NAS",
                    content_directory="Movies",
                    playback_file_name="Movie.mkv",
                    playback_file_format="mkv",
                )
            )
        )

        self.assertFalse(result.successful)
        self.assertFalse(result.media_mounted)
        self.assertEqual("Timeout in Mount Request", result.detail)

    def test_reads_playback_position_from_media_control_endpoint(self):
        client = RecordingMediaControlClient()
        playback = OppoMediaControlPlayback(
            {
                "oppo": {
                    "use_smb": False,
                    "nfs_mount_timeout_seconds": 30,
                    "playback_start_timeout_seconds": 30,
                }
            },
            client=client,
            playback_state_waiter=_started_playback,
        )

        position = playback.get_playback_position()

        self.assertEqual(12, position.current_seconds)
        self.assertEqual(120, position.total_seconds)
        self.assertEqual(["get_playing_time"], client.calls)

    def test_sends_seek_and_audio_selection_through_media_control_client(self):
        client = RecordingMediaControlClient(
            audio_menu_responses=[
                '{"audio_list":[{"index":1,"selected":true},{"index":2,"selected":false}]}',
                '{"audio_list":[{"index":1,"selected":true},{"index":2,"selected":false}]}',
            ]
        )
        playback = OppoMediaControlPlayback(
            {
                "oppo": {
                    "use_smb": False,
                    "nfs_mount_timeout_seconds": 30,
                    "playback_start_timeout_seconds": 30,
                }
            },
            client=client,
            playback_state_waiter=_started_playback,
        )

        seek_result = playback.seek_to(120_000_000)
        audio_result = playback.select_audio_track(2)

        self.assertFalse(seek_result.successful)
        self.assertFalse(audio_result.successful)
        self.assertEqual(
            [
                ("set_play_time", 120_000_000),
                ("get_audio_menu", 1.0),
                ("select_audio_track", 2),
            ],
            client.calls,
        )

    def test_waits_for_audio_menu_to_contain_requested_track_before_selecting(self):
        client = RecordingMediaControlClient(
            audio_menu_responses=[
                '{"success":true,"audio_list":[]}',
                '{"success":true,"audio_list":[{"index":1,"selected":true},{"index":2,"selected":false}]}',
                '{"success":true,"audio_list":[{"index":1,"selected":false},{"index":2,"selected":true}]}',
            ],
            audio_selection_response='{"success":true,"msg":""}',
        )
        playback = OppoMediaControlPlayback(
            {
                "oppo": {
                    "use_smb": False,
                    "nfs_mount_timeout_seconds": 30,
                    "playback_start_timeout_seconds": 30,
                    "track_menu_ready_timeout_seconds": 1,
                    "track_menu_ready_poll_interval_seconds": 0,
                }
            },
            client=client,
            playback_state_waiter=_started_playback,
            sleep=lambda _: None,
        )

        result = playback.select_audio_track(2)

        self.assertTrue(result.successful)
        self.assertEqual(
            [
                ("get_audio_menu", 1.0),
                ("get_audio_menu", 1.0),
                ("select_audio_track", 2),
                ("get_audio_menu", 1.0),
            ],
            client.calls,
        )

    def test_reports_failed_audio_selection_when_oppo_keeps_previous_track(self):
        client = RecordingMediaControlClient(
            audio_menu_responses=[
                '{"success":true,"audio_list":[{"index":1,"selected":true},{"index":2,"selected":false}]}',
                '{"success":true,"audio_list":[{"index":1,"selected":true},{"index":2,"selected":false}]}',
            ],
            audio_selection_response='{"success":true,"msg":""}',
        )
        playback = OppoMediaControlPlayback(
            {
                "oppo": {
                    "use_smb": False,
                    "nfs_mount_timeout_seconds": 30,
                    "playback_start_timeout_seconds": 30,
                }
            },
            client=client,
            playback_state_waiter=_started_playback,
        )

        result = playback.select_audio_track(2)

        self.assertFalse(result.successful)
        self.assertIn("requested=2", result.detail)
        self.assertIn("selected=1", result.detail)

    def test_skips_audio_selection_when_requested_track_is_already_selected(self):
        client = RecordingMediaControlClient()
        playback = OppoMediaControlPlayback(
            {
                "oppo": {
                    "use_smb": False,
                    "nfs_mount_timeout_seconds": 30,
                    "playback_start_timeout_seconds": 30,
                }
            },
            client=client,
            playback_state_waiter=_started_playback,
        )

        result = playback.select_audio_track(1)

        self.assertTrue(result.successful)
        self.assertEqual([("get_audio_menu", 1.0)], client.calls)

    def test_skips_subtitle_selection_when_requested_track_is_already_selected(self):
        client = RecordingMediaControlClient()
        playback = OppoMediaControlPlayback(
            {
                "oppo": {
                    "use_smb": False,
                    "nfs_mount_timeout_seconds": 30,
                    "playback_start_timeout_seconds": 30,
                }
            },
            client=client,
            playback_state_waiter=_started_playback,
        )

        result = playback.select_subtitle_track(1)

        self.assertTrue(result.successful)
        self.assertEqual([("get_subtitle_menu", 1.0)], client.calls)

    def test_waits_for_subtitle_menu_to_contain_requested_track_before_selecting(self):
        client = RecordingMediaControlClient(
            subtitle_menu_responses=[
                '{"success":true,"subtitle_list":[]}',
                '{"success":true,"subtitle_list":[{"index":1,"selected":true},{"index":3,"selected":false}]}',
                '{"success":true,"subtitle_list":[{"index":1,"selected":false},{"index":3,"selected":true}]}',
            ]
        )
        playback = OppoMediaControlPlayback(
            {
                "oppo": {
                    "use_smb": False,
                    "nfs_mount_timeout_seconds": 30,
                    "playback_start_timeout_seconds": 30,
                    "track_menu_ready_timeout_seconds": 1,
                    "track_menu_ready_poll_interval_seconds": 0,
                }
            },
            client=client,
            playback_state_waiter=_started_playback,
            sleep=lambda _: None,
        )

        result = playback.select_subtitle_track(3)

        self.assertTrue(result.successful)
        self.assertEqual(
            [
                ("get_subtitle_menu", 1.0),
                ("get_subtitle_menu", 1.0),
                ("select_subtitle_track", 3),
                ("get_subtitle_menu", 1.0),
            ],
            client.calls,
        )

    def test_retries_subtitle_selection_once_when_activation_selects_first_track(self):
        client = RecordingMediaControlClient(
            subtitle_menu_responses=[
                '{"success":true,"subtitle_list":[{"index":0,"selected":true},{"index":1,"selected":false},{"index":2,"selected":false}]}',
                '{"success":true,"subtitle_list":[{"index":0,"selected":false},{"index":1,"selected":true},{"index":2,"selected":false}]}',
                '{"success":true,"subtitle_list":[{"index":0,"selected":false},{"index":1,"selected":false},{"index":2,"selected":true}]}',
            ]
        )
        playback = OppoMediaControlPlayback(
            {
                "oppo": {
                    "use_smb": False,
                    "nfs_mount_timeout_seconds": 30,
                    "playback_start_timeout_seconds": 30,
                    "track_selection_applied_timeout_seconds": 0,
                }
            },
            client=client,
            playback_state_waiter=_started_playback,
            sleep=lambda _: None,
        )

        result = playback.select_subtitle_track(2)

        self.assertTrue(result.successful)
        self.assertEqual(
            [
                ("get_subtitle_menu", 1.0),
                ("select_subtitle_track", 2),
                ("get_subtitle_menu", 1.0),
                ("select_subtitle_track", 2),
                ("get_subtitle_menu", 1.0),
            ],
            client.calls,
        )

    def test_reports_subtitle_selection_success_when_requested_track_becomes_selected(self):
        client = RecordingMediaControlClient(
            subtitle_menu_responses=[
                '{"subtitle_list":[{"index":1,"selected":true},{"index":3,"selected":false}]}',
                '{"subtitle_list":[{"index":1,"selected":false},{"index":3,"selected":true}]}',
            ]
        )
        playback = OppoMediaControlPlayback(
            {
                "oppo": {
                    "use_smb": False,
                    "nfs_mount_timeout_seconds": 30,
                    "playback_start_timeout_seconds": 30,
                }
            },
            client=client,
            playback_state_waiter=_started_playback,
        )

        result = playback.select_subtitle_track(3)

        self.assertTrue(result.successful)
        self.assertEqual(
            [
                ("get_subtitle_menu", 1.0),
                ("select_subtitle_track", 3),
                ("get_subtitle_menu", 1.0),
            ],
            client.calls,
        )

    def test_reports_failed_subtitle_selection_when_oppo_keeps_previous_track(self):
        client = RecordingMediaControlClient(
            subtitle_menu_responses=[
                '{"subtitle_list":[{"index":1,"selected":true},{"index":3,"selected":false}]}',
                '{"subtitle_list":[{"index":1,"selected":true},{"index":3,"selected":false}]}',
            ]
        )
        playback = OppoMediaControlPlayback(
            {
                "oppo": {
                    "use_smb": False,
                    "nfs_mount_timeout_seconds": 30,
                    "playback_start_timeout_seconds": 30,
                }
            },
            client=client,
            playback_state_waiter=_started_playback,
        )

        result = playback.select_subtitle_track(3)

        self.assertFalse(result.successful)
        self.assertIn("requested=3", result.detail)
        self.assertIn("selected=1", result.detail)


def _started_playback(**kwargs):
    return PlaybackStartupWaitResult(
        started=True,
        attempts=1,
        elapsed_seconds=0.1,
        status=OppoPlaybackStatus.PLAY,
        category=OppoPlaybackCategory.ACTIVE,
        raw_response="@OK PLAY",
    )


if __name__ == "__main__":
    unittest.main()
