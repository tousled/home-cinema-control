import json
import tempfile
import unittest
from pathlib import Path

from home_cinema_control.config.migration import (
    LEGACY_DETECTION_KEYS,
    LEGACY_FLAT_CONFIG_KEYS,
    apply_all_migrations,
    _migrate_app_flat_keys,
    _migrate_app_to_playback_keys,
    _migrate_av_flat_keys,
    _migrate_oppo_flat_keys,
    _migrate_playback_flat_keys,
    _migrate_tv_flat_keys,
    _rename_app_keys,
    _rename_av_keys,
    _rename_oppo_keys,
    _rename_playback_keys,
    _rename_tv_keys,
)
from home_cinema_control.web.migration import apply_migration, is_migration_available


# ---------------------------------------------------------------------------
# Flat → nested migrations
# ---------------------------------------------------------------------------

class MigrateAvFlatKeysTest(unittest.TestCase):
    def test_moves_flat_av_keys_into_av_section(self):
        config = {"AV": True, "AV_Ip": "192.168.1.10", "AV_Port": 23}
        _migrate_av_flat_keys(config)
        self.assertTrue(config["av"]["enabled"])
        self.assertEqual("192.168.1.10", config["av"]["ip"])
        self.assertEqual(23, config["av"]["port"])
        self.assertNotIn("AV", config)
        self.assertNotIn("AV_Ip", config)

    def test_string_true_coerced_to_bool_for_enabled(self):
        config = {"AV": "True"}
        _migrate_av_flat_keys(config)
        self.assertIs(True, config["av"]["enabled"])

    def test_string_false_coerced_to_bool_for_enabled(self):
        config = {"AV": "False"}
        _migrate_av_flat_keys(config)
        self.assertIs(False, config["av"]["enabled"])

    def test_existing_nested_value_wins_over_flat(self):
        config = {"AV_Ip": "old-flat", "av": {"ip": "existing-nested"}}
        _migrate_av_flat_keys(config)
        self.assertEqual("existing-nested", config["av"]["ip"])
        self.assertNotIn("AV_Ip", config)

    def test_no_flat_keys_leaves_config_unchanged(self):
        config = {"av": {"ip": "192.168.1.1"}}
        _migrate_av_flat_keys(config)
        self.assertEqual({"ip": "192.168.1.1"}, config["av"])


class MigrateTvFlatKeysTest(unittest.TestCase):
    def test_moves_flat_tv_keys_into_tv_section(self):
        config = {"TV": True, "TV_IP": "192.168.1.20", "Source": 3}
        _migrate_tv_flat_keys(config)
        self.assertTrue(config["tv"]["enabled"])
        self.assertEqual("192.168.1.20", config["tv"]["ip"])
        self.assertEqual(3, config["tv"]["player_hdmi_input_id"])
        self.assertNotIn("TV", config)

    def test_string_true_coerced_to_bool_for_enabled(self):
        config = {"TV": "True"}
        _migrate_tv_flat_keys(config)
        self.assertIs(True, config["tv"]["enabled"])

    def test_existing_nested_value_wins_over_flat(self):
        config = {"TV_IP": "old", "tv": {"ip": "current"}}
        _migrate_tv_flat_keys(config)
        self.assertEqual("current", config["tv"]["ip"])


class MigrateOppoFlatKeysTest(unittest.TestCase):
    def test_moves_flat_oppo_keys_into_oppo_section(self):
        config = {
            "Oppo_IP": "192.168.1.5",
            "timeout_oppo_conection": 10,
            "timeout_oppo_playitem": 30,
            "timeout_oppo_mount": 60,
            "BRDisc": True,
            "smbtrick": False,
        }
        _migrate_oppo_flat_keys(config)
        self.assertEqual("192.168.1.5", config["oppo"]["ip"])
        self.assertEqual(10, config["oppo"]["connection_timeout_seconds"])
        self.assertEqual(30, config["oppo"]["playback_start_timeout_seconds"])
        self.assertEqual(60, config["oppo"]["nfs_mount_timeout_seconds"])
        self.assertTrue(config["oppo"]["bluray_disc_mode"])
        self.assertFalse(config["oppo"]["pre_mount_smb"])
        self.assertNotIn("Oppo_IP", config)

    def test_existing_nested_value_wins_over_flat(self):
        config = {"Oppo_IP": "old", "oppo": {"ip": "current"}}
        _migrate_oppo_flat_keys(config)
        self.assertEqual("current", config["oppo"]["ip"])

    def test_default_nfs_false_inverts_to_use_smb_true(self):
        config = {"default_nfs": False}
        _migrate_oppo_flat_keys(config)
        self.assertTrue(config["oppo"]["use_smb"])

    def test_default_nfs_true_inverts_to_use_smb_false(self):
        config = {"default_nfs": True}
        _migrate_oppo_flat_keys(config)
        self.assertFalse(config["oppo"]["use_smb"])

    def test_default_nfs_string_false_inverts_to_use_smb_true(self):
        config = {"default_nfs": "False"}
        _migrate_oppo_flat_keys(config)
        self.assertTrue(config["oppo"]["use_smb"])

    def test_default_nfs_string_true_inverts_to_use_smb_false(self):
        config = {"default_nfs": "True"}
        _migrate_oppo_flat_keys(config)
        self.assertFalse(config["oppo"]["use_smb"])


