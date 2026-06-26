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
    is_library_active,
)
from home_cinema_control.media_servers.emby.web_config import (
    authenticate_legacy_credentials,
    build_control_device_config,
    build_library_config,
    build_selectable_folder_servers,
    configure_emby_token,
    load_devices,
    load_libraries,
    load_selectable_folders,
)


class BuildControlDeviceConfigTest(unittest.TestCase):
    def test_returns_filtered_device_list(self):
        devices = [
            {"ReportedDeviceId": "abc", "Name": "My TV", "AppName": "Emby for LG"},
        ]

        result = build_control_device_config(devices)

        self.assertEqual(1, len(result))
        self.assertEqual("abc", result[0].id)
        self.assertEqual("My TV / Emby for LG", result[0].name)

    def test_excludes_bridge_device_id(self):
        devices = [
            {"ReportedDeviceId": "home-cinema-control", "Name": "HCC", "AppName": "Home Cinema Control"},
            {"ReportedDeviceId": "real-device", "Name": "Phone", "AppName": "Emby for Android"},
        ]

        result = build_control_device_config(devices)

        self.assertEqual(1, len(result))
        self.assertEqual("real-device", result[0].id)

    def test_does_not_filter_old_xnoppo_client_name(self):
        devices = [
            {"ReportedDeviceId": "Xnoppo", "Name": "Old bridge", "AppName": "Xnoppo"},
        ]

        result = build_control_device_config(devices)

        self.assertEqual(1, len(result))
        self.assertEqual("Xnoppo", result[0].id)

    def test_excludes_bridge_app_name(self):
        devices = [
            {"ReportedDeviceId": "d1", "Name": "Something", "AppName": "Home Cinema Control"},
        ]

        result = build_control_device_config(devices)

        self.assertEqual([], result)

    def test_excludes_device_without_name(self):
        devices = [
            {"ReportedDeviceId": "d1", "Name": "", "AppName": "Emby Web"},
            {"ReportedDeviceId": "d2", "Name": "   ", "AppName": "Emby Web"},
        ]

        result = build_control_device_config(devices)

        self.assertEqual([], result)

    def test_excludes_device_without_reported_id(self):
        devices = [
            {"ReportedDeviceId": "", "Name": "No ID Device", "AppName": "Emby Web"},
        ]

        result = build_control_device_config(devices)

        self.assertEqual([], result)

    def test_display_name_without_app_name(self):
        devices = [
            {"ReportedDeviceId": "d1", "Name": "Smart TV", "AppName": ""},
        ]

        result = build_control_device_config(devices)

        self.assertEqual("Smart TV", result[0].name)

    @patch("home_cinema_control.media_servers.emby.web_config._authenticated_client")
    def test_load_devices_raises_when_provider_is_unreachable(self, mock_client_factory):
        mock_client_factory.side_effect = RuntimeError("offline")

        with self.assertRaisesRegex(RuntimeError, "Could not read Emby devices"):
            load_devices({"media_servers": {"active": "emby", "providers": {"emby": {}}}})

    def test_captures_app_name_and_drops_arbitrary_provider_fields(self):
        devices = [
            {
                "ReportedDeviceId": "d1",
                "Name": "TV",
                "AppName": "Emby for LG",
                "IpAddress": "192.168.1.10",
                "LastUserName": "pedro",
            }
        ]

        result = build_control_device_config(devices)

        self.assertEqual("Emby for LG", result[0].app_name)
        # The value object is the HCC contract, not a passthrough of the
        # provider payload: arbitrary API fields are not carried through.
        self.assertEqual(
            {"id", "name", "app_name"}, set(result[0].model_dump().keys())
        )

    def test_empty_input_returns_empty_list(self):
        self.assertEqual([], build_control_device_config([]))


class BuildLibraryConfigTest(unittest.TestCase):
    def test_builds_library_list_from_views(self):
        views = [{"Id": "1", "Name": "Movies"}, {"Id": "2", "Name": "Series"}]

        result = build_library_config(views, existing_libraries=[])

        self.assertEqual(2, len(result))
        self.assertEqual("1", result[0].id)
        self.assertEqual("Movies", result[0].name)
        self.assertFalse(result[0].active)

    def test_preserves_active_flag_from_existing(self):
        views = [{"Id": "1", "Name": "Movies"}]
        existing = [{"id": "1", "name": "Movies", "active": True}]

        result = build_library_config(views, existing_libraries=existing)

        self.assertTrue(result[0].active)

    def test_new_library_not_in_existing_defaults_to_inactive(self):
        views = [{"Id": "99", "Name": "New Library"}]

        result = build_library_config(views, existing_libraries=[])

        self.assertFalse(result[0].active)

    def test_skips_view_without_id(self):
        views = [{"Id": "", "Name": "No ID"}, {"Id": "2", "Name": "Valid"}]

        result = build_library_config(views, existing_libraries=[])

        self.assertEqual(1, len(result))
        self.assertEqual("2", result[0].id)

    def test_empty_views_returns_empty_list(self):
        result = build_library_config(
            [], existing_libraries=[{"id": "1", "name": "Old"}]
        )

        self.assertEqual([], result)


