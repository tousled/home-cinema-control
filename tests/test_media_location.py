import unittest

from home_cinema_control.playback.media_location import (
    resolve_player_media_file_location,
)


class ResolvePlayerMediaFileLocationTest(unittest.TestCase):
    def test_explicit_playback_filename_keeps_mapped_physical_directory(self):
        location = resolve_player_media_file_location(
            emby_media_path="/media/library/Movie/Movie.strm",
            playback_file_format="mkv",
            playback_file_name="Movie.mkv",
            path_mappings=[
                {
                    "source_path": "/media/library",
                    "player_path": "/nas",
                    "protocol": "nfs",
                    "verified": True,
                }
            ],
        )

        self.assertEqual("nas", location.content_server)
        self.assertEqual("Movie", location.content_directory)
        self.assertEqual("Movie.mkv", location.playback_file_name)

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
                            "verified": True,
                        }
                    ],
                )

                self.assertEqual(case["expected"][0], location.content_server)
                self.assertEqual(case["expected"][1], location.content_directory)
                self.assertEqual(case["expected"][2], location.playback_file_name)

    def test_rejects_a_media_path_without_a_matching_mapping(self):
        cases = [
            ("linux source mismatch", "/emby/Movies/Movie.mkv", "/jf"),
            ("windows source mismatch", r"Z:\Movies\Movie.mkv", "Y:\\"),
        ]

        for name, media_path, source_path in cases:
            with self.subTest(name):
                with self.assertRaisesRegex(
                    ValueError, "No verified path mapping matches"
                ):
                    resolve_player_media_file_location(
                        emby_media_path=media_path,
                        playback_file_format="mkv",
                        path_mappings=[
                            {
                                "source_path": source_path,
                                "player_path": "/nas",
                                "protocol": "nfs",
                                "verified": True,
                            }
                        ],
                    )

    def test_selects_the_longest_verified_nested_mapping(self):
        location = resolve_player_media_file_location(
            emby_media_path="/media/Movies/4K/Alien.mkv",
            playback_file_format="mkv",
            path_mappings=[
                {
                    "source_path": "/media/Movies/4K",
                    "player_path": "/nas/Movies4K",
                    "verified": True,
                },
                {
                    "source_path": "/media/Movies",
                    "player_path": "/nas/Movies",
                    "verified": True,
                },
            ],
        )

        self.assertEqual("Movies4K/Alien.mkv", location.content_directory + "/" + location.playback_file_name)

    def test_rejects_unverified_specific_mapping_without_falling_back(self):
        with self.assertRaisesRegex(ValueError, "not verified"):
            resolve_player_media_file_location(
                emby_media_path="/media/Movies/4K/Alien.mkv",
                playback_file_format="mkv",
                path_mappings=[
                    {
                        "source_path": "/media/Movies",
                        "player_path": "/nas/Movies",
                        "verified": True,
                    },
                    {
                        "source_path": "/media/Movies/4K",
                        "player_path": "/nas/Movies4K",
                        "verified": False,
                    },
                ],
            )

    def test_does_not_match_a_sibling_directory_with_a_common_prefix(self):
        with self.assertRaisesRegex(ValueError, "No verified path mapping matches"):
            resolve_player_media_file_location(
                emby_media_path="/media/Movies-Old/Alien.mkv",
                playback_file_format="mkv",
                path_mappings=[
                    {
                        "source_path": "/media/Movies",
                        "player_path": "/nas/Movies",
                        "verified": True,
                    }
                ],
                )

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
                            "verified": True,
                            }
                        ],
                    )


if __name__ == "__main__":
    unittest.main()
