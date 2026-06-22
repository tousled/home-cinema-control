import unittest

from home_cinema_control.playback.content_kind import MediaContentKind
from home_cinema_control.media_servers.emby.session import EmbySession


class FakeEmbyClient:
    def __init__(self, item_data=None, sessions_by_user=None):
        self._item_data = item_data
        self._sessions_by_user = sessions_by_user

    def get_item_info(self, user_id, item_id):
        return self._item_data

    def get_sessions_by_user(self, user_id):
        return self._sessions_by_user


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


class FindControllingSessionIdTest(unittest.TestCase):
    def test_returns_none_without_a_controlling_user(self):
        session = _session_with_client(FakeEmbyClient())

        self.assertIsNone(session.find_controlling_session_id(""))

    def test_returns_none_when_only_the_bridge_own_session_is_active(self):
        session = _session_with_client(
            FakeEmbyClient(
                sessions_by_user=[
                    {"Id": "bridge-session", "DeviceId": "home-cinema-control"},
                ]
            )
        )

        self.assertIsNone(session.find_controlling_session_id("user-1"))

    def test_picks_the_most_recently_active_session_excluding_the_bridge(self):
        session = _session_with_client(
            FakeEmbyClient(
                sessions_by_user=[
                    {
                        "Id": "bridge-session",
                        "DeviceId": "home-cinema-control",
                        "LastActivityDate": "2026-06-22T13:50:00Z",
                    },
                    {
                        "Id": "tv-session",
                        "DeviceId": "tv-device",
                        "LastActivityDate": "2026-06-22T13:41:04Z",
                    },
                    {
                        "Id": "phone-session",
                        "DeviceId": "phone-device",
                        "LastActivityDate": "2026-06-22T13:45:56Z",
                    },
                ]
            )
        )

        self.assertEqual(
            "phone-session", session.find_controlling_session_id("user-1")
        )


if __name__ == "__main__":
    unittest.main()
