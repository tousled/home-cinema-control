import unittest

from home_cinema_control.devices.oppo.media_control_playback import (
    OppoMediaControlPlayback,
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
        mount_nfs_response='{"success":true,"nfsMntPath":"/mnt/nfs1"}',
        mount_samba_with_id_responses=None,
        audio_menu_responses=None,
        audio_selection_response='{"success":false,"msg":""}',
        subtitle_menu_responses=None,
    ):
        self.calls = []
        self.mount_nfs_response = mount_nfs_response
        self.mount_samba_with_id_responses = list(
            mount_samba_with_id_responses
            or ['{"success":true,"cifsMntPath":"/mnt/cifs1"}']
        )
        self.audio_menu_responses = list(
            audio_menu_responses
            or ['{"audio_list":[{"index":1,"selected":true}]}']
        )
        self.audio_selection_response = audio_selection_response
        self.subtitle_menu_responses = list(
            subtitle_menu_responses
            or ['{"subtitle_list":[{"index":1,"selected":true}]}']
        )

    def sign_in(self):
        self.calls.append("sign_in")
        return OppoCommandResponse.from_text('{"success":true}')

    def login_nfs_server(self, server):
        self.calls.append(("login_nfs_server", server))
        return OppoCommandResponse.from_text('{"success":true}')

    def login_samba_without_id(self, server):
        self.calls.append(("login_samba_without_id", server))
        return OppoCommandResponse.from_text('{"success":true}')

    def mount_nfs_folder(self, *, server, folder, timeout):
        self.calls.append(("mount_nfs_folder", server, folder, timeout))
        return OppoCommandResponse.from_text(self.mount_nfs_response)

    def mount_samba_folder(self, *, server, folder, timeout):
        self.calls.append(("mount_samba_folder", server, folder, timeout))
        return OppoCommandResponse.from_text(
            '{"success":true,"cifsMntPath":"/mnt/cifs1"}'
        )

    def mount_samba_folder_with_id(self, server, folder, username, password, *, timeout):
        self.calls.append(("mount_samba_folder_with_id", server, folder, username, password, timeout))
        if len(self.mount_samba_with_id_responses) > 1:
            return OppoCommandResponse.from_text(self.mount_samba_with_id_responses.pop(0))
        return OppoCommandResponse.from_text(self.mount_samba_with_id_responses[0])

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


class RecordingNetworkPlaybackStarter:
    def __init__(self):
        self.calls = []

    def prime_samba_mount(self, server, folder):
        self.calls.append(("prime_samba_mount", server, folder))


