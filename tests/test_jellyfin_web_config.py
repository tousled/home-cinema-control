import unittest

from home_cinema_control.media_servers.jellyfin.web_config import (
    build_control_device_config,
    build_library_config,
    build_virtual_folder_servers,
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


if __name__ == "__main__":
    unittest.main()