class BuildSelectableFolderServersTest(unittest.TestCase):
    def _folder(self, name, subfolders):
        return {
            "Name": name,
            "SubFolders": [{"Id": str(i), "Path": p} for i, p in enumerate(subfolders)],
        }

    def test_builds_server_list_from_media_folders(self):
        folders = [self._folder("Movies", ["/media/movies"])]

        result = build_selectable_folder_servers(
            folders,
            libraries=[{"name": "Movies", "active": True}],
            existing_servers=[],
            enable_all_libraries=False,
        )

        self.assertEqual(1, len(result))
        self.assertEqual("Movies", result[0]["name"])
        self.assertEqual("/media/movies", result[0]["source_path"])

    def test_skips_inactive_library_when_not_all_enabled(self):
        folders = [self._folder("Trailers", ["/media/trailers"])]

        result = build_selectable_folder_servers(
            folders,
            libraries=[{"name": "Trailers", "active": False}],
            existing_servers=[],
            enable_all_libraries=False,
        )

        self.assertEqual([], result)

    def test_includes_inactive_library_when_all_enabled(self):
        folders = [self._folder("Trailers", ["/media/trailers"])]

        result = build_selectable_folder_servers(
            folders,
            libraries=[{"name": "Trailers", "active": False}],
            existing_servers=[],
            enable_all_libraries=True,
        )

        self.assertEqual(1, len(result))

    def test_preserves_oppo_path_and_test_ok_from_existing(self):
        folders = [self._folder("Movies", ["/media/movies"])]
        existing = [{"source_path": "/media/movies", "player_path": "/mnt/movies", "verified": True}]

        result = build_selectable_folder_servers(
            folders,
            libraries=[{"name": "Movies", "active": True}],
            existing_servers=existing,
            enable_all_libraries=False,
        )

        self.assertEqual("/mnt/movies", result[0]["player_path"])
        self.assertTrue(result[0]["verified"])

    def test_multiple_subfolders_get_indexed_names(self):
        folders = [
            {
                "Name": "Movies",
                "SubFolders": [
                    {"Id": "1", "Path": "/vol1/movies"},
                    {"Id": "2", "Path": "/vol2/movies"},
                ],
            }
        ]

        result = build_selectable_folder_servers(
            folders,
            libraries=[{"name": "Movies", "active": True}],
            existing_servers=[],
            enable_all_libraries=False,
        )

        self.assertEqual("Movies", result[0]["name"])
        self.assertEqual("Movies(2)", result[1]["name"])

    def test_skips_subfolder_without_path(self):
        folders = [{"Name": "Movies", "SubFolders": [{"Id": "1", "Path": ""}]}]

        result = build_selectable_folder_servers(
            folders,
            libraries=[{"name": "Movies", "active": True}],
            existing_servers=[],
            enable_all_libraries=False,
        )

        self.assertEqual([], result)


class IsLibraryActiveTest(unittest.TestCase):
    def test_returns_true_for_active_library(self):
        libraries = [MediaServerLibrary(name="Movies", active=True)]
        self.assertTrue(is_library_active(libraries, "Movies"))

    def test_returns_false_for_inactive_library(self):
        libraries = [MediaServerLibrary(name="Movies", active=False)]
        self.assertFalse(is_library_active(libraries, "Movies"))

    def test_returns_false_when_library_not_found(self):
        self.assertFalse(is_library_active([], "Movies"))

    def test_returns_false_for_unknown_library_name(self):
        libraries = [MediaServerLibrary(name="Movies", active=True)]
        self.assertFalse(is_library_active(libraries, "Trailers"))


class ConfigureEmbyTokenTest(unittest.TestCase):
    @patch("home_cinema_control.media_servers.emby.web_config._authenticate_with_temporary_password")
    def test_returns_effective_config_with_token_for_secret_persistence(self, mock_authenticate):
        mock_authenticate.return_value = {
            "AccessToken": "emby-token",
            "User": {"Id": "emby-user", "Name": "Pedro"},
        }

        result = configure_emby_token(
            {
                "media_servers": {
                    "active": "emby",
                    "providers": {"emby": {"server_url": "http://emby.local/"}},
                }
            },
            MediaServerLoginCredentials(user_name="pedro", password="secret"),
        )

        provider = result["media_servers"]["providers"]["emby"]
        self.assertEqual("emby-token", provider["access_token"])
        self.assertEqual("emby-user", provider["user_id"])
        self.assertEqual("Pedro", provider["display_name"])
        self.assertEqual("http://emby.local", provider["server_url"])
        self.assertEqual("emby", result["media_servers"]["active"])

        public_config = sanitize_config_for_web(result)

        public_provider = public_config["media_servers"]["providers"]["emby"]
        self.assertTrue(public_provider["access_token_configured"])
        self.assertNotIn("access_token", public_provider)
        self.assertNotIn("user_id", public_provider)


