import unittest

from home_cinema_control.media_servers.emby.network_paths import (
    EmbyNetworkPathResolver,
    network_path_substitutions,
    to_library_path,
)


SERVER_MOVIES_PATH = "/sharefolder/Video/Movies"
NETWORK_MOVIES_PATH = r"\\192.168.50.110\volume1\Video\Movies"


def _virtual_folders():
    return [
        {
            "Name": "Películas",
            "LibraryOptions": {
                "PathInfos": [
                    {
                        "Path": SERVER_MOVIES_PATH,
                        "NetworkPath": NETWORK_MOVIES_PATH,
                    }
                ]
            },
        }
    ]


class EmbyNetworkPathTest(unittest.TestCase):
    def test_maps_shared_network_path_to_the_configured_library_path(self):
        substitutions = network_path_substitutions(_virtual_folders())

        self.assertEqual(
            f"{SERVER_MOVIES_PATH}/Dune (2021)/Dune.mkv",
            to_library_path(
                f"{NETWORK_MOVIES_PATH}\\Dune (2021)\\Dune.mkv",
                substitutions,
            ),
        )

    def test_does_not_match_a_sibling_network_folder(self):
        substitutions = network_path_substitutions(_virtual_folders())

        self.assertEqual(
            f"{NETWORK_MOVIES_PATH}4K\\Dune.mkv",
            to_library_path(f"{NETWORK_MOVIES_PATH}4K\\Dune.mkv", substitutions),
        )

    def test_prefers_the_longest_network_path(self):
        substitutions = network_path_substitutions(
            [
                {
                    "LibraryOptions": {
                        "PathInfos": [
                            {"Path": "/sharefolder/Video", "NetworkPath": r"\\nas\Video"},
                            {
                                "Path": SERVER_MOVIES_PATH,
                                "NetworkPath": NETWORK_MOVIES_PATH,
                            },
                        ]
                    }
                }
            ]
        )

        self.assertEqual(
            f"{SERVER_MOVIES_PATH}/Dune.mkv",
            to_library_path(f"{NETWORK_MOVIES_PATH}\\Dune.mkv", substitutions),
        )


class EmbyNetworkPathResolverTest(unittest.TestCase):
    def test_caches_virtual_folders_and_refreshes_after_ttl(self):
        now = [0.0]
        fetch_count = [0]

        def fetch_virtual_folders():
            fetch_count[0] += 1
            return _virtual_folders()

        resolver = EmbyNetworkPathResolver(
            fetch_virtual_folders,
            cache_seconds=300,
            monotonic=lambda: now[0],
        )

        resolver.to_library_path(NETWORK_MOVIES_PATH)
        resolver.to_library_path(NETWORK_MOVIES_PATH)
        self.assertEqual(1, fetch_count[0])

        now[0] = 300
        resolver.to_library_path(NETWORK_MOVIES_PATH)
        self.assertEqual(2, fetch_count[0])

    def test_keeps_the_last_known_mapping_when_refresh_fails(self):
        responses = [_virtual_folders(), RuntimeError("Emby unavailable")]

        def fetch_virtual_folders():
            response = responses.pop(0)
            if isinstance(response, Exception):
                raise response
            return response

        now = [0.0]
        resolver = EmbyNetworkPathResolver(
            fetch_virtual_folders,
            cache_seconds=300,
            monotonic=lambda: now[0],
        )

        first = resolver.to_library_path(NETWORK_MOVIES_PATH)
        now[0] = 300
        second = resolver.to_library_path(NETWORK_MOVIES_PATH)

        self.assertEqual(SERVER_MOVIES_PATH, first)
        self.assertEqual(SERVER_MOVIES_PATH, second)


if __name__ == "__main__":
    unittest.main()
