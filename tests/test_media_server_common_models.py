import unittest

from home_cinema_control.media_servers.common.models import (
    MediaServerSession,
    find_controlling_session_id,
)


def _session(id_, device_id, user_id, last_activity_at=""):
    return MediaServerSession(
        client_session_id=id_,
        device_id=device_id,
        user_id=user_id,
        last_activity_at=last_activity_at,
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


if __name__ == "__main__":
    unittest.main()