class AuthenticateLegacyCredentialsTest(unittest.TestCase):
    @patch("home_cinema_control.media_servers.emby.web_config._authenticate_with_temporary_password")
    def test_returns_auth_response_on_success(self, mock_authenticate):
        mock_authenticate.return_value = {
            "AccessToken": "emby-token",
            "User": {"Id": "emby-user", "Name": "Pedro"},
        }

        result = authenticate_legacy_credentials("http://emby.local/", "pedro", "secret")

        self.assertEqual("emby-token", result["AccessToken"])
        mock_authenticate.assert_called_once_with(
            server_url="http://emby.local/", user_name="pedro", password="secret"
        )

    @patch("home_cinema_control.media_servers.emby.web_config._authenticate_with_temporary_password")
    def test_returns_none_when_authentication_raises(self, mock_authenticate):
        mock_authenticate.side_effect = RuntimeError("connection refused")

        result = authenticate_legacy_credentials("http://emby.local/", "pedro", "wrong")

        self.assertIsNone(result)


class LoadLibrariesTest(unittest.TestCase):
    @patch("home_cinema_control.media_servers.emby.web_config._authenticated_user_id")
    @patch("home_cinema_control.media_servers.emby.web_config._authenticated_client")
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
                "active": "emby",
                "providers": {"emby": {"server_url": "http://emby"}},
            }
        }

        result = load_libraries(config)

        provider = get_media_server_provider(result, "emby")
        self.assertEqual(2, len(provider.playback.libraries))
        self.assertEqual("Movies", provider.playback.libraries[0].name)
        for library in provider.playback.libraries:
            self.assertIsInstance(library, MediaServerLibrary)

    @patch("home_cinema_control.media_servers.emby.web_config._authenticated_user_id")
    @patch("home_cinema_control.media_servers.emby.web_config._authenticated_client")
    def test_does_not_touch_other_providers_libraries(self, mock_client_factory, mock_user_id):
        mock_user_id.return_value = "user-1"
        mock_client = MagicMock()
        mock_client.get_user_views.return_value = [{"Id": "1", "Name": "Movies"}]
        mock_client_factory.return_value = mock_client

        config = {
            "media_servers": {
                "active": "emby",
                "providers": {
                    "emby": {"server_url": "http://emby"},
                    "jellyfin": {
                        "playback": {"libraries": [{"id": "9", "name": "Old", "active": True}]}
                    },
                },
            }
        }

        result = load_libraries(config)

        jellyfin = get_media_server_provider(result, "jellyfin")
        self.assertEqual(1, len(jellyfin.playback.libraries))
        self.assertEqual("Old", jellyfin.playback.libraries[0].name)

    @patch("home_cinema_control.media_servers.emby.web_config._authenticated_client")
    def test_error_during_load_does_not_raise(self, mock_client_factory):
        mock_client_factory.side_effect = RuntimeError("connection failed")

        result = load_libraries({})

        self.assertIsInstance(result, dict)


class LoadSelectableFoldersTest(unittest.TestCase):
    @patch("home_cinema_control.media_servers.emby.web_config._authenticated_client")
    def test_path_mappings_are_real_pathmappingconfig_instances(self, mock_client_factory):
        # Regression test for the gotcha that sank the previous attempt at
        # this spec: model_copy(update=...) does not validate on assignment,
        # so a plain dict assigned to a typed list field silently stays a
        # dict instead of becoming a PathMappingConfig.
        mock_client = MagicMock()
        mock_client.get_selectable_media_folders.return_value = [
            {
                "Name": "Movies",
                "SubFolders": [{"Id": "1", "Path": "/media/movies"}],
            }
        ]
        mock_client_factory.return_value = mock_client

        config = {
            "media_servers": {
                "active": "emby",
                "providers": {
                    "emby": {
                        "server_url": "http://emby",
                        "playback": {"use_all_libraries": True},
                    }
                },
            }
        }

        result = load_selectable_folders(config)

        provider = get_media_server_provider(result, "emby")
        self.assertEqual(1, len(provider.playback.path_mappings))
        for mapping in provider.playback.path_mappings:
            self.assertIsInstance(mapping, PathMappingConfig)
        self.assertEqual("/media/movies", provider.playback.path_mappings[0].source_path)

    @patch("home_cinema_control.media_servers.emby.web_config._authenticated_client")
    def test_does_not_touch_other_providers_path_mappings(self, mock_client_factory):
        mock_client = MagicMock()
        mock_client.get_selectable_media_folders.return_value = [
            {"Name": "Movies", "SubFolders": [{"Id": "1", "Path": "/media/movies"}]}
        ]
        mock_client_factory.return_value = mock_client

        config = {
            "media_servers": {
                "active": "emby",
                "providers": {
                    "emby": {
                        "server_url": "http://emby",
                        "playback": {"use_all_libraries": True},
                    },
                    "jellyfin": {
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

        jellyfin = get_media_server_provider(result, "jellyfin")
        self.assertEqual(1, len(jellyfin.playback.path_mappings))
        self.assertEqual("/old", jellyfin.playback.path_mappings[0].source_path)
        self.assertTrue(jellyfin.playback.path_mappings[0].verified)


if __name__ == "__main__":
    unittest.main()
