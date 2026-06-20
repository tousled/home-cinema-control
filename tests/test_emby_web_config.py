import unittest

from home_cinema_control.media_servers.common.models import (
    MediaServerLibrary,
    is_library_active,
)
from home_cinema_control.media_servers.emby.web_config import (
    build_control_device_config,
    build_library_config,
    build_selectable_folder_servers,
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


if __name__ == "__main__":
    unittest.main()
