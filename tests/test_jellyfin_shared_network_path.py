import unittest
from unittest.mock import MagicMock

from home_cinema_control.media_servers.jellyfin.client import JellyfinClient
from home_cinema_control.media_servers.jellyfin.session import JellyfinSession


SERVER_MOVIES_PATH = "/sharefolder/Video/Movies"
PLAYER_MOVIES_PATH = "/192.168.50.110/volume1/Video/Movies"
LEGACY_NETWORK_PATH = r"\\192.168.50.110\volume1\Video\Movies"


def _legacy_path_info():
    return {
        "Path": SERVER_MOVIES_PATH,
        "NetworkPath": LEGACY_NETWORK_PATH,
    }


def _virtual_folders():
    return [
        {
            "Name": "Películas",
            "ItemId": "movies",
            "Locations": [SERVER_MOVIES_PATH],
            "LibraryOptions": {"PathInfos": [_legacy_path_info()]},
        }
    ]


class JellyfinSharedNetworkPathContractTest(unittest.TestCase):
    def test_library_paths_use_locations_not_legacy_network_path(self):
        client = JellyfinClient(
            "http://jellyfin.local:8096",
            access_token="token",
            user_id="user-1",
            http_session=MagicMock(),
        )
        client.get_virtual_folders = MagicMock(return_value=_virtual_folders())

        self.assertEqual(
            [{"library_name": "Películas", "source_path": SERVER_MOVIES_PATH}],
            client.get_library_paths(),
        )

    def test_library_matching_expects_jellyfin_server_path(self):
        session = object.__new__(JellyfinSession)
        session.client = MagicMock()
        session.client.get_virtual_folders.return_value = _virtual_folders()

        self.assertTrue(
            session.is_item_path_in_library(
                "movies",
                f"{SERVER_MOVIES_PATH}/Dune (2021)/Dune.mkv",
            )
        )
        self.assertFalse(
            session.is_item_path_in_library(
                "movies",
                f"{LEGACY_NETWORK_PATH}\\Dune (2021)\\Dune.mkv",
            )
        )

    def test_media_source_path_remains_the_jellyfin_server_path(self):
        session = object.__new__(JellyfinSession)
        session.client = MagicMock()
        session.client.get_item_info.return_value = {
            "Name": "Dune (2021)",
            "Type": "Movie",
            "MediaSources": [
                {
                    "Id": "source-1",
                    "Path": f"{SERVER_MOVIES_PATH}/Dune (2021)/Dune.mkv",
                    "Container": "mkv",
                    "RunTimeTicks": 600000000,
                }
            ],
        }

        source = session.get_media_source_info("user-1", "item-1", "source-1")

        self.assertEqual(
            f"{SERVER_MOVIES_PATH}/Dune (2021)/Dune.mkv",
            source.path,
        )
        self.assertNotEqual(
            PLAYER_MOVIES_PATH,
            source.path,
        )


if __name__ == "__main__":
    unittest.main()
