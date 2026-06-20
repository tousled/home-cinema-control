import unittest
from unittest.mock import patch

from home_cinema_control.config.manager import sanitize_config_for_web

from home_cinema_control.media_servers.emby.web_config import (
    build_control_device_config,
    build_library_config,
    build_selectable_folder_servers,
    configure_emby_token,
    is_library_active,
)


class BuildControlDeviceConfigTest(unittest.TestCase):
    def test_returns_filtered_device_list(self):
        devices = [
            {"ReportedDeviceId": "abc", "Name": "My TV", "AppName": "Emby for LG"},
        ]

        result = build_control_device_config(devices)

        self.assertEqual(1, len(result))
        self.assertEqual("abc", result[0]["Id"])
        self.assertEqual("My TV / Emby for LG", result[0]["Name"])

    def test_excludes_bridge_device_id(self):
        devices = [
            {"ReportedDeviceId": "home-cinema-control", "Name": "HCC", "AppName": "Home Cinema Control"},
            {"ReportedDeviceId": "real-device", "Name": "Phone", "AppName": "Emby for Android"},
        ]

        result = build_control_device_config(devices)

        self.assertEqual(1, len(result))
        self.assertEqual("real-device", result[0]["Id"])

    def test_does_not_filter_old_xnoppo_client_name(self):
        devices = [
            {"ReportedDeviceId": "Xnoppo", "Name": "Old bridge", "AppName": "Xnoppo"},
        ]

        result = build_control_device_config(devices)

        self.assertEqual(1, len(result))
        self.assertEqual("Xnoppo", result[0]["Id"])

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

        self.assertEqual("Smart TV", result[0]["Name"])

    def test_preserves_original_device_fields(self):
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

        self.assertEqual("192.168.1.10", result[0]["IpAddress"])
        self.assertEqual("pedro", result[0]["LastUserName"])

    def test_empty_input_returns_empty_list(self):
        self.assertEqual([], build_control_device_config([]))


class BuildLibraryConfigTest(unittest.TestCase):
    def test_builds_library_list_from_views(self):
        views = [{"Id": "1", "Name": "Movies"}, {"Id": "2", "Name": "Series"}]

        result = build_library_config(views, existing_libraries=[])

        self.assertEqual(2, len(result))
        self.assertEqual("1", result[0]["Id"])
        self.assertEqual("Movies", result[0]["Name"])
        self.assertFalse(result[0]["Active"])

    def test_preserves_active_flag_from_existing(self):
        views = [{"Id": "1", "Name": "Movies"}]
        existing = [{"Id": "1", "Name": "Movies", "Active": True}]

        result = build_library_config(views, existing_libraries=existing)

        self.assertTrue(result[0]["Active"])

    def test_new_library_not_in_existing_defaults_to_inactive(self):
        views = [{"Id": "99", "Name": "New Library"}]

        result = build_library_config(views, existing_libraries=[])

        self.assertFalse(result[0]["Active"])

    def test_skips_view_without_id(self):
        views = [{"Id": "", "Name": "No ID"}, {"Id": "2", "Name": "Valid"}]

        result = build_library_config(views, existing_libraries=[])

        self.assertEqual(1, len(result))
        self.assertEqual("2", result[0]["Id"])

    def test_empty_views_returns_empty_list(self):
        result = build_library_config([], existing_libraries=[{"Id": "1", "Name": "Old"}])

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
            libraries=[{"Name": "Movies", "Active": True}],
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
            libraries=[{"Name": "Trailers", "Active": False}],
            existing_servers=[],
            enable_all_libraries=False,
        )

        self.assertEqual([], result)

    def test_includes_inactive_library_when_all_enabled(self):
        folders = [self._folder("Trailers", ["/media/trailers"])]

        result = build_selectable_folder_servers(
            folders,
            libraries=[{"Name": "Trailers", "Active": False}],
            existing_servers=[],
            enable_all_libraries=True,
        )

        self.assertEqual(1, len(result))

    def test_preserves_oppo_path_and_test_ok_from_existing(self):
        folders = [self._folder("Movies", ["/media/movies"])]
        existing = [{"source_path": "/media/movies", "player_path": "/mnt/movies", "verified": True}]

        result = build_selectable_folder_servers(
            folders,
            libraries=[{"Name": "Movies", "Active": True}],
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
            libraries=[{"Name": "Movies", "Active": True}],
            existing_servers=[],
            enable_all_libraries=False,
        )

        self.assertEqual("Movies", result[0]["name"])
        self.assertEqual("Movies(2)", result[1]["name"])

    def test_skips_subfolder_without_path(self):
        folders = [{"Name": "Movies", "SubFolders": [{"Id": "1", "Path": ""}]}]

        result = build_selectable_folder_servers(
            folders,
            libraries=[{"Name": "Movies", "Active": True}],
            existing_servers=[],
            enable_all_libraries=False,
        )

        self.assertEqual([], result)


class IsLibraryActiveTest(unittest.TestCase):
    def test_returns_true_for_active_library(self):
        libraries = [{"Name": "Movies", "Active": True}]
        self.assertTrue(is_library_active(libraries, "Movies"))

    def test_returns_false_for_inactive_library(self):
        libraries = [{"Name": "Movies", "Active": False}]
        self.assertFalse(is_library_active(libraries, "Movies"))

    def test_returns_false_when_library_not_found(self):
        self.assertFalse(is_library_active([], "Movies"))

    def test_returns_false_for_unknown_library_name(self):
        libraries = [{"Name": "Movies", "Active": True}]
        self.assertFalse(is_library_active(libraries, "Trailers"))


class ConfigureEmbyTokenTest(unittest.TestCase):
    @patch("home_cinema_control.media_servers.emby.web_config._authenticate_with_temporary_password")
    def test_returns_effective_config_with_token_for_secret_persistence(self, mock_authenticate):
        mock_authenticate.return_value = {
            "AccessToken": "emby-token",
            "User": {"Id": "emby-user", "Name": "Pedro"},
        }

        result = configure_emby_token(
            {"media_server": {"type": "emby", "server_url": "http://emby.local/"}},
            {"user_name": "pedro", "password": "secret"},
        )

        self.assertEqual("emby-token", result["media_server"]["access_token"])
        self.assertEqual("emby-user", result["media_server"]["user_id"])
        self.assertTrue(result["media_server"]["access_token_configured"])
        self.assertEqual("Pedro", result["media_server"]["display_name"])
        self.assertEqual("http://emby.local", result["media_server"]["server_url"])

        public_config = sanitize_config_for_web(result)

        self.assertTrue(public_config["media_server"]["access_token_configured"])
        self.assertNotIn("access_token", public_config["media_server"])
        self.assertNotIn("user_id", public_config["media_server"])


if __name__ == "__main__":
    unittest.main()