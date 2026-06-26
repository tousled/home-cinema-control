import unittest

from home_cinema_control.media_servers.common.models import (
    MediaServerNowPlaying,
    MediaServerSession,
    find_controlling_session_id,
    find_stale_playback_session_ids,
)


def _session(id_, device_id, user_id, last_activity_at=""):
    return MediaServerSession(
        client_session_id=id_,
        device_id=device_id,
        user_id=user_id,
        last_activity_at=last_activity_at,
    )


def _playing_session(id_, device_id, user_id, item_id):
    return MediaServerSession(
        client_session_id=id_,
        device_id=device_id,
        user_id=user_id,
        now_playing=MediaServerNowPlaying(item_id=item_id),
    )


def _idle_session(id_, device_id, user_id):
    return MediaServerSession(
        client_session_id=id_,
        device_id=device_id,
        user_id=user_id,
    )


class FindControllingSessionIdTest(unittest.TestCase):
    """Shared policy used by both EmbySession and JellyfinSession to resolve
    the real client session behind a remote Play command — see ADR-0001:
    each provider maps its own Sessions payload into MediaServerSession at
    its edge, then this one implementation decides which session controls.
    """

    def test_returns_none_without_a_controlling_user(self):
        sessions = [_session("s1", "device-1", "user-1")]

        self.assertIsNone(
            find_controlling_session_id(
                sessions, controlling_user_id="", own_device_id="home-cinema-control"
            )
        )

    def test_excludes_own_device(self):
        sessions = [_session("bridge", "home-cinema-control", "user-1")]

        self.assertIsNone(
            find_controlling_session_id(
                sessions,
                controlling_user_id="user-1",
                own_device_id="home-cinema-control",
            )
        )

    def test_excludes_other_users_sessions(self):
        sessions = [_session("other-session", "tv-device", "user-2")]

        self.assertIsNone(
            find_controlling_session_id(
                sessions,
                controlling_user_id="user-1",
                own_device_id="home-cinema-control",
            )
        )

    def test_picks_the_most_recently_active_matching_session(self):
        sessions = [
            _session("bridge", "home-cinema-control", "user-1", "2026-06-22T13:50:00Z"),
            _session("tv-session", "tv-device", "user-1", "2026-06-22T13:41:04Z"),
            _session("phone-session", "phone-device", "user-1", "2026-06-22T13:45:56Z"),
        ]

        result = find_controlling_session_id(
            sessions, controlling_user_id="user-1", own_device_id="home-cinema-control"
        )

        self.assertEqual("phone-session", result)


class FindStalePlaybackSessionIdsTest(unittest.TestCase):
    def test_keeps_source_session_when_session_list_is_empty(self):
        result = find_stale_playback_session_ids(
            [],
            controlling_user_id="user-1",
            media_library_item_id="movie-1",
            own_device_id="home-cinema-control",
            source_client_session_id="web-session",
        )

        self.assertEqual(["web-session"], result)

    def test_returns_source_plus_same_user_sessions_actively_playing_the_item(self):
        sessions = [
            _playing_session("bridge", "home-cinema-control", "user-1", "movie-1"),
            _playing_session("web-session", "web-device", "user-1", "movie-1"),
            _playing_session("phone-session", "phone-device", "user-1", "movie-1"),
            _idle_session("mobile-cleared-session", "mobile-device", "user-1"),
            _playing_session("other-item", "tablet-device", "user-1", "movie-2"),
            _playing_session("other-user", "guest-device", "user-2", "movie-1"),
        ]

        result = find_stale_playback_session_ids(
            sessions,
            controlling_user_id="user-1",
            media_library_item_id="movie-1",
            own_device_id="home-cinema-control",
            source_client_session_id="web-session",
        )

        self.assertEqual(
            ["web-session", "phone-session"],
            result,
        )

    def test_does_not_include_idle_non_source_sessions_as_cleanup_targets(self):
        """Regression: idle sessions (now_playing=None) must not receive a Stop.

        When a mobile client initiates Stop, Jellyfin clears its now_playing
        before HCC's cleanup query runs. Including that session as a stale
        target sends an extra Stop back to the mobile mid-transition, which
        freezes the playback screen instead of closing it.
        """
        mobile = _idle_session("mobile-session", "mobile-device", "user-1")
        sessions = [mobile]

        result = find_stale_playback_session_ids(
            sessions,
            controlling_user_id="user-1",
            media_library_item_id="movie-1",
            own_device_id="home-cinema-control",
            source_client_session_id="chrome-session",
        )

        self.assertNotIn("mobile-session", result)
        self.assertEqual(["chrome-session"], result)


if __name__ == "__main__":
    unittest.main()