class MigrateAppFlatKeysTest(unittest.TestCase):
    def test_moves_flat_app_keys_into_app_section(self):
        config = {
            "output_path": "backup",
            "refresh_time": 5,
            "check_beta": False,
            "DebugLevel": 1,
        }
        _migrate_app_flat_keys(config)
        self.assertEqual("backup", config["app"]["backup_path"])
        self.assertEqual(5, config["app"]["status_refresh_interval_seconds"])
        self.assertFalse(config["app"]["include_prerelease"])
        self.assertEqual(1, config["app"]["log_level"])
        self.assertNotIn("output_path", config)

    def test_language_moves_into_app(self):
        config = {"language": "en-US"}
        _migrate_app_flat_keys(config)
        self.assertEqual("en-US", config["app"]["language"])


class MigratePlaybackFlatKeysTest(unittest.TestCase):
    def test_moves_flat_playback_keys_into_playback_section(self):
        config = {
            "MonitoredDevice": "TV-Living",
            "enable_all_libraries": True,
            "servers": [{"name": "Movies"}],
            "Libraries": [],
        }
        _migrate_playback_flat_keys(config)
        self.assertEqual("TV-Living", config["playback"]["hcc_controlled_device"])
        self.assertTrue(config["playback"]["use_all_libraries"])
        self.assertEqual([{"name": "Movies"}], config["playback"]["path_mappings"])
        self.assertNotIn("MonitoredDevice", config)

    def test_existing_nested_value_wins_over_flat(self):
        config = {"MonitoredDevice": "old", "playback": {"hcc_controlled_device": "current"}}
        _migrate_playback_flat_keys(config)
        self.assertEqual("current", config["playback"]["hcc_controlled_device"])


class MigrateAppToPlaybackKeysTest(unittest.TestCase):
    def test_moves_playback_keys_from_app_to_playback(self):
        config = {
            "app": {
                "hcc_controlled_device": "TV-Living",
                "use_all_libraries": True,
                "log_level": 1,
            }
        }
        _migrate_app_to_playback_keys(config)
        self.assertEqual("TV-Living", config["playback"]["hcc_controlled_device"])
        self.assertTrue(config["playback"]["use_all_libraries"])
        self.assertNotIn("hcc_controlled_device", config["app"])
        self.assertEqual(1, config["app"]["log_level"])

    def test_existing_playback_value_wins_over_app(self):
        config = {
            "app": {"hcc_controlled_device": "from-app"},
            "playback": {"hcc_controlled_device": "already-in-playback"},
        }
        _migrate_app_to_playback_keys(config)
        self.assertEqual("already-in-playback", config["playback"]["hcc_controlled_device"])

    def test_no_app_section_is_a_noop(self):
        config = {}
        _migrate_app_to_playback_keys(config)
        self.assertNotIn("playback", config)


# ---------------------------------------------------------------------------
# Nested key renames
# ---------------------------------------------------------------------------

class RenameAppKeysTest(unittest.TestCase):
    def test_renames_intermediate_app_keys(self):
        config = {
            "app": {
                "output_path": "backup",
                "refresh_time": 5,
                "check_beta": False,
                "debug_level": 2,
                "version_check_timeout": 10,
            }
        }
        _rename_app_keys(config)
        app = config["app"]
        self.assertEqual("backup", app["backup_path"])
        self.assertEqual(5, app["status_refresh_interval_seconds"])
        self.assertFalse(app["include_prerelease"])
        self.assertEqual(2, app["log_level"])
        self.assertEqual(10, app["version_check_timeout_seconds"])
        self.assertNotIn("output_path", app)
        self.assertNotIn("debug_level", app)

    def test_existing_new_key_takes_priority(self):
        config = {"app": {"debug_level": 0, "log_level": 2}}
        _rename_app_keys(config)
        self.assertEqual(2, config["app"]["log_level"])
        self.assertNotIn("debug_level", config["app"])

    def test_no_app_section_is_a_noop(self):
        config = {}
        _rename_app_keys(config)
        self.assertEqual({}, config)


