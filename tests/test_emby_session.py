import unittest

from home_cinema_control.media_servers.emby.playback import MediaContentKind
from home_cinema_control.media_servers.emby.session import EmbySession


class FakeEmbyClient:
    def __init__(self, item_data):
        self._item_data = item_data

    def get_item_info(self, user_id, item_id):
        return self._item_data


def _session_with_client(client) -> EmbySession:
    session = EmbySession.__new__(EmbySession)
    session.client = client
    return session


class GetMediaSourceInfoTest(unittest.TestCase):
    def test_maps_matched_media_source_with_parent_item_metadata(self):
        session = _session_with_client(
            FakeEmbyClient(
                {
                    "Type": "Movie",
                    "Name": "Aquaman",
                    "ProductionYear": 2018,
                    "MediaSources": [
                        {
                            "Id": "source-1",
                            "Path": "/movies/aquaman.mkv",
                            "Container": "mkv",
                            "RunTimeTicks": 72_000_000_000,
                        },
                    ],
                }
            )
        )

        media_source = session.get_media_source_info("user-1", "item-1", "source-1")

        self.assertEqual("/movies/aquaman.mkv", media_source.path)
        self.assertEqual("mkv", media_source.container)
        self.assertEqual(7200, media_source.duration_seconds)
        self.assertEqual(2018, media_source.production_year)
        self.assertEqual("Aquaman", media_source.title)
        self.assertEqual(MediaContentKind.MOVIE, media_source.content_kind)

    def test_falls_back_to_full_item_when_media_source_not_found(self):
        session = _session_with_client(
            FakeEmbyClient(
                {
                    "Type": "Episode",
                    "Name": "Pilot",
                    "Path": "/tv/show/episode1.mkv",
                    "Container": "mkv",
                    "MediaSources": [],
                }
            )
        )

        media_source = session.get_media_source_info("user-1", "item-1", "missing-source")

        self.assertEqual("/tv/show/episode1.mkv", media_source.path)
        self.assertEqual("Pilot", media_source.title)
        self.assertEqual(MediaContentKind.EPISODE, media_source.content_kind)


if __name__ == "__main__":
    unittest.main()
