import unittest

from home_cinema_control.media_servers.jellyfin.track_resolver import (
    JellyfinTrackResolver,
)


class JellyfinTrackResolverTest(unittest.TestCase):
    def test_resolves_audio_track_through_jellyfin_session(self):
        session = RecordingJellyfinSession()
        resolver = JellyfinTrackResolver(session)

        result = resolver.resolve_audio_track(
            source_user_id="user-1",
            media_item_id="movie-1",
            selected_source_track_id=4,
        )

        self.assertEqual(40, result)
        self.assertEqual([("audio", "user-1", "movie-1", 4)], session.calls)

    def test_resolves_subtitle_track_through_jellyfin_session(self):
        session = RecordingJellyfinSession()
        resolver = JellyfinTrackResolver(session)

        result = resolver.resolve_subtitle_track(
            source_user_id="user-1",
            media_item_id="movie-1",
            selected_source_track_id=6,
        )

        self.assertEqual(60, result)
        self.assertEqual([("subtitle", "user-1", "movie-1", 6)], session.calls)


class RecordingJellyfinSession:
    def __init__(self):
        self.calls = []

    def resolve_audio_track_index(self, user_id, item_id, index):
        self.calls.append(("audio", user_id, item_id, index))
        return index * 10

    def resolve_subtitle_track_index(self, user_id, item_id, index):
        self.calls.append(("subtitle", user_id, item_id, index))
        return index * 10


if __name__ == "__main__":
    unittest.main()
