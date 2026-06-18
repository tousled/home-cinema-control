import unittest

from pydantic import ValidationError

from home_cinema_control.config.models import (
    AppConfig,
    AvConfig,
    HccConfig,
    MediaServerConfig,
    OppoConfig,
    PathMappingConfig,
    PlaybackConfig,
    TvConfig,
)


class TestHccConfig(unittest.TestCase):
    def test_empty_dict_produces_all_defaults(self):
        config = HccConfig()
        self.assertEqual(0, config.app.log_level)
        self.assertEqual("", config.playback.hcc_controlled_device)
        self.assertFalse(config.av.enabled)
        self.assertFalse(config.tv.enabled)
        self.assertEqual(3, config.oppo.api_retry_attempts)
        self.assertEqual("emby", config.media_server.type)

    def test_nested_sections_populated_from_dict(self):
        config = HccConfig(**{
            "app": {"log_level": 2},
            "oppo": {"ip": "192.168.1.5"},
        })
        self.assertEqual(2, config.app.log_level)
        self.assertEqual("192.168.1.5", config.oppo.ip)
        self.assertEqual(10.0, config.oppo.connection_timeout_seconds)

    def test_extra_top_level_keys_allowed(self):
        config = HccConfig(**{"Version": "1.0", "tv_dirs": ["lg"]})
        self.assertEqual("1.0", config.model_extra["Version"])
        self.assertEqual(["lg"], config.model_extra["tv_dirs"])

    def test_model_dump_is_dict(self):
        result = HccConfig().model_dump()
        self.assertIsInstance(result, dict)
        self.assertIsInstance(result["app"], dict)
        self.assertEqual(0, result["app"]["log_level"])


class TestAppConfig(unittest.TestCase):
    def test_defaults(self):
        app = AppConfig()
        self.assertEqual("backup", app.backup_path)
        self.assertEqual(5, app.status_refresh_interval_seconds)
        self.assertFalse(app.include_prerelease)
        self.assertEqual(10, app.version_check_timeout_seconds)
        self.assertEqual(0, app.log_level)

    def test_log_level_rejects_non_int(self):
        with self.assertRaises(ValidationError):
            AppConfig(log_level="high")

    def test_extra_keys_allowed(self):
        app = AppConfig(unknown_future_key="value")
        self.assertEqual("value", app.model_extra["unknown_future_key"])


class TestPlaybackConfig(unittest.TestCase):
    def test_defaults(self):
        p = PlaybackConfig()
        self.assertEqual("", p.hcc_controlled_device)
        self.assertFalse(p.use_all_libraries)
        self.assertEqual([], p.path_mappings)
        self.assertEqual([], p.libraries)

    def test_path_mappings_parsed_as_models(self):
        p = PlaybackConfig(path_mappings=[
            {"name": "Movies", "source_path": "/nas/movies", "player_path": "/movies"},
        ])
        self.assertEqual(1, len(p.path_mappings))
        self.assertEqual("/nas/movies", p.path_mappings[0].source_path)
        self.assertFalse(p.path_mappings[0].verified)


class TestPathMappingConfig(unittest.TestCase):
    def test_defaults(self):
        m = PathMappingConfig()
        self.assertEqual("", m.name)
        self.assertEqual("", m.source_path)
        self.assertEqual("/", m.player_path)
        self.assertFalse(m.verified)

    def test_verified_field(self):
        m = PathMappingConfig(verified=True)
        self.assertTrue(m.verified)


class TestAvConfig(unittest.TestCase):
    def test_defaults(self):
        av = AvConfig()
        self.assertFalse(av.enabled)
        self.assertEqual(23, av.port)
        self.assertEqual(0.0, av.hdmi_switch_delay_seconds)
        self.assertEqual(5.0, av.connection_timeout_seconds)
        self.assertEqual(1.0, av.command_timeout_seconds)

    def test_timeout_accepts_int(self):
        av = AvConfig(connection_timeout_seconds=10)
        self.assertEqual(10.0, av.connection_timeout_seconds)


class TestTvConfig(unittest.TestCase):
    def test_defaults(self):
        tv = TvConfig()
        self.assertFalse(tv.enabled)
        self.assertEqual(0, tv.player_hdmi_input_id)
        self.assertEqual("", tv.startup_script)
        self.assertEqual("", tv.shutdown_script)


class TestOppoConfig(unittest.TestCase):
    def test_defaults(self):
        oppo = OppoConfig()
        self.assertEqual(10.0, oppo.connection_timeout_seconds)
        self.assertEqual(30.0, oppo.playback_start_timeout_seconds)
        self.assertEqual(30.0, oppo.nfs_mount_timeout_seconds)
        self.assertEqual(1.0, oppo.api_connect_timeout_seconds)
        self.assertEqual(3, oppo.api_retry_attempts)
        self.assertFalse(oppo.bluray_disc_mode)
        self.assertFalse(oppo.pre_mount_smb)

    def test_api_retry_attempts_rejects_float(self):
        with self.assertRaises(ValidationError):
            OppoConfig(api_retry_attempts=2.5)


class TestMediaServerConfig(unittest.TestCase):
    def test_defaults(self):
        ms = MediaServerConfig()
        self.assertEqual("emby", ms.type)
        self.assertEqual("", ms.server_url)
        self.assertEqual("", ms.access_token)

    def test_extra_keys_preserved(self):
        ms = MediaServerConfig(access_token_configured=True)
        self.assertTrue(ms.model_extra["access_token_configured"])


if __name__ == "__main__":
    unittest.main()
