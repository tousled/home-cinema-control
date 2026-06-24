import unittest

from home_cinema_control.media_servers.jellyfin.session import JellyfinSession


class FakeJellyfinClient:
    def __init__(self, sessions=None):
        self._sessions = sessions

    def get_sessions(self):
        return self._sessions


def _session_with_client(client) -> JellyfinSession:
    session = JellyfinSession.__new__(JellyfinSession)
    session.client = client
    return session


class FindControllingSessionIdTest(unittest.TestCase):
    """Regression test: Jellyfin's "Play" websocket message has the same gap
    as Emby's — it never identifies the controller's own session, only the
    bridge's own target session. Without this resolution, every startup
    notification for Jellyfin-originated playback silently skipped sending
    (no active source session is available), reported by Pedro as "no veo
    notificaciones en Jellyfin".
    """

    def test_returns_none_without_a_controlling_user(self):
        session = _session_with_client(FakeJellyfinClient())

        self.assertIsNone(session.find_controlling_session_id(""))

    def test_returns_none_when_only_the_bridge_own_session_is_active(self):
        session = _session_with_client(
            FakeJellyfinClient(
                sessions=[
                    {"Id": "bridge-session", "DeviceId": "home-cinema-control", "UserId": "user-1"},
                ]
            )
        )

        self.assertIsNone(session.find_controlling_session_id("user-1"))

    def test_excludes_other_users_sessions(self):
        session = _session_with_client(
            FakeJellyfinClient(
                sessions=[
                    {"Id": "other-user-session", "DeviceId": "tv-device", "UserId": "user-2"},
                ]
            )
        )

        self.assertIsNone(session.find_controlling_session_id("user-1"))

    def test_picks_the_most_recently_active_session_excluding_the_bridge(self):
        session = _session_with_client(
            FakeJellyfinClient(
                sessions=[
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
