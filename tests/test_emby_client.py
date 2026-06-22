import unittest

from home_cinema_control.media_servers.emby import EmbyClient


class FakeResponse:
    def __init__(self, *, text="", json_data=None, status_code=200):
        self.text = text
        self._json_data = json_data
        self.status_code = status_code

    def json(self):
        return self._json_data


class RecordingHttpSession:
    def __init__(self):
        self.calls = []

    def post(self, url, *, data=None, json=None, headers=None):
        self.calls.append(("post", url, data, json, headers))
        return FakeResponse(json_data={"ok": True})

    def delete(self, url, *, headers=None):
        self.calls.append(("delete", url, headers))
        return FakeResponse(json_data={"ok": True})

    def get(self, url, *, headers=None):
        self.calls.append(("get", url, headers))
        return FakeResponse(text='{"ok":true}', json_data={"ok": True})


class EmbyClientTest(unittest.TestCase):
    def test_authenticate_uses_configured_token_without_password_login(self):
        http = RecordingHttpSession()
        client = EmbyClient(
            "http://emby.local:8096",
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
        client = EmbyClient(
            "http://emby.local:8096",
            access_token="",
            user_id="user1",
            display_name="Pedro",
            http_session=RecordingHttpSession(),
        )

        with self.assertRaisesRegex(RuntimeError, "missing media_server.access_token"):
            client.authenticate()

    def test_authenticate_fails_without_user_id(self):
        client = EmbyClient(
            "http://emby.local:8096",
            access_token="token",
            user_id="",
            display_name="Pedro",
            http_session=RecordingHttpSession(),
        )

        with self.assertRaisesRegex(RuntimeError, "missing media_server.user_id"):
            client.authenticate()

    def test_playback_started_posts_json_payload_with_emby_token_header(self):
        http = RecordingHttpSession()
        client = EmbyClient(
            "http://emby.local:8096/",
            access_token="token",
            user_id="user1",
            display_name="Pedro",
            http_session=http,
        )
        client.authenticate()

        client.notify_playback_started({"ItemId": "movie1"})

        method, url, data, json_payload, headers = http.calls[0]
        self.assertEqual("post", method)
        self.assertEqual(
            "http://emby.local:8096/emby/Sessions/Playing/?format=json",
            url,
        )
        self.assertIsNone(data)
        self.assertEqual({"ItemId": "movie1"}, json_payload)
        self.assertEqual("token", headers["X-Emby-Token"])

    def test_playback_progress_posts_json_payload_with_emby_token_header(self):
        http = RecordingHttpSession()
        client = EmbyClient(
            "http://emby.local:8096/",
            access_token="token",
            user_id="user1",
            display_name="Pedro",
            http_session=http,
        )
        client.authenticate()

        client.report_playback_progress({"ItemId": "movie1"})

        method, url, data, json_payload, headers = http.calls[0]
        self.assertEqual("post", method)
        self.assertEqual(
            "http://emby.local:8096/emby/Sessions/Playing/Progress?format=json",
            url,
        )
        self.assertIsNone(data)
        self.assertEqual({"ItemId": "movie1"}, json_payload)
        self.assertEqual("token", headers["X-Emby-Token"])

    def test_playback_stopped_posts_json_payload_with_emby_token_header(self):
        http = RecordingHttpSession()
        client = EmbyClient(
            "http://emby.local:8096/",
            access_token="token",
            user_id="user1",
            display_name="Pedro",
            http_session=http,
        )
        client.authenticate()

        client.notify_playback_stopped({"ItemId": "movie1"})

        method, url, data, json_payload, headers = http.calls[0]
        self.assertEqual("post", method)
        self.assertEqual(
            "http://emby.local:8096/emby/Sessions/Playing/Stopped?format=json",
            url,
        )
        self.assertIsNone(data)
        self.assertEqual({"ItemId": "movie1"}, json_payload)
        self.assertEqual("token", headers["X-Emby-Token"])

    def test_mark_item_unplayed_deletes_played_item_with_emby_token_header(self):
        http = RecordingHttpSession()
        client = EmbyClient(
            "http://emby.local:8096/",
            access_token="token",
            user_id="user1",
            display_name="Pedro",
            http_session=http,
        )
        client.authenticate()

        client.mark_item_unplayed("user1", "movie1")

        method, url, headers = http.calls[0]
        self.assertEqual("delete", method)
        self.assertEqual(
            "http://emby.local:8096/emby/Users/user1/PlayedItems/movie1",
            url,
        )
        self.assertEqual("token", headers["X-Emby-Token"])


    def test_set_item_playback_position_posts_json_payload_with_emby_token_header(self):
        http = RecordingHttpSession()
        client = EmbyClient(
            "http://emby.local:8096/",
            access_token="token",
            user_id="user1",
            display_name="Pedro",
            http_session=http,
        )
        client.authenticate()

        client.set_item_playback_position(
            "user1",
            "movie1",
            {"PlaybackPositionTicks": 250_000_000, "Played": False},
        )

        method, url, data, json_payload, headers = http.calls[0]
        self.assertEqual("post", method)
        self.assertEqual(
            "http://emby.local:8096/emby/Users/user1/Items/movie1/UserData?format=json",
            url,
        )
        self.assertIsNone(data)
        self.assertEqual(
            {"PlaybackPositionTicks": 250_000_000, "Played": False},
            json_payload,
        )
        self.assertEqual("token", headers["X-Emby-Token"])

    def test_send_session_message_url_encodes_reserved_characters(self):
        http = RecordingHttpSession()
        client = EmbyClient(
            "http://emby.local:8096/",
            access_token="token",
            user_id="user1",
            display_name="Pedro",
            http_session=http,
        )
        client.authenticate()

        client.send_session_message("session-1", "Tom & Jerry #1 = fun", 3500)

        method, url, data, json_payload, headers = http.calls[0]
        self.assertEqual("post", method)
        self.assertEqual(
            "http://emby.local:8096/emby/Sessions/session-1/Message"
            "?Text=Tom%20%26%20Jerry%20%231%20%3D%20fun"
            "&Header=Notification&TimeoutMs=3500",
            url,
        )
        self.assertEqual("token", headers["X-Emby-Token"])

    def test_accepts_absolute_url_for_legacy_callers(self):
        http = RecordingHttpSession()
        client = EmbyClient(
            "http://emby.local:8096",
            access_token="token",
            user_id="user1",
            display_name="Pedro",
            http_session=http,
        )
        client.authenticate()

        text = client.get_text("http://emby.local:8096/emby/Devices?")

        method, url, headers = http.calls[0]
        self.assertEqual("get", method)
        self.assertEqual("http://emby.local:8096/emby/Devices?", url)
        self.assertEqual("token", headers["X-Emby-Token"])
        self.assertEqual('{"ok":true}', text)


if __name__ == "__main__":
    unittest.main()