class RenamePlaybackKeysTest(unittest.TestCase):
    def test_renames_intermediate_playback_keys(self):
        config = {
            "playback": {
                "servers": [{"Emby_Path": "/nas/movies", "Oppo_Path": "/movies", "Test_OK": True}],
                "monitored_device": "TV-Living",
                "enable_all_libraries": True,
                "resume_on": "something",
            }
        }
        _rename_playback_keys(config)
        p = config["playback"]
        self.assertEqual("TV-Living", p["hcc_controlled_device"])
        self.assertTrue(p["use_all_libraries"])
        self.assertNotIn("monitored_device", p)
        self.assertNotIn("resume_on", p)
        mapping = p["path_mappings"][0]
        self.assertEqual("/nas/movies", mapping["source_path"])
        self.assertEqual("/movies", mapping["player_path"])
        self.assertTrue(mapping["verified"])

    def test_resume_on_is_always_dropped(self):
        config = {"playback": {"resume_on": "anything", "path_mappings": []}}
        _rename_playback_keys(config)
        self.assertNotIn("resume_on", config["playback"])


class RenameAvKeysTest(unittest.TestCase):
    def test_renames_intermediate_av_keys(self):
        config = {
            "av": {
                "cmd_pow_on": "PWR ON",
                "cmd_change_hdmi": "HDMI",
                "cmd_pow_off": "PWR OFF",
                "delay_hdmi": 2,
                "media_player_hdmi_input_name": "GAME",
                "timeout": 5,
                "query_timeout": 1,
                "tv_input": "TV",
            }
        }
        _rename_av_keys(config)
        av = config["av"]
        self.assertEqual("PWR ON", av["power_on_command"])
        self.assertEqual("HDMI", av["hdmi_input_command"])
        self.assertEqual("PWR OFF", av["power_off_command"])
        self.assertEqual(2, av["hdmi_switch_delay_seconds"])
        self.assertEqual("GAME", av["player_hdmi_input"])
        self.assertEqual(5, av["connection_timeout_seconds"])
        self.assertEqual(1, av["command_timeout_seconds"])
        self.assertEqual("TV", av["tv_connected_input"])


class RenameTvKeysTest(unittest.TestCase):
    def test_renames_intermediate_tv_keys(self):
        config = {
            "tv": {
                "media_player_hdmi_input_id": 3,
                "script_init": "init.sh",
                "script_end": "end.sh",
            }
        }
        _rename_tv_keys(config)
        tv = config["tv"]
        self.assertEqual(3, tv["player_hdmi_input_id"])
        self.assertEqual("init.sh", tv["startup_script"])
        self.assertEqual("end.sh", tv["shutdown_script"])


class RenameOppoKeysTest(unittest.TestCase):
    def test_renames_intermediate_oppo_keys(self):
        config = {
            "oppo": {
                "timeout_connection": 3,
                "timeout_playitem": 30,
                "timeout_mount": 60,
                "control_api_connect_timeout": 1.0,
                "web_control_api_attempts": 3,
                "br_disc": True,
                "smb_trick": False,
            }
        }
        _rename_oppo_keys(config)
        oppo = config["oppo"]
        self.assertEqual(3, oppo["connection_timeout_seconds"])
        self.assertEqual(30, oppo["playback_start_timeout_seconds"])
        self.assertEqual(60, oppo["nfs_mount_timeout_seconds"])
        self.assertEqual(1.0, oppo["api_connect_timeout_seconds"])
        self.assertEqual(3, oppo["api_retry_attempts"])
        self.assertTrue(oppo["bluray_disc_mode"])
        self.assertFalse(oppo["pre_mount_smb"])

    def test_default_nfs_inverts_to_use_smb(self):
        config = {"oppo": {"default_nfs": False}}
        _rename_oppo_keys(config)
        self.assertTrue(config["oppo"]["use_smb"])
        self.assertNotIn("default_nfs", config["oppo"])


# ---------------------------------------------------------------------------
# apply_all_migrations end-to-end
# ---------------------------------------------------------------------------

