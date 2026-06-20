import unittest

from home_cinema_control.media_servers.jellyfin import JellyfinClient


class FakeResponse:
    def __init__(self, *, json_data=None, status_code=200):
        self._json_data = json_data
        self.status_code = status_code
        self.text = ""

    def json(self):
        return self._json_data


class RecordingHttpSession:
    def __init__(self):
        self.calls = []

    def post(self, url, *, data=None, json=None, headers=None):
        self.calls.append(("post", url, data, json, headers))
        return FakeResponse(json_data={"ok": True})

    def get(self, url, *, headers=None):
        self.calls.append(("get", url, headers))
        return FakeResponse(json_data={"ok": True})

    def delete(self, url, *, headers=None):
        self.calls.append(("delete", url, headers))
        return FakeResponse(json_data={"ok": True})


class JellyfinClientTest(unittest.TestCase):
    def test_authenticate_uses_configured_token_without_password_login(self):
        http = RecordingHttpSession()
        client = JellyfinClient(
            "http://jellyfin.local:8096",
            access_token="token",
            user_id="user1",
            display_name="Pedro",
            http_session=http,
        )

        user_info = client.authenticate()

        self.assertEqual([], http.calls)
        self.assertEqual("token", user_info["AccessToken"])
        self.assertEqual("user1", user_info["User"]["Id"])
        self.assertEqual("Pedro", user_info["User"]["Name"])

    def test_authenticate_fails_without_access_token(self):
        client = JellyfinClient(
            "http://jellyfin.local:8096",
            access_token="",
            user_id="user1",
            display_name="Pedro",
            http_session=RecordingHttpSession(),
        )

        with self.assertRaisesRegex(RuntimeError, "missing media_server.access_token"):
            client.authenticate()

    def test_authenticate_fails_without_user_id(self):
        client = JellyfinClient(
            "http://jellyfin.local:8096",
            access_token="token",
            user_id="",
            display_name="Pedro",
            http_session=RecordingHttpSession(),
        )

        with self.assertRaisesRegex(RuntimeError, "missing media_server.user_id"):
            client.authenticate()

    def test_set_capabilities_posts_json_payload_with_jellyfin_token_headers(self):
        http = RecordingHttpSession()
        client = JellyfinClient(
            "http://jellyfin.local:8096/",
            access_token="token",
            user_id="user1",
            display_name="Pedro",
            http_session=http,
        )
        client.authenticate()

        client.set_capabilities({"SupportsMediaControl": True})

        method, url, data, json_payload, headers = http.calls[0]
        self.assertEqual("post", method)
        self.assertEqual(
            "http://jellyfin.local:8096/Sessions/Capabilities/Full",
            url,
        )
        self.assertIsNone(data)
        self.assertEqual({"SupportsMediaControl": True}, json_payload)
        self.assertEqual("token", headers["X-Emby-Token"])
        self.assertEqual("token", headers["X-MediaBrowser-Token"])

    def test_get_library_paths_from_virtual_folders(self):
        http = RecordingHttpSession()
        http.get = lambda url, *, headers=None: (
            http.calls.append(("get", url, headers))
            or FakeResponse(
                json_data=[
                    {"Name": "Movies", "Locations": ["/media/movies", "/uhd"]},
                    {"Name": "Series", "Locations": ["/media/series"]},
                ]
            )
        )
        client = JellyfinClient(
            "http://jellyfin.local:8096",
            access_token="token",
            user_id="user1",
            display_name="Pedro",
            http_session=http,
        )
        client.authenticate()

        paths = client.get_library_paths()

        self.assertEqual(
            [
                {"library_name": "Movies", "source_path": "/media/movies"},
                {"library_name": "Movies", "source_path": "/uhd"},
                {"library_name": "Series", "source_path": "/media/series"},
            ],
            paths,
        )

    def test_playback_lifecycle_routes_are_jellyfin_native(self):
        http = RecordingHttpSession()
        client = _authenticated_client(http)

        client.notify_playback_started({"ItemId": "movie-1"})
        client.report_playback_progress({"ItemId": "movie-1"})
        client.notify_playback_stopped({"ItemId": "movie-1"})

        self.assertEqual(
            [
                "http://jellyfin.local:8096/Sessions/Playing",
                "http://jellyfin.local:8096/Sessions/Playing/Progress",
                "http://jellyfin.local:8096/Sessions/Playing/Stopped",
            ],
            [call[1] for call in http.calls],
        )
        self.assertEqual(["post", "post", "post"], [call[0] for call in http.calls])

    def test_played_and_resume_routes_are_jellyfin_native(self):
        http = RecordingHttpSession()
        client = _authenticated_client(http)

        client.mark_item_unplayed("user-1", "movie-1")
        client.set_item_playback_position(
            "user-1",
            "movie-1",
            {"PlaybackPositionTicks": 10},
        )

        self.assertEqual("delete", http.calls[0][0])
        self.assertEqual(
            "http://jellyfin.local:8096/UserPlayedItems/movie-1?userId=user-1",
            http.calls[0][1],
        )
        self.assertEqual("post", http.calls[1][0])
        self.assertEqual(
            "http://jellyfin.local:8096/UserItems/movie-1/UserData?userId=user-1",
            http.calls[1][1],
        )
        self.assertEqual({"PlaybackPositionTicks": 10}, http.calls[1][3])


def _authenticated_client(http):
    client = JellyfinClient(
        "http://jellyfin.local:8096",
        access_token="token",
        user_id="user1",
        display_name="Pedro",
        http_session=http,
    )
    client.authenticate()
    return client


if __name__ == "__main__":
    unittest.main()
