import unittest

from home_cinema_control.web.config_sections import apply_config_section


class ConfigSectionSaveTest(unittest.TestCase):
    def test_saves_oppo_without_overwriting_other_sections(self):
        config = {
            "oppo": {"ip": "192.168.1.10", "always_on": True},
            "tv": {"enabled": True, "model": "LG", "ip": "192.168.1.20"},
            "playback": {"path_mappings": [{"name": "Movies"}]},
        }

        updated = apply_config_section(config, "oppo", {"ip": "192.168.1.11"})

        self.assertEqual("192.168.1.11", updated["oppo"]["ip"])
        self.assertTrue(updated["oppo"]["always_on"])
        self.assertEqual(config["tv"], updated["tv"])
        self.assertEqual(config["playback"], updated["playback"])

    def test_saves_media_server_and_only_monitored_playback_device(self):
        config = {
            "media_server": {"type": "emby", "server_url": "http://old"},
            "playback": {
                "hcc_controlled_device": "old-client",
                "path_mappings": [{"name": "Movies"}],
                "libraries": [{"Name": "Movies"}],
            },
        }

        updated = apply_config_section(
            config,
            "media-server",
            {
                "media_server": {"server_url": "http://new"},
                "playback": {"hcc_controlled_device": "new-client"},
            },
        )

        self.assertEqual("http://new", updated["media_server"]["server_url"])
        self.assertEqual("new-client", updated["playback"]["hcc_controlled_device"])
        self.assertEqual([{"name": "Movies"}], updated["playback"]["path_mappings"])
        self.assertEqual([{"Name": "Movies"}], updated["playback"]["libraries"])

    def test_saves_libraries_without_overwriting_path_mappings(self):
        config = {
            "playback": {
                "path_mappings": [{"name": "Movies"}],
                "libraries": [],
                "use_all_libraries": True,
            }
        }

        updated = apply_config_section(
            config,
            "playback-libraries",
            {"libraries": [{"Name": "Series", "Active": True}], "use_all_libraries": False},
        )

        self.assertEqual([{"name": "Movies"}], updated["playback"]["path_mappings"])
        self.assertEqual([{"Name": "Series", "Active": True}], updated["playback"]["libraries"])
        self.assertFalse(updated["playback"]["use_all_libraries"])

    def test_saves_network_access_without_overwriting_libraries(self):
        config = {
            "oppo": {"pre_mount_smb": False, "always_on": True},
            "smb": {"username": "old", "password": "secret"},
            "playback": {
                "path_mappings": [{"name": "Movies", "verified": True}],
                "libraries": [{"Name": "Movies", "Active": True}],
            },
        }

        updated = apply_config_section(
            config,
            "network-access",
            {
                "oppo": {"pre_mount_smb": True},
                "smb": {"username": "new", "password": ""},
                "path_mappings": [{"name": "Movies", "verified": False}],
            },
        )

        self.assertTrue(updated["oppo"]["pre_mount_smb"])
        self.assertTrue(updated["oppo"]["always_on"])
        self.assertEqual("new", updated["smb"]["username"])
        self.assertEqual("", updated["smb"]["password"])
        self.assertEqual([{"name": "Movies", "verified": False}], updated["playback"]["path_mappings"])
        self.assertEqual([{"Name": "Movies", "Active": True}], updated["playback"]["libraries"])

    def test_rejects_unknown_section(self):
        with self.assertRaises(ValueError):
            apply_config_section({}, "unknown", {})


if __name__ == "__main__":
    unittest.main()
