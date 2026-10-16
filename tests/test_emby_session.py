import unittest

from home_cinema_control.playback.content_kind import MediaContentKind
from home_cinema_control.media_servers.emby.network_paths import EmbyNetworkPathResolver
from home_cinema_control.media_servers.emby.session import EmbySession


class FakeEmbyClient:
    def __init__(self, item_data=None, sessions_by_user=None, playback_info=None):
        self._item_data = item_data
        self._sessions_by_user = sessions_by_user
        self._playback_info = playback_info if playback_info is not None else {}
        self.playback_info_calls = 0
        self.item_info_calls = 0
        self.capabilities_payload = None

    def get_virtual_folders(self):
        return []

    def get_item_info(self, user_id, item_id):
        self.item_info_calls += 1
        return self._item_data

    def get_item_playback_info(self, user_id, item_id):
        self.playback_info_calls += 1
        return self._playback_info

    def get_sessions_by_user(self, user_id):
        return self._sessions_by_user

    def set_capabilities(self, payload):
        self.capabilities_payload = payload
        return FakeResponse()


class FakeResponse:
    text = ""


def _session_with_client(client) -> EmbySession:
    session = EmbySession.__new__(EmbySession)
    session.client = client
    session._item_info_cache = {}
    session._track_cache = {}
    session._network_path_resolver = EmbyNetworkPathResolver(client.get_virtual_folders)
    session._refresh_session_info = lambda: None
    return session


class SetCapabilitiesTest(unittest.TestCase):
    def test_registers_hcc_as_video_only_playback_target(self):
        client = FakeEmbyClient()

        _session_with_client(client).set_capabilities()

        self.assertEqual(["Video"], client.capabilities_payload["PlayableMediaTypes"])


class LibraryPathMembershipTest(unittest.TestCase):
    def test_does_not_treat_sibling_directory_as_part_of_library(self):
        client = FakeEmbyClient()
        client.get_selectable_media_folders = lambda: [
            {
                "Id": "movies",
                "SubFolders": [{"Path": "/media/Movies"}],
            }
        ]
        session = _session_with_client(client)

        self.assertTrue(
            session.is_item_path_in_library("movies", "/media/Movies/Alien.mkv")
        )
        self.assertFalse(
            session.is_item_path_in_library("movies", "/media/Movies-Old/Alien.mkv")
        )


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


class GetItemTracksTest(unittest.TestCase):
    def test_uses_playback_info_for_the_active_media_source_and_reuses_it(self):
        client = FakeEmbyClient(
            item_data={"MediaStreams": [{"Type": "Audio", "Index": 99}]},
            playback_info={
                "MediaSources": [
                    {
                        "Id": "source-1",
                        "MediaStreams": [{"Type": "Audio", "Index": 1}],
                    },
                    {
                        "Id": "source-2",
                        "MediaStreams": [{"Type": "Audio", "Index": 4}],
                    },
                ]
            },
        )
        session = _session_with_client(client)

        tracks = session.get_item_tracks("user-1", "item-1", "source-2")
        cached_tracks = session.get_item_tracks("user-1", "item-1", "source-2")

        self.assertEqual([4], [track.source_index for track in tracks])
        self.assertIs(tracks, cached_tracks)
        self.assertEqual(1, client.playback_info_calls)
        self.assertEqual(0, client.item_info_calls)

    def test_falls_back_to_existing_item_metadata_when_playback_info_has_no_tracks(self):
        client = FakeEmbyClient(
            item_data={
                "MediaSources": [
                    {
                        "Id": "source-1",
                        "MediaStreams": [{"Type": "Subtitle", "Index": 6}],
                    }
                ]
            },
            playback_info={"MediaSources": [{"Id": "source-1", "MediaStreams": []}]},
        )
        session = _session_with_client(client)

        tracks = session.get_item_tracks("user-1", "item-1", "source-1")

        self.assertEqual([6], [track.source_index for track in tracks])
        self.assertEqual(1, client.playback_info_calls)
        self.assertEqual(1, client.item_info_calls)


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
                        "UserId": "user-1",
                        "LastActivityDate": "2026-06-22T13:50:00Z",
                    },
                    {
                        "Id": "tv-session",
                        "DeviceId": "tv-device",
                        "UserId": "user-1",
                        "LastActivityDate": "2026-06-22T13:41:04Z",
                    },
                    {
                        "Id": "phone-session",
                        "DeviceId": "phone-device",
                        "UserId": "user-1",
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
