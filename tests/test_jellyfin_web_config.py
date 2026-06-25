import unittest
from unittest.mock import MagicMock, patch

from home_cinema_control.config.manager import (
    get_media_server_provider,
    sanitize_config_for_web,
)
from home_cinema_control.config.models import PathMappingConfig
from home_cinema_control.media_servers.common.models import (
    MediaServerLibrary,
    MediaServerLoginCredentials,
)
from home_cinema_control.media_servers.jellyfin.web_config import (
    build_control_device_config,
    build_library_config,
    build_virtual_folder_servers,
    configure_jellyfin_token,
    load_devices,
    load_libraries,
    load_selectable_folders,
)


class JellyfinWebConfigTest(unittest.TestCase):
    def test_build_control_device_config_uses_device_id(self):
        devices = build_control_device_config(
            [
                {"Id": "device-1", "Name": "Living Room", "AppName": "Jellyfin"},
                {"Id": "home-cinema-control", "Name": "HCC", "AppName": "HCC"},
                {"Id": "device-2", "Name": "", "AppName": "Jellyfin"},
            ]
        )

        self.assertEqual(1, len(devices))
        self.assertEqual("device-1", devices[0].id)
        self.assertEqual("Living Room / Jellyfin", devices[0].name)

    @patch("home_cinema_control.media_servers.jellyfin.web_config._authenticated_client")
    def test_load_devices_raises_when_provider_is_unreachable(self, mock_client_factory):
        mock_client_factory.side_effect = RuntimeError("offline")

        with self.assertRaisesRegex(RuntimeError, "Could not read Jellyfin devices"):
            load_devices({"media_servers": {"active": "jellyfin", "providers": {"jellyfin": {}}}})

    def test_build_library_config_preserves_existing_active_flag(self):
        libraries = build_library_config(
            [{"Id": "movies", "Name": "Movies"}, {"Id": "series", "Name": "Series"}],
            existing_libraries=[{"id": "movies", "name": "Movies", "active": True}],
        )

        self.assertEqual(
            [
                {"name": "Movies", "id": "movies", "active": True},
                {"name": "Series", "id": "series", "active": False},
            ],
            [library.model_dump() for library in libraries],
        )

    def test_build_virtual_folder_servers_uses_locations(self):
        mappings = build_virtual_folder_servers(
            [
                {
                    "Name": "Movies",
                    "Locations": ["/media/movies", "/media/uhd"],
                },
                {"Name": "Music", "Locations": ["/media/music"]},
            ],
            libraries=[{"name": "Movies", "active": True}],
            existing_servers=[
                {
                    "source_path": "/media/movies",
                    "name": "Cinema",
                    "player_path": "/nas/movies",
                    "verified": True,
                }
            ],
            enable_all_libraries=False,
        )

        self.assertEqual(2, len(mappings))
        self.assertEqual("Cinema", mappings[0]["name"])
        self.assertEqual("/media/movies", mappings[0]["source_path"])
        self.assertEqual("/nas/movies", mappings[0]["player_path"])
        self.assertTrue(mappings[0]["verified"])
        self.assertEqual("Movies(2)", mappings[1]["name"])
        self.assertEqual("/media/uhd", mappings[1]["source_path"])


class ConfigureJellyfinTokenTest(unittest.TestCase):
    @patch("home_cinema_control.media_servers.jellyfin.web_config._authenticate_with_temporary_password")
    def test_returns_effective_config_with_token_for_secret_persistence(self, mock_authenticate):
        mock_authenticate.return_value = {
            "AccessToken": "jellyfin-token",
            "User": {"Id": "jellyfin-user", "Name": "Pedro"},
        }

        result = configure_jellyfin_token(
            {
                "media_servers": {
                    "active": "jellyfin",
                    "providers": {"jellyfin": {"server_url": "http://jellyfin.local/"}},
                }
            },
            MediaServerLoginCredentials(user_name="pedro", password="secret"),
        )

        provider = result["media_servers"]["providers"]["jellyfin"]
        self.assertEqual("jellyfin-token", provider["access_token"])
        self.assertEqual("jellyfin-user", provider["user_id"])
        self.assertEqual("Pedro", provider["display_name"])
        self.assertEqual("http://jellyfin.local", provider["server_url"])
        self.assertEqual("jellyfin", result["media_servers"]["active"])

        public_config = sanitize_config_for_web(result)

        public_provider = public_config["media_servers"]["providers"]["jellyfin"]
        self.assertTrue(public_provider["access_token_configured"])
        self.assertNotIn("access_token", public_provider)
        self.assertNotIn("user_id", public_provider)


