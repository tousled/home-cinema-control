import unittest
from unittest.mock import patch

from home_cinema_control.devices.oppo.models import OppoCommandResponse
from home_cinema_control.web.path_config import (
    _login_and_mount,
    build_test_media_path,
    check_path_configuration,
    get_mount_path,
    normalize_config_path,
    preview_path_mapping,
)


class WebPathConfigTest(unittest.TestCase):
    def test_normalize_config_path_accepts_windows_separators(self):
        self.assertEqual(
            "/volume1/Video/Movies",
            normalize_config_path(r"\\volume1\Video\Movies"),
        )

    def test_build_test_media_path_requires_emby_path(self):
        with self.assertRaisesRegex(ValueError, "source_path is required"):
            build_test_media_path({"source_path": ""})

    def test_get_mount_path_maps_emby_path_to_oppo_path(self):
        mount_path = get_mount_path(
            "/volume1/Video/Movies/test.mkv",
            {
                "source_path": "/volume1/Video/Movies",
                "player_path": "/192.168.1.100/volume1/Video/Movies",
            },
        )

        self.assertEqual(
            {
                "Servidor": "192.168.1.100",
                "Carpeta": "volume1/Video/Movies",
                "Fichero": "test.mkv",
            },
            mount_path,
        )

    def test_get_mount_path_requires_oppo_server_and_folder(self):
        with self.assertRaisesRegex(ValueError, "must include server and folder"):
            get_mount_path(
                "/volume1/Video/Movies/test.mkv",
                {
                    "source_path": "/volume1/Video/Movies",
                    "player_path": "/NAS",
                },
            )

    @patch("home_cinema_control.web.path_config.test_mount_path")
    def test_path_configuration_tests_mapped_folder(self, test_mount_path):
        test_mount_path.return_value = "OK"

        result = check_path_configuration(
            {"app": {"log_level": 0}},
            {
                "source_path": "/volume1/Video/Movies",
                "player_path": "/192.168.1.100/volume1/Video/Movies",
            },
        )

        self.assertEqual("OK", result)
        test_mount_path.assert_called_once_with(
            {"app": {"log_level": 0}},
            "192.168.1.100",
            "volume1/Video/Movies",
            protocol=None,
        )

    @patch("home_cinema_control.web.path_config.test_mount_path")
    def test_path_configuration_passes_mapping_protocol_to_mount_test(self, test_mount_path):
        test_mount_path.return_value = "OK"

        result = check_path_configuration(
            {"oppo": {"use_smb": False}},
            {
                "source_path": "/volume1/Video/Trailers",
                "player_path": "/NAS/Video/Trailers",
                "protocol": "cifs",
            },
        )

        self.assertEqual("OK", result)
        test_mount_path.assert_called_once_with(
            {"oppo": {"use_smb": False}},
            "NAS",
            "Video/Trailers",
            protocol="cifs",
        )

    @patch("home_cinema_control.web.path_config.test_mount_path")
    def test_path_configuration_returns_validation_error_without_mounting(
        self, test_mount_path
    ):
        result = check_path_configuration(
            {"app": {"log_level": 0}},
            {
                "source_path": "/volume1/Video/Movies",
                "player_path": "/",
            },
        )

        self.assertEqual("INVALID PATH CONFIG: player_path is required.", result)
        test_mount_path.assert_not_called()


class FakeOppoClient:
    def __init__(
        self,
        *,
        nfs_response='{"success":true,"nfsMntPath":"/mnt/nfs1"}',
        samba_response='{"success":true,"cifsMntPath":"/mnt/cifs1"}',
    ):
        self.calls = []
        self.nfs_response = nfs_response
        self.samba_response = samba_response

    def login_nfs_server(self, server):
        self.calls.append(("login_nfs_server", server))
        return OppoCommandResponse.from_text('{"success":true}')

    def login_samba_without_id(self, server):
        self.calls.append(("login_samba_without_id", server))
        return OppoCommandResponse.from_text('{"success":true}')

    def mount_nfs_folder(self, *, server, folder, timeout):
        self.calls.append(("mount_nfs_folder", server, folder, timeout))
        return OppoCommandResponse.from_text(self.nfs_response)

    def mount_samba_folder(self, *, server, folder, timeout):
        self.calls.append(("mount_samba_folder", server, folder, timeout))
        return OppoCommandResponse.from_text(self.samba_response)

    def mount_samba_folder_with_id(self, *, server, folder, username, password, timeout):
        self.calls.append(
            ("mount_samba_folder_with_id", server, folder, username, password, timeout)
        )
        return OppoCommandResponse.from_text(self.samba_response)


