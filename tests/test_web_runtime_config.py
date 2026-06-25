import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from home_cinema_control.web.runtime_config import (
    apply_runtime_defaults,
    get_dir_folders,
)


class WebRuntimeConfigTest(unittest.TestCase):
    @patch("home_cinema_control.web.runtime_config.get_supported_av_models")
    @patch("home_cinema_control.web.runtime_config.get_supported_tv_models")
    def test_apply_runtime_defaults_adds_web_runtime_fields(
        self, tv_models, av_models
    ):
        tv_models.return_value = ["lg"]
        av_models.return_value = ["denon"]

        config = {
            "tv": {"enabled": True},
            "av": {"enabled": False},
            "media_servers": {
                "active": "emby",
                "providers": {
                    "emby": {
                        "playback": {
                            "path_mappings": [
                                {"name": "Movies"},
                                {"name": "Series", "verified": True},
                            ]
                        }
                    }
                },
            },
        }

        result = apply_runtime_defaults(config, version="0.5.1")

        self.assertIs(result, config)
        self.assertEqual("0.5.1", config["Version"])
        app = config["app"]
        self.assertEqual("es-ES", app["language"])
        self.assertEqual(5, app["status_refresh_interval_seconds"])
        self.assertFalse(app["include_prerelease"])
        self.assertEqual("tousled/home-cinema-control", app["release_repository"])
        self.assertEqual(10, app["version_check_timeout_seconds"])
        playback = config["media_servers"]["providers"]["emby"]["playback"]
        self.assertFalse(playback["use_all_libraries"])

        av = config["av"]
        self.assertFalse(av["enabled"])
        self.assertEqual("", av["ip"])
        self.assertEqual(23, av["port"])
        self.assertEqual("", av["model"])
        self.assertTrue(av["always_on"])
        self.assertEqual(0, av["hdmi_switch_delay_seconds"])
        self.assertEqual("", av["power_on_command"])
        self.assertEqual("", av["hdmi_input_command"])
        self.assertEqual("", av["power_off_command"])
        self.assertEqual([], av["available_hdmi_inputs"])
        self.assertEqual("", av["player_hdmi_input"])
        self.assertEqual(5, av["connection_timeout_seconds"])
        self.assertEqual(1, av["command_timeout_seconds"])
        self.assertEqual("", av["tv_connected_input"])

        tv = config["tv"]
        self.assertTrue(tv["enabled"])
        self.assertEqual("", tv["ip"])
        self.assertEqual("", tv["mac"])
        self.assertEqual("", tv["model"])
        self.assertEqual([], tv["available_hdmi_inputs"])
        self.assertEqual(0, tv["player_hdmi_input_id"])
        self.assertEqual("", tv["startup_script"])
        self.assertEqual("", tv["shutdown_script"])

        oppo = config["oppo"]
        self.assertEqual("", oppo["ip"])
        self.assertEqual("auto", oppo["observation_mode"])
        self.assertEqual(10, oppo["connection_timeout_seconds"])
        self.assertEqual(30, oppo["playback_start_timeout_seconds"])
        self.assertEqual(30, oppo["nfs_mount_timeout_seconds"])
        self.assertEqual(3.0, oppo["autoscript_unmount_timeout_seconds"])
        self.assertEqual(1.0, oppo["api_connect_timeout_seconds"])
        self.assertEqual(3, oppo["api_retry_attempts"])
        self.assertFalse(oppo["autoscript"])
        self.assertTrue(oppo["always_on"])
        self.assertFalse(oppo["bluray_disc_mode"])
        self.assertFalse(oppo["pre_mount_smb"])
        self.assertFalse(oppo["use_smb"])
        self.assertFalse(playback["path_mappings"][0]["verified"])
        self.assertTrue(playback["path_mappings"][1]["verified"])
        self.assertEqual(["lg"], config["tv_dirs"])
        self.assertEqual(["denon"], config["av_dirs"])
        self.assertEqual(["en-US", "es-ES"], config["langs"])

    @patch("home_cinema_control.web.runtime_config.get_supported_av_models")
    @patch("home_cinema_control.web.runtime_config.get_supported_tv_models")
    def test_apply_runtime_defaults_on_fresh_install_with_no_media_servers_key(
            self, tv_models, av_models
    ):
        tv_models.return_value = []
        av_models.return_value = []

        config = {}

        result = apply_runtime_defaults(config, version="0.5.1")

        self.assertEqual("emby", result["media_servers"]["active"])
        playback = result["media_servers"]["providers"]["emby"]["playback"]
        self.assertEqual("", playback["hcc_controlled_device"])
        self.assertFalse(playback["use_all_libraries"])
        self.assertEqual([], playback["path_mappings"])
        self.assertEqual([], playback["libraries"])

    def test_get_dir_folders_returns_sorted_directories_only(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            Path(temp_dir, "z").mkdir()
            Path(temp_dir, "a").mkdir()
            Path(temp_dir, "file.txt").write_text("", encoding="utf-8")

            self.assertEqual(["a", "z"], get_dir_folders(temp_dir))


if __name__ == "__main__":
    unittest.main()
