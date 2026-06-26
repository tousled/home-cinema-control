import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from home_cinema_control.web.runtime_config import (
    apply_runtime_defaults,
    get_dir_folders,
    load_runtime_config,
)


class WebRuntimeConfigTest(unittest.TestCase):
    @patch("home_cinema_control.web.runtime_config.get_supported_av_models")
    @patch("home_cinema_control.web.runtime_config.get_supported_tv_models")
    def test_apply_runtime_defaults_adds_only_web_runtime_fields(
        self, tv_models, av_models
    ):
        tv_models.return_value = ["lg"]
        av_models.return_value = ["denon"]

        config = {"tv": {"enabled": True}}

        result = apply_runtime_defaults(config, version="0.5.1")

        self.assertIs(result, config)
        self.assertEqual("0.5.1", config["Version"])
        self.assertEqual(["lg"], config["tv_dirs"])
        self.assertEqual(["denon"], config["av_dirs"])
        self.assertEqual(["en-US", "es-ES"], config["langs"])
        self.assertIn("arp_available", config)
        self.assertNotIn("app", config)
        self.assertNotIn("av", config)
        self.assertNotIn("oppo", config)
        self.assertNotIn("media_servers", config)

    @patch("home_cinema_control.web.runtime_config.get_supported_av_models")
    @patch("home_cinema_control.web.runtime_config.get_supported_tv_models")
    def test_load_runtime_config_applies_pydantic_defaults_then_runtime_fields(
            self, tv_models, av_models
    ):
        tv_models.return_value = ["lg"]
        av_models.return_value = ["denon"]

        with tempfile.TemporaryDirectory() as directory:
            config_file = Path(directory) / "config.json"
            config_file.write_text(
                json.dumps(
                    {
                        "tv": {"enabled": True},
                        "media_servers": {
                            "active": "emby",
                            "providers": {
                                "emby": {
                                    "playback": {
                                        "path_mappings": [{"name": "Movies"}]
                                    }
                                }
                            },
                        },
                    }
                ),
                encoding="utf-8",
            )

            result = load_runtime_config(config_file, version="0.5.1")

        self.assertEqual("0.5.1", result["Version"])
        self.assertEqual("es-ES", result["app"]["language"])
        self.assertEqual(5, result["app"]["status_refresh_interval_seconds"])
        self.assertFalse(result["app"]["include_prerelease"])
        self.assertEqual(
            "tousled/home-cinema-control", result["app"]["release_repository"]
        )
        self.assertEqual(10, result["app"]["version_check_timeout_seconds"])
        self.assertTrue(result["tv"]["enabled"])
        self.assertEqual("", result["tv"]["ip"])
        self.assertFalse(result["av"]["enabled"])
        self.assertEqual("", result["oppo"]["ip"])
        self.assertEqual("auto", result["oppo"]["observation_mode"])
        playback = result["media_servers"]["providers"]["emby"]["playback"]
        self.assertFalse(playback["use_all_libraries"])
        self.assertFalse(playback["path_mappings"][0]["verified"])
        self.assertEqual(["lg"], result["tv_dirs"])
        self.assertEqual(["denon"], result["av_dirs"])
        self.assertEqual(["en-US", "es-ES"], result["langs"])

    def test_get_dir_folders_returns_sorted_directories_only(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            Path(temp_dir, "z").mkdir()
            Path(temp_dir, "a").mkdir()
            Path(temp_dir, "file.txt").write_text("", encoding="utf-8")

            self.assertEqual(["a", "z"], get_dir_folders(temp_dir))


if __name__ == "__main__":
    unittest.main()