class OppoMediaControlPlaybackTest(unittest.TestCase):
    def test_starts_nfs_playback_without_legacy_refresh_or_remote_key(self):
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
            [
                "sign_in",
                ("login_nfs_server", "NAS"),
                ("mount_nfs_folder", "NAS", "Movies", 30),
                ("play_normal_file", "/mnt/nfs1", "NAS", "Movie.mkv", "0", 30),
            ],
            client.calls,
        )
        self.assertNotIn("get_setup_menu", client.calls)
        self.assertNotIn(("send_remote_key", "EJT"), client.calls)
        self.assertNotIn(("send_remote_key", "QPW"), client.calls)

    def test_starts_samba_playback_when_smb_is_active(self):
        client = RecordingMediaControlClient()
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
        self.assertEqual(
            [
                "sign_in",
                ("login_samba_without_id", "NAS"),
                ("mount_samba_folder_with_id", "NAS", "Movies", "user", "pass", 30),
                ("play_normal_file", "/mnt/cifs1", "NAS", "Movie.mkv", "0", 30),
            ],
            client.calls,
        )

    def test_mapping_protocol_can_use_samba_when_global_default_is_nfs(self):
        client = RecordingMediaControlClient()
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
        self.assertEqual("/mnt/cifs1", result.mounted_path)
        self.assertEqual(
            [
                "sign_in",
                ("login_samba_without_id", "NAS"),
                ("mount_samba_folder_with_id", "NAS", "Trailers", "user", "pass", 30),
                ("play_normal_file", "/mnt/cifs1", "NAS", "Trailer.mkv", "0", 30),
            ],
            client.calls,
        )

    def test_primes_samba_mount_before_real_mount_when_pre_mount_smb_enabled(self):
        client = RecordingMediaControlClient()
        network_playback_starter = RecordingNetworkPlaybackStarter()
        playback = OppoMediaControlPlayback(
            {
                "oppo": {
                    "use_smb": True,
                    "pre_mount_smb": True,
                    "nfs_mount_timeout_seconds": 30,
                    "playback_start_timeout_seconds": 30,
                },
                "smb": {"username": "user", "password": "pass"},
            },
            client=client,
            playback_state_waiter=_started_playback,
            network_playback_starter=network_playback_starter,
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
        self.assertEqual(
            [("prime_samba_mount", "NAS", "Movies")], network_playback_starter.calls
        )
        self.assertEqual(
            [
                "sign_in",
                ("login_samba_without_id", "NAS"),
                ("mount_samba_folder_with_id", "NAS", "Movies", "user", "pass", 30),
                ("play_normal_file", "/mnt/cifs1", "NAS", "Movie.mkv", "0", 30),
            ],
            client.calls,
        )

    def test_does_not_prime_samba_mount_when_pre_mount_smb_disabled(self):
        client = RecordingMediaControlClient()
        network_playback_starter = RecordingNetworkPlaybackStarter()
        playback = OppoMediaControlPlayback(
            {
                "oppo": {
                    "use_smb": True,
                    "pre_mount_smb": False,
                    "nfs_mount_timeout_seconds": 30,
                    "playback_start_timeout_seconds": 30,
                },
                "smb": {"username": "user", "password": "pass"},
            },
            client=client,
            playback_state_waiter=_started_playback,
            network_playback_starter=network_playback_starter,
        )

        playback.start_playback(
            OppoPlaybackStartRequest(
                media_location=PlayerMediaFileLocation(
                    content_server="NAS",
                    content_directory="Movies",
                    playback_file_name="Movie.mkv",
                    playback_file_format="mkv",
                )
            )
        )

        self.assertEqual([], network_playback_starter.calls)

    def test_does_not_prime_samba_mount_for_nfs_even_when_pre_mount_smb_enabled(self):
        client = RecordingMediaControlClient()
        network_playback_starter = RecordingNetworkPlaybackStarter()
        playback = OppoMediaControlPlayback(
            {
                "oppo": {
                    "use_smb": False,
                    "pre_mount_smb": True,
                    "nfs_mount_timeout_seconds": 30,
                    "playback_start_timeout_seconds": 30,
                }
            },
            client=client,
            playback_state_waiter=_started_playback,
            network_playback_starter=network_playback_starter,
        )

        playback.start_playback(
            OppoPlaybackStartRequest(
                media_location=PlayerMediaFileLocation(
                    content_server="NAS",
                    content_directory="Movies",
                    playback_file_name="Movie.mkv",
                    playback_file_format="mkv",
                )
            )
        )

        self.assertEqual([], network_playback_starter.calls)

    def test_does_not_fall_back_to_nfs_when_smb_selected_and_mount_fails(self):
        # NFS and SMB don't share an addressing scheme on every NAS (some
        # require a `volume1/`-style root prefix for NFS that SMB share
        # names omit), so silently retrying the user's selected protocol
        # under a different one reuses a folder string that may not be
        # valid there. Real playback mounts the protocol the mapping
        # selected and fails cleanly if that fails — see HCC-TASK-019.
        client = RecordingMediaControlClient(
            mount_samba_with_id_responses=['{"success":false,"retInfo":"failed"}'],
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
        self.assertEqual(
            [
                "sign_in",
                ("login_samba_without_id", "NAS"),
                ("mount_samba_folder_with_id", "NAS", "Movies", "user", "pass", 30),
            ],
            client.calls,
        )

    def test_does_not_fall_back_to_smb_when_nfs_selected_and_mount_fails(self):
        client = RecordingMediaControlClient(
            mount_nfs_response='{"success":false,"retInfo":"failed"}',
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
        self.assertEqual(
            [
                "sign_in",
                ("login_nfs_server", "NAS"),
                ("mount_nfs_folder", "NAS", "Movies", 30),
            ],
            client.calls,
        )

    def test_retries_samba_mount_once_on_id_error(self):
        client = RecordingMediaControlClient(
            mount_samba_with_id_responses=[
                '{"success":false,"retInfo":"id_error"}',
                '{"success":true,"cifsMntPath":"/mnt/cifs1"}',
            ]
        )
        playback = OppoMediaControlPlayback(
            {
                "oppo": {
                    "use_smb": True,
                    "nfs_mount_timeout_seconds": 30,
                    "playback_start_timeout_seconds": 30,
                },
                "smb": {"username": "guest", "password": ""},
            },
            client=client,
            playback_state_waiter=_started_playback,
            sleep=lambda _: None,
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
        self.assertEqual(
            [
                "sign_in",
                ("login_samba_without_id", "NAS"),
                ("mount_samba_folder_with_id", "NAS", "Movies", "guest", "", 30),
                ("mount_samba_folder_with_id", "NAS", "Movies", "guest", "", 30),
                ("play_normal_file", "/mnt/cifs1", "NAS", "Movie.mkv", "0", 30),
            ],
            client.calls,
        )

    def test_treats_optical_mount_failure_as_success_when_oppo_reports_active(self):
        client = RecordingMediaControlClient(
            mount_nfs_response='{"success":false,"retInfo":"failed"}',
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
        self.assertEqual(
            [
                "sign_in",
                ("login_nfs_server", "NAS"),
                ("mount_nfs_folder", "NAS", "Movies", 30),
            ],
            client.calls,
        )

    def test_treats_optical_mount_timeout_as_success_when_oppo_reports_active(self):
        client = RecordingMediaControlClient(
            mount_nfs_response='{"success":false,"retInfo":"Timeout in Mount Request"}',
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

    def test_keeps_non_optical_mount_timeout_as_failure(self):
        client = RecordingMediaControlClient(
            mount_nfs_response='{"success":false,"retInfo":"Timeout in Mount Request"}',
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