class LoadLibrariesTest(unittest.TestCase):
    @patch("home_cinema_control.media_servers.jellyfin.web_config._authenticated_user_id")
    @patch("home_cinema_control.media_servers.jellyfin.web_config._authenticated_client")
    def test_writes_libraries_into_active_providers_playback(
            self, mock_client_factory, mock_user_id
    ):
        mock_user_id.return_value = "user-1"
        mock_client = MagicMock()
        mock_client.get_user_views.return_value = [
            {"Id": "1", "Name": "Movies"},
            {"Id": "2", "Name": "Series"},
        ]
        mock_client_factory.return_value = mock_client

        config = {
            "media_servers": {
                "active": "jellyfin",
                "providers": {"jellyfin": {"server_url": "http://jf"}},
            }
        }

        result = load_libraries(config)

        provider = get_media_server_provider(result, "jellyfin")
        self.assertEqual(2, len(provider.playback.libraries))
        self.assertEqual("Movies", provider.playback.libraries[0].name)
        for library in provider.playback.libraries:
            self.assertIsInstance(library, MediaServerLibrary)

    @patch("home_cinema_control.media_servers.jellyfin.web_config._authenticated_user_id")
    @patch("home_cinema_control.media_servers.jellyfin.web_config._authenticated_client")
    def test_does_not_touch_other_providers_libraries(self, mock_client_factory, mock_user_id):
        mock_user_id.return_value = "user-1"
        mock_client = MagicMock()
        mock_client.get_user_views.return_value = [{"Id": "1", "Name": "Movies"}]
        mock_client_factory.return_value = mock_client

        config = {
            "media_servers": {
                "active": "jellyfin",
                "providers": {
                    "jellyfin": {"server_url": "http://jf"},
                    "emby": {
                        "playback": {"libraries": [{"id": "9", "name": "Old", "active": True}]}
                    },
                },
            }
        }

        result = load_libraries(config)

        emby = get_media_server_provider(result, "emby")
        self.assertEqual(1, len(emby.playback.libraries))
        self.assertEqual("Old", emby.playback.libraries[0].name)


class LoadSelectableFoldersTest(unittest.TestCase):
    @patch("home_cinema_control.media_servers.jellyfin.web_config._authenticated_client")
    def test_path_mappings_are_real_pathmappingconfig_instances(self, mock_client_factory):
        # Regression test for the gotcha that sank the previous attempt at
        # this spec: model_copy(update=...) does not validate on assignment,
        # so a plain dict assigned to a typed list field silently stays a
        # dict instead of becoming a PathMappingConfig.
        mock_client = MagicMock()
        mock_client.get_virtual_folders.return_value = [
            {"Name": "Movies", "Locations": ["/media/movies"]}
        ]
        mock_client_factory.return_value = mock_client

        config = {
            "media_servers": {
                "active": "jellyfin",
                "providers": {
                    "jellyfin": {
                        "server_url": "http://jf",
                        "playback": {"use_all_libraries": True},
                    }
                },
            }
        }

        result = load_selectable_folders(config)

        provider = get_media_server_provider(result, "jellyfin")
        self.assertEqual(1, len(provider.playback.path_mappings))
        for mapping in provider.playback.path_mappings:
            self.assertIsInstance(mapping, PathMappingConfig)
        self.assertEqual("/media/movies", provider.playback.path_mappings[0].source_path)

    @patch("home_cinema_control.media_servers.jellyfin.web_config._authenticated_client")
    def test_does_not_touch_other_providers_path_mappings(self, mock_client_factory):
        mock_client = MagicMock()
        mock_client.get_virtual_folders.return_value = [
            {"Name": "Movies", "Locations": ["/media/movies"]}
        ]
        mock_client_factory.return_value = mock_client

        config = {
            "media_servers": {
                "active": "jellyfin",
                "providers": {
                    "jellyfin": {
                        "server_url": "http://jf",
                        "playback": {"use_all_libraries": True},
                    },
                    "emby": {
                        "playback": {
                            "path_mappings": [
                                {"name": "Old", "source_path": "/old", "verified": True}
                            ]
                        }
                    },
                },
            }
        }

        result = load_selectable_folders(config)

        emby = get_media_server_provider(result, "emby")
        self.assertEqual(1, len(emby.playback.path_mappings))
        self.assertEqual("/old", emby.playback.path_mappings[0].source_path)
        self.assertTrue(emby.playback.path_mappings[0].verified)


if __name__ == "__main__":
    unittest.main()