class ApplyAllMigrationsTest(unittest.TestCase):
    def test_fully_migrates_legacy_flat_config(self):
        config = {
            "Oppo_IP": "192.168.1.5",
            "timeout_oppo_conection": 10,
            "timeout_oppo_playitem": 30,
            "timeout_oppo_mount": 60,
            "BRDisc": False,
            "smbtrick": False,
            "Autoscript": False,
            "Always_ON": True,
            "default_nfs": False,
            "TV": True,
            "TV_IP": "192.168.1.6",
            "TV_MAC": "aa:bb:cc:dd:ee:ff",
            "TV_model": "lg",
            "TV_SOURCES": [],
            "Source": 3,
            "TV_script_init": "init.sh",
            "TV_script_end": "end.sh",
            "AV": False,
            "AV_Ip": "192.168.1.7",
            "AV_Port": 23,
            "AV_model": "denon",
            "AV_Always_ON": True,
            "av_delay_hdmi": 2,
            "AV_CMD_POW_ON": "PWR ON",
            "AV_CMD_CHANGE_HDMI": "HDMI",
            "AV_CMD_POW_OFF": "PWR OFF",
            "AV_SOURCES": [],
            "AV_Input": "GAME",
            "AV_Timeout": 5,
            "AV_Query_Timeout": 1,
            "AV_TV_Input": "TV",
            "MonitoredDevice": "TV-Living",
            "enable_all_libraries": True,
            "servers": [{"name": "Movies", "Emby_Path": "/nas/movies", "Oppo_Path": "/movies", "Test_OK": True}],
            "Libraries": [],
            "resume_on": "",
            "output_path": "backup",
            "language": "es-ES",
            "refresh_time": 5,
            "check_beta": False,
            "DebugLevel": 1,
            "media_server": {"type": "emby", "server_url": "http://emby:8096"},
        }

        apply_all_migrations(config)

        # no legacy flat keys remain
        for key in LEGACY_FLAT_CONFIG_KEYS:
            self.assertNotIn(key, config, f"legacy key still present: {key}")

        # sections are populated
        self.assertEqual("192.168.1.5", config["oppo"]["ip"])
        self.assertEqual(10, config["oppo"]["connection_timeout_seconds"])
        self.assertEqual(30, config["oppo"]["playback_start_timeout_seconds"])
        self.assertEqual(60, config["oppo"]["nfs_mount_timeout_seconds"])
        self.assertTrue(config["oppo"]["use_smb"])

        self.assertTrue(config["tv"]["enabled"])
        self.assertEqual("192.168.1.6", config["tv"]["ip"])
        self.assertEqual(3, config["tv"]["player_hdmi_input_id"])
        self.assertEqual("init.sh", config["tv"]["startup_script"])
        self.assertEqual("end.sh", config["tv"]["shutdown_script"])

        self.assertFalse(config["av"]["enabled"])
        self.assertEqual("192.168.1.7", config["av"]["ip"])
        self.assertEqual(2, config["av"]["hdmi_switch_delay_seconds"])
        self.assertEqual("PWR ON", config["av"]["power_on_command"])
        self.assertEqual(5, config["av"]["connection_timeout_seconds"])
        self.assertEqual(1, config["av"]["command_timeout_seconds"])
        self.assertEqual("TV", config["av"]["tv_connected_input"])

        self.assertEqual("backup", config["app"]["backup_path"])
        self.assertEqual(5, config["app"]["status_refresh_interval_seconds"])
        self.assertFalse(config["app"]["include_prerelease"])
        self.assertEqual(1, config["app"]["log_level"])

        self.assertEqual("TV-Living", config["playback"]["hcc_controlled_device"])
        self.assertTrue(config["playback"]["use_all_libraries"])
        mapping = config["playback"]["path_mappings"][0]
        self.assertEqual("/nas/movies", mapping["source_path"])
        self.assertEqual("/movies", mapping["player_path"])
        self.assertTrue(mapping["verified"])

    def test_canonical_config_is_unchanged_by_migration(self):
        config = {
            "app": {"log_level": 1, "include_prerelease": False},
            "playback": {"hcc_controlled_device": "TV", "use_all_libraries": False, "path_mappings": []},
            "av": {"enabled": False, "power_on_command": "PWR ON"},
            "tv": {"enabled": True, "player_hdmi_input_id": 3},
            "oppo": {"ip": "192.168.1.5", "connection_timeout_seconds": 3},
            "media_server": {"type": "emby"},
        }
        import copy
        original = copy.deepcopy(config)
        apply_all_migrations(config)
        self.assertEqual(original, config)


# ---------------------------------------------------------------------------
# is_migration_available / apply_migration integration
# ---------------------------------------------------------------------------

