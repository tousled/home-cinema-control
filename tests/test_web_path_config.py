import unittest
from unittest.mock import patch

from home_cinema_control.devices.oppo.mounted_share import OppoMountedShare
from home_cinema_control.devices.oppo.network_mount_service import (
    OppoMountResult,
    OppoNetworkFolderProtocol,
)
from home_cinema_control.web.path_config import (
    build_test_media_path,
    check_path_configuration,
    get_mount_path,
    normalize_config_path,
    preview_path_mapping,
    test_mount_path as call_test_mount_path,
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


class TestMountPathTest(unittest.TestCase):
    """test_mount_path mounts the configured protocol exactly once and never falls back to
    the other one. A "Probar ruta" pass must reflect the protocol the user actually selected
    (use_smb) the same way real playback does — silently retrying the other protocol on
    failure would mask real problems and, on NAS layouts where NFS and SMB don't share an
    addressing scheme (see HCC-TASK-019), would attempt a structurally invalid path anyway.

    The activate/login/mount/retry sequence itself is tested in detail against
    OppoNetworkMountService directly (test_oppo_network_mount_service.py) — these tests
    only check that test_mount_path resolves the right protocol and maps the result."""

    def _config(self):
        return {"oppo": {"always_on": True, "nfs_mount_timeout_seconds": 30}, "smb": {}}

    @patch("home_cinema_control.web.path_config.OppoNetworkMountService")
    def test_nfs_selected_mounts_via_nfs_only(self, mount_service_cls):
        mount_service = mount_service_cls.return_value
        mount_service.mount.return_value = OppoMountResult(
            successful=True,
            mounted_share=OppoMountedShare(
                server="NAS", folder="Movies", mount_path="/mnt/nfs1", is_nfs=True
            ),
            failure_stage=None,
            detail="",
        )

        result = call_test_mount_path(self._config(), "NAS", "Movies", protocol="nfs")

        self.assertEqual("OK", result)
        network_folder = mount_service.mount.call_args.args[0]
        self.assertEqual(OppoNetworkFolderProtocol.NFS, network_folder.protocol)

    def test_nfs_selected_failure_does_not_try_smb(self):
        with patch("home_cinema_control.web.path_config.OppoNetworkMountService") as mount_service_cls:
            mount_service = mount_service_cls.return_value
            mount_service.mount.return_value = OppoMountResult(
                successful=False, mounted_share=None, failure_stage="mount", detail="failed"
            )

            result = call_test_mount_path(self._config(), "NAS", "Movies", protocol="nfs")

        self.assertEqual("OPPO_MOUNT_FAILED: failed", result)
        network_folder = mount_service.mount.call_args.args[0]
        self.assertEqual(OppoNetworkFolderProtocol.NFS, network_folder.protocol)

    @patch("home_cinema_control.web.path_config.OppoNetworkMountService")
    def test_smb_selected_mounts_via_smb_only(self, mount_service_cls):
        mount_service = mount_service_cls.return_value
        mount_service.mount.return_value = OppoMountResult(
            successful=True,
            mounted_share=OppoMountedShare(
                server="NAS", folder="Movies", mount_path="/mnt/cifs1", is_nfs=False
            ),
            failure_stage=None,
            detail="",
        )

        result = call_test_mount_path(self._config(), "NAS", "Movies", protocol="cifs")

        self.assertEqual("OK", result)
        network_folder = mount_service.mount.call_args.args[0]
        self.assertEqual(OppoNetworkFolderProtocol.CIFS, network_folder.protocol)

    @patch("home_cinema_control.web.path_config.OppoNetworkMountService")
    def test_smb_selected_failure_does_not_fall_back_to_nfs(self, mount_service_cls):
        mount_service = mount_service_cls.return_value
        mount_service.mount.return_value = OppoMountResult(
            successful=False, mounted_share=None, failure_stage="mount", detail="id_error"
        )

        result = call_test_mount_path(self._config(), "NAS", "Movies", protocol="cifs")

        self.assertEqual("OPPO_MOUNT_FAILED: id_error", result)
        self.assertEqual(1, mount_service.mount.call_count)
        network_folder = mount_service.mount.call_args.args[0]
        self.assertEqual(OppoNetworkFolderProtocol.CIFS, network_folder.protocol)

    @patch("home_cinema_control.web.path_config.OppoNetworkMountService")
    def test_control_api_unavailable_is_reported_without_mounting(self, mount_service_cls):
        mount_service = mount_service_cls.return_value
        mount_service.mount.return_value = OppoMountResult(
            successful=False,
            mounted_share=None,
            failure_stage="control_api",
            detail="OPPO control API is not reachable",
        )

        result = call_test_mount_path(self._config(), "NAS", "Movies", protocol="nfs")

        self.assertEqual("OPPO_UNAVAILABLE: OPPO control API is not reachable", result)

    @patch("home_cinema_control.web.path_config.unmount_oppo_path")
    @patch("home_cinema_control.web.path_config.OppoNetworkMountService")
    def test_unmount_after_test_uses_autoscript_timeout_not_mount_timeout(
            self, mount_service_cls, unmount_oppo_path
    ):
        # Regression test: this call site used to pass nfs_mount_timeout_seconds
        # (30s, meant for mounting) instead of autoscript_unmount_timeout_seconds
        # (3s, meant for the unmount telnet session) — a real-device 30s stall on
        # every "Probar ruta" pass with Autoscript enabled, even though the
        # equivalent real-playback-finish call site already used the right key.
        mount_service = mount_service_cls.return_value
        mount_service.mount.return_value = OppoMountResult(
            successful=True,
            mounted_share=OppoMountedShare(
                server="NAS", folder="Movies", mount_path="/mnt/cifs1", is_nfs=False
            ),
            failure_stage=None,
            detail="",
        )
        config = {
            "oppo": {
                "always_on": True,
                "ip": "192.168.1.50",
                "nfs_mount_timeout_seconds": 30,
                "autoscript": True,
                "autoscript_unmount_timeout_seconds": 3,
            },
            "smb": {},
        }

        call_test_mount_path(config, "NAS", "Movies", protocol="cifs")

        unmount_oppo_path.assert_called_once()
        self.assertEqual(3, unmount_oppo_path.call_args.kwargs["timeout"])

    @patch("home_cinema_control.web.path_config.unmount_oppo_path")
    @patch("home_cinema_control.web.path_config.OppoNetworkMountService")
    def test_unmount_after_test_skips_nfs_mounts(
            self, mount_service_cls, unmount_oppo_path
    ):
        # Regression test: real playback (playback_adapters.py) already skips
        # the Autoscript unmount for NFS mounts (it only ever applies to
        # CIFS/SMB) — this call site ("Probar ruta") never got the same gate,
        # so testing an NFS mapping with Autoscript enabled would needlessly
        # attempt a telnet unmount that was never meant to run against NFS.
        mount_service = mount_service_cls.return_value
        mount_service.mount.return_value = OppoMountResult(
            successful=True,
            mounted_share=OppoMountedShare(
                server="NAS", folder="Movies", mount_path="/mnt/nfs1", is_nfs=True
            ),
            failure_stage=None,
            detail="",
        )
        config = {
            "oppo": {
                "always_on": True,
                "ip": "192.168.1.50",
                "nfs_mount_timeout_seconds": 30,
                "autoscript": True,
                "autoscript_unmount_timeout_seconds": 3,
            },
            "smb": {},
        }

        call_test_mount_path(config, "NAS", "Movies", protocol="nfs")

        unmount_oppo_path.assert_not_called()


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
