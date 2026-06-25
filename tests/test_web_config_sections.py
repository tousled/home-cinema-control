import unittest

from home_cinema_control.web.config_sections import apply_config_section


class ConfigSectionSaveTest(unittest.TestCase):
    def test_saves_oppo_without_overwriting_other_sections(self):
        config = {
            "oppo": {"ip": "192.168.1.10", "always_on": True},
            "tv": {"enabled": True, "model": "LG", "ip": "192.168.1.20"},
            "media_servers": {
                "active": "emby",
                "providers": {
                    "emby": {"playback": {"path_mappings": [{"name": "Movies"}]}}
                },
            },
        }

        updated = apply_config_section(config, "oppo", {"ip": "192.168.1.11"})

        self.assertEqual("192.168.1.11", updated["oppo"]["ip"])
        self.assertTrue(updated["oppo"]["always_on"])
        self.assertEqual(config["tv"], updated["tv"])
        self.assertEqual(config["media_servers"], updated["media_servers"])

    def test_saves_media_server_device_selector_without_overwriting_other_playback_fields(self):
        config = {
            "media_servers": {
                "active": "emby",
                "providers": {
                    "emby": {
                        "server_url": "http://old",
                        "playback": {
                            "hcc_controlled_device": "old-client",
                            "path_mappings": [{"name": "Movies"}],
                            "libraries": [{"id": "1", "name": "Movies", "active": True}],
                        },
                    }
                },
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

        emby = updated["media_servers"]["providers"]["emby"]
        self.assertEqual("http://new", emby["server_url"])
        self.assertEqual("emby", updated["media_servers"]["active"])
        self.assertEqual("new-client", emby["playback"]["hcc_controlled_device"])
        self.assertEqual([{"name": "Movies", "source_path": "", "player_path": "/", "protocol": "", "verified": False}],
                         emby["playback"]["path_mappings"])
        self.assertEqual([{"id": "1", "name": "Movies", "active": True}], emby["playback"]["libraries"])

    def test_media_server_device_selector_does_not_touch_other_providers_playback(self):
        config = {
            "media_servers": {
                "active": "emby",
                "providers": {
                    "emby": {"playback": {"hcc_controlled_device": "old-client"}},
                    "jellyfin": {"playback": {"hcc_controlled_device": "jf-client"}},
                },
            },
        }

        updated = apply_config_section(
            config,
            "media-server",
            {"playback": {"hcc_controlled_device": "new-client"}},
        )

        self.assertEqual(
            "new-client",
            updated["media_servers"]["providers"]["emby"]["playback"]["hcc_controlled_device"],
        )
        self.assertEqual(
            "jf-client",
            updated["media_servers"]["providers"]["jellyfin"]["playback"]["hcc_controlled_device"],
        )

    def test_media_server_switch_lands_in_target_providers_entry(self):
        config = {
            "media_servers": {
                "active": "emby",
                "providers": {"emby": {"server_url": "http://emby"}},
            },
        }

        updated = apply_config_section(
            config,
            "media-server",
            {"media_server": {"type": "jellyfin", "server_url": "http://jf"}},
        )

        self.assertEqual("jellyfin", updated["media_servers"]["active"])
        self.assertEqual(
            "http://jf", updated["media_servers"]["providers"]["jellyfin"]["server_url"]
        )
        self.assertEqual(
            "http://emby", updated["media_servers"]["providers"]["emby"]["server_url"]
        )

    def test_saves_libraries_without_overwriting_path_mappings(self):
        config = {
            "media_servers": {
                "active": "emby",
                "providers": {
                    "emby": {
                        "playback": {
                            "path_mappings": [{"name": "Movies"}],
                            "libraries": [],
                            "use_all_libraries": True,
                        }
                    }
                },
            },
        }

        updated = apply_config_section(
            config,
            "playback-libraries",
            {"libraries": [{"name": "Series", "active": True}], "use_all_libraries": False},
        )

        emby_playback = updated["media_servers"]["providers"]["emby"]["playback"]
        self.assertEqual(
            [{"name": "Movies", "source_path": "", "player_path": "/", "protocol": "", "verified": False}],
            emby_playback["path_mappings"],
        )
        self.assertEqual([{"id": "", "name": "Series", "active": True}], emby_playback["libraries"])
        self.assertFalse(emby_playback["use_all_libraries"])

    def test_libraries_save_does_not_touch_other_providers_playback(self):
        config = {
            "media_servers": {
                "active": "jellyfin",
                "providers": {
                    "emby": {"playback": {"libraries": [{"id": "1", "name": "Old", "active": True}]}},
                    "jellyfin": {},
                },
            },
        }

        updated = apply_config_section(
            config,
            "playback-libraries",
            {"libraries": [{"name": "New", "active": True}], "use_all_libraries": False},
        )

        emby_libraries = updated["media_servers"]["providers"]["emby"]["playback"]["libraries"]
        self.assertEqual([{"id": "1", "name": "Old", "active": True}], emby_libraries)

    def test_saves_path_mappings_without_overwriting_libraries(self):
        config = {
            "media_servers": {
                "active": "emby",
                "providers": {
                    "emby": {
                        "playback": {
                            "path_mappings": [{"name": "Old", "verified": False}],
                            "libraries": [{"id": "1", "name": "Movies", "active": True}],
                        }
                    }
                },
            },
        }

        updated = apply_config_section(
            config,
            "path-mappings",
            {"path_mappings": [{"name": "Movies", "source_path": "/m", "verified": True}]},
        )

        emby_playback = updated["media_servers"]["providers"]["emby"]["playback"]
        self.assertEqual(
            [{"name": "Movies", "source_path": "/m", "player_path": "/", "protocol": "", "verified": True}],
            emby_playback["path_mappings"],
        )
        self.assertEqual([{"id": "1", "name": "Movies", "active": True}], emby_playback["libraries"])

    def test_saves_network_access_without_overwriting_libraries(self):
        config = {
            "oppo": {"pre_mount_smb": False, "always_on": True},
            "smb": {"username": "old", "password": "secret"},
            "media_servers": {
                "active": "emby",
                "providers": {
                    "emby": {
                        "playback": {
                            "path_mappings": [{"name": "Movies", "verified": True}],
                            "libraries": [{"id": "1", "name": "Movies", "active": True}],
                        }
                    }
                },
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
        emby_playback = updated["media_servers"]["providers"]["emby"]["playback"]
        self.assertEqual(
            [{"name": "Movies", "source_path": "", "player_path": "/", "protocol": "", "verified": False}],
            emby_playback["path_mappings"],
        )
        self.assertEqual([{"id": "1", "name": "Movies", "active": True}], emby_playback["libraries"])

    def test_network_access_without_path_mappings_does_not_touch_playback(self):
        config = {
            "oppo": {"pre_mount_smb": False},
            "smb": {"username": "old"},
            "media_servers": {
                "active": "emby",
                "providers": {
                    "emby": {"playback": {"path_mappings": [{"name": "Movies"}]}}
                },
            },
        }

        updated = apply_config_section(
            config, "network-access", {"oppo": {"pre_mount_smb": True}}
        )

        self.assertEqual(
            config["media_servers"]["providers"]["emby"]["playback"]["path_mappings"],
            updated["media_servers"]["providers"]["emby"]["playback"]["path_mappings"],
        )

    def test_rejects_unknown_section(self):
        with self.assertRaises(ValueError):
            apply_config_section({}, "unknown", {})


if __name__ == "__main__":
    unittest.main()