class LoginAndMountTest(unittest.TestCase):
    """_login_and_mount tests the configured protocol exactly once and never falls back to
    the other one. A "Probar ruta" pass must reflect the protocol the user actually selected
    (use_smb) the same way real playback does — silently retrying the other protocol on
    failure would mask real problems and, on NAS layouts where NFS and SMB don't share an
    addressing scheme (see HCC-TASK-019), would attempt a structurally invalid path anyway.

    mount_smb_share/mount_nfs_share build their own OPPO client internally, so only the
    login call still goes through the injected FakeOppoClient — the mount call is verified via
    the patched wrappers."""

    def _config(self):
        return {"oppo": {"always_on": True, "nfs_mount_timeout_seconds": 30}, "smb": {}}

    @patch("home_cinema_control.web.path_config.mount_smb_share")
    @patch("home_cinema_control.web.path_config.mount_nfs_share")
    def test_nfs_selected_mounts_via_nfs_only(self, mount_nfs, mount_smb):
        mount_nfs.return_value = OppoCommandResponse.from_text(
            '{"success":true,"nfsMntPath":"/mnt/nfs1"}'
        )
        client = FakeOppoClient()
        config = self._config()
        response = _login_and_mount(
            client=client, config=config, server="NAS", folder="Movies",
            use_nfs=True, oppo=config["oppo"],
        )
        self.assertTrue(response.is_successful)
        self.assertEqual([("login_nfs_server", "NAS")], client.calls)
        mount_nfs.assert_called_once_with("NAS", "Movies", config)
        mount_smb.assert_not_called()

    @patch("home_cinema_control.web.path_config.mount_smb_share")
    @patch("home_cinema_control.web.path_config.mount_nfs_share")
    def test_nfs_selected_failure_does_not_try_smb(self, mount_nfs, mount_smb):
        mount_nfs.return_value = OppoCommandResponse.from_text(
            '{"success":false,"retInfo":"failed"}'
        )
        client = FakeOppoClient()
        config = self._config()
        response = _login_and_mount(
            client=client, config=config, server="NAS", folder="Movies",
            use_nfs=True, oppo=config["oppo"],
        )
        self.assertFalse(response.is_successful)
        mount_smb.assert_not_called()

    @patch("home_cinema_control.web.path_config.mount_smb_share")
    @patch("home_cinema_control.web.path_config.mount_nfs_share")
    def test_smb_selected_mounts_via_smb_only(self, mount_nfs, mount_smb):
        mount_smb.return_value = OppoCommandResponse.from_text(
            '{"success":true,"cifsMntPath":"/mnt/cifs1"}'
        )
        client = FakeOppoClient()
        config = self._config()
        response = _login_and_mount(
            client=client, config=config, server="NAS", folder="Movies",
            use_nfs=False, oppo=config["oppo"],
        )
        self.assertTrue(response.is_successful)
        self.assertEqual([("login_samba_without_id", "NAS")], client.calls)
        mount_smb.assert_called_once_with("NAS", "Movies", config)
        mount_nfs.assert_not_called()

    @patch("home_cinema_control.web.path_config.mount_smb_share")
    @patch("home_cinema_control.web.path_config.mount_nfs_share")
    def test_smb_selected_failure_does_not_fall_back_to_nfs(self, mount_nfs, mount_smb):
        mount_smb.return_value = OppoCommandResponse.from_text(
            '{"success":false,"retInfo":"id_error"}'
        )
        client = FakeOppoClient()
        config = self._config()
        response = _login_and_mount(
            client=client, config=config, server="NAS", folder="Movies",
            use_nfs=False, oppo=config["oppo"],
        )
        self.assertFalse(response.is_successful)
        self.assertEqual([("login_samba_without_id", "NAS")], client.calls)
        mount_nfs.assert_not_called()


class PreviewPathMappingTest(unittest.TestCase):
    def test_preview_returns_server_and_folder(self):
        result = preview_path_mapping({
            "source_path": "/volume1/Video/Movies",
            "player_path": "/192.168.1.100/volume1/Video/Movies",
        })
        self.assertEqual("192.168.1.100", result["server"])
        self.assertEqual("volume1/Video/Movies", result["folder"])
        self.assertEqual("/volume1/Video/Movies", result["source_prefix"])
        self.assertEqual("/192.168.1.100/volume1/Video/Movies", result["player_prefix"])

    def test_preview_raises_for_missing_source_path(self):
        with self.assertRaises(ValueError):
            preview_path_mapping({"source_path": "", "player_path": "/NAS/Movies"})

    def test_preview_raises_for_root_only_player_path(self):
        with self.assertRaises(ValueError):
            preview_path_mapping({"source_path": "/videos", "player_path": "/"})

    def test_preview_normalizes_windows_paths(self):
        result = preview_path_mapping({
            "source_path": r"\\server\videos",
            "player_path": r"\\nas\videos",
        })
        self.assertIsNotNone(result["server"])


if __name__ == "__main__":
    unittest.main()
