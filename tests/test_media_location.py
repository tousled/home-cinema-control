import unittest

from home_cinema_control.playback.media_location import (
    resolve_player_media_file_location,
)


class ResolvePlayerMediaFileLocationTest(unittest.TestCase):
    def test_joins_path_prefixes_without_relying_on_trailing_slashes(self):
        cases = [
            {
                "name": "linux destination without trailing slash",
                "media_path": "/emby/Movies/Movie.mkv",
                "source_path": "/emby",
                "player_path": "/nas",
                "expected": ("nas", "Movies", "Movie.mkv"),
            },
            {
                "name": "linux destination with trailing slash",
                "media_path": "/emby/Movies/Movie.mkv",
                "source_path": "/emby",
                "player_path": "/nas/",
                "expected": ("nas", "Movies", "Movie.mkv"),
            },
            {
                "name": "windows source and nfs destination from user report",
                "media_path": r"Z:\HD-Olimpo\La oveja Shaun\index.bdmv",
                "source_path": "Z:\\",
                "player_path": "//192.168.1.149/Z",
                "expected": (
                    "192.168.1.149",
                    "Z/HD-Olimpo/La oveja Shaun",
                    "index.bdmv",
                ),
            },
            {
                "name": "windows source and nfs destination with trailing slash",
                "media_path": r"Z:\HD-Olimpo\La oveja Shaun\index.bdmv",
                "source_path": "Z:\\",
                "player_path": "//192.168.1.149/Z/",
                "expected": (
                    "192.168.1.149",
                    "Z/HD-Olimpo/La oveja Shaun",
                    "index.bdmv",
                ),
            },
        ]

        for case in cases:
            with self.subTest(case["name"]):
                location = resolve_player_media_file_location(
                    emby_media_path=case["media_path"],
                    playback_file_format="mkv",
                    path_mappings=[
                        {
                            "source_path": case["source_path"],
                            "player_path": case["player_path"],
                            "protocol": "nfs",
                        }
                    ],
                )

                self.assertEqual(case["expected"][0], location.content_server)
                self.assertEqual(case["expected"][1], location.content_directory)
                self.assertEqual(case["expected"][2], location.playback_file_name)

    def test_does_not_apply_a_mapping_when_the_source_is_not_a_path_prefix(self):
        cases = [
            ("linux source mismatch", "/emby/Movies/Movie.mkv", "/jf", "emby"),
            ("windows source mismatch", r"Z:\Movies\Movie.mkv", "Y:\\", "Z:"),
        ]

        for name, media_path, source_path, expected_server in cases:
            with self.subTest(name):
                location = resolve_player_media_file_location(
                    emby_media_path=media_path,
                    playback_file_format="mkv",
                    path_mappings=[
                        {
                            "source_path": source_path,
                            "player_path": "/nas",
                            "protocol": "nfs",
                        }
                    ],
                )

                self.assertEqual(
                    expected_server,
                    location.content_server,
                )
                self.assertIsNone(location.network_protocol)

    def test_rejects_an_unusable_destination_for_linux_and_windows_mappings(self):
        cases = [
            {
                "name": "linux destination has no media folder",
                "media_path": "/emby/Movie.mkv",
                "source_path": "/emby",
                "player_path": "/nas",
            },
            {
                "name": "windows destination has no media folder",
                "media_path": r"Z:\Movie.mkv",
                "source_path": "Z:\\",
                "player_path": "//server",
            },
        ]

        for case in cases:
            with self.subTest(case["name"]):
                with self.assertRaises(ValueError):
                    resolve_player_media_file_location(
                        emby_media_path=case["media_path"],
                        playback_file_format="mkv",
                        path_mappings=[
                            {
                                "source_path": case["source_path"],
                                "player_path": case["player_path"],
                                "protocol": "nfs",
                            }
                        ],
                    )


if __name__ == "__main__":
    unittest.main()
