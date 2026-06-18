import unittest

from home_cinema_control.playback.media_location import (
    PlayerMediaFileLocationError,
    resolve_player_media_file_location,
)


class PlayerMediaFileLocationTest(unittest.TestCase):
    def test_resolves_emby_path_to_player_media_file_location(self):
        location = resolve_player_media_file_location(
            emby_media_path="/volume1/Video/Movies/Full UHD/Movie.iso",
            playback_file_format="blurayiso",
            path_mappings=[
                {
                    "source_path": "/volume1/Video/Movies",
                    "player_path": "/192.168.1.100/volume1/Video/Movies",
                }
            ],
        )

        self.assertEqual("192.168.1.100", location.content_server)
        self.assertEqual("volume1/Video/Movies/Full UHD", location.content_directory)
        self.assertEqual("Movie.iso", location.playback_file_name)
        self.assertEqual("blurayiso", location.playback_file_format)
        self.assertIsNone(location.network_protocol)

    def test_resolves_mapping_protocol_to_player_media_file_location(self):
        location = resolve_player_media_file_location(
            emby_media_path="/volume1/Video/Trailers/Trailer.mkv",
            playback_file_format="mkv",
            path_mappings=[
                {
                    "source_path": "/volume1/Video/Trailers",
                    "player_path": "/NAS/Video/Trailers",
                    "protocol": "cifs",
                }
            ],
        )

        self.assertEqual("NAS", location.content_server)
        self.assertEqual("Video/Trailers", location.content_directory)
        self.assertEqual("Trailer.mkv", location.playback_file_name)
        self.assertEqual("cifs", location.network_protocol)

    def test_normalizes_windows_path_separators_after_mapping(self):
        location = resolve_player_media_file_location(
            emby_media_path=r"\\nas\Video\Movies\Movie.mkv",
            playback_file_format="mkv",
            path_mappings=[
                {
                    "source_path": r"\\nas\Video",
                    "player_path": "/192.168.1.100/volume1/Video",
                }
            ],
        )

        self.assertEqual("192.168.1.100", location.content_server)
        self.assertEqual("volume1/Video/Movies", location.content_directory)
        self.assertEqual("Movie.mkv", location.playback_file_name)

    def test_rejects_path_without_server_folder_and_file(self):
        with self.assertRaises(PlayerMediaFileLocationError):
            resolve_player_media_file_location(
                emby_media_path="/Movie.iso",
                playback_file_format="blurayiso",
                path_mappings=[],
            )

    def test_resolves_bdmv_folder_path_where_last_segment_has_no_extension(self):
        location = resolve_player_media_file_location(
            emby_media_path="/volume1/Video/Movies/MovieTitle",
            playback_file_format="bluray",
            path_mappings=[
                {
                    "source_path": "/volume1/Video/Movies",
                    "player_path": "/192.168.1.100/volume1/Video/Movies",
                }
            ],
        )

        self.assertEqual("192.168.1.100", location.content_server)
        self.assertEqual("volume1/Video/Movies", location.content_directory)
        self.assertEqual("MovieTitle", location.playback_file_name)
        self.assertEqual("bluray", location.playback_file_format)


if __name__ == "__main__":
    unittest.main()