class IsMigrationAvailableTest(unittest.TestCase):
    def test_returns_true_for_config_with_flat_keys(self):
        with tempfile.TemporaryDirectory() as d:
            config_path = Path(d) / "config.json"
            config_path.write_text(json.dumps({"MonitoredDevice": "TV", "DebugLevel": 1}))
            self.assertTrue(is_migration_available(config_path))

    def test_returns_false_for_already_migrated_config(self):
        with tempfile.TemporaryDirectory() as d:
            config_path = Path(d) / "config.json"
            config_path.write_text(json.dumps({
                "app": {"log_level": 1},
                "playback": {"hcc_controlled_device": "TV"},
            }))
            self.assertFalse(is_migration_available(config_path))

    def test_returns_true_for_config_with_nested_legacy_oppo_key(self):
        with tempfile.TemporaryDirectory() as d:
            config_path = Path(d) / "config.json"
            config_path.write_text(json.dumps({
                "oppo": {"ip": "192.168.1.5", "default_nfs": False},
            }))
            self.assertTrue(is_migration_available(config_path))

    def test_returns_false_for_missing_file(self):
        self.assertFalse(is_migration_available("/nonexistent/config.json"))

    def test_returns_false_for_empty_config(self):
        with tempfile.TemporaryDirectory() as d:
            config_path = Path(d) / "config.json"
            config_path.write_text("{}")
            self.assertFalse(is_migration_available(config_path))


class ApplyMigrationTest(unittest.TestCase):
    def test_migrates_flat_config_file_in_place(self):
        with tempfile.TemporaryDirectory() as d:
            config_path = Path(d) / "config.json"
            config_path.write_text(json.dumps({
                "MonitoredDevice": "TV-Living",
                "DebugLevel": 2,
                "Oppo_IP": "192.168.1.5",
                "media_server": {"type": "emby"},
            }))

            apply_migration(config_path)

            result = json.loads(config_path.read_text())
            self.assertNotIn("MonitoredDevice", result)
            self.assertNotIn("DebugLevel", result)
            self.assertNotIn("Oppo_IP", result)
            self.assertEqual("TV-Living", result["playback"]["hcc_controlled_device"])
            self.assertEqual(2, result["app"]["log_level"])
            self.assertEqual("192.168.1.5", result["oppo"]["ip"])

    def test_migrated_config_is_no_longer_detected_as_needing_migration(self):
        with tempfile.TemporaryDirectory() as d:
            config_path = Path(d) / "config.json"
            config_path.write_text(json.dumps({"MonitoredDevice": "TV", "DebugLevel": 1}))

            self.assertTrue(is_migration_available(config_path))
            apply_migration(config_path)
            self.assertFalse(is_migration_available(config_path))

    def test_migrates_stale_nested_default_nfs_without_other_legacy_keys(self):
        with tempfile.TemporaryDirectory() as d:
            config_path = Path(d) / "config.json"
            config_path.write_text(json.dumps({
                "oppo": {"ip": "192.168.1.5", "default_nfs": False},
                "media_server": {"type": "emby"},
            }))

            self.assertTrue(is_migration_available(config_path))
            apply_migration(config_path)

            result = json.loads(config_path.read_text())
            self.assertNotIn("default_nfs", result["oppo"])
            self.assertTrue(result["oppo"]["use_smb"])
            self.assertFalse(is_migration_available(config_path))


class LegacyDetectionKeysTest(unittest.TestCase):
    def test_detection_keys_are_subset_of_legacy_flat_keys(self):
        self.assertTrue(LEGACY_DETECTION_KEYS.issubset(LEGACY_FLAT_CONFIG_KEYS))

    def test_detection_keys_include_all_flat_map_keys(self):
        from home_cinema_control.config.migration import (
            _APP_FLAT_KEY_MAP,
            _AV_FLAT_KEY_MAP,
            _OPPO_FLAT_KEY_MAP,
            _PLAYBACK_FLAT_KEY_MAP,
            _TV_FLAT_KEY_MAP,
        )
        all_flat = (
            set(_AV_FLAT_KEY_MAP)
            | set(_TV_FLAT_KEY_MAP)
            | set(_APP_FLAT_KEY_MAP)
            | set(_PLAYBACK_FLAT_KEY_MAP)
            | set(_OPPO_FLAT_KEY_MAP)
        )
        self.assertEqual(all_flat, LEGACY_DETECTION_KEYS)


if __name__ == "__main__":
    unittest.main()
