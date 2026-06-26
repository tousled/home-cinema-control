import json
import unittest
import urllib.parse

from home_cinema_control.devices.oppo.control_api_client import (
    OppoControlApiClient,
    extract_host_from_url,
)
from home_cinema_control.devices.oppo.models import OppoCommandResponse


class RecordingOppoControlApiClient(OppoControlApiClient):
    def _call_player_endpoint(
        self,
        endpoint,
        query=None,
        *,
        timeout=None,
        suppress_exception_log=False,
    ):
        object.__setattr__(self, "last_endpoint", endpoint)
        object.__setattr__(self, "last_query", query)
        object.__setattr__(self, "last_timeout", timeout)
        object.__setattr__(self, "last_suppress_exception_log", suppress_exception_log)
        return OppoCommandResponse.from_text('{"success":true}')


def decode_query_payload(query):
    return json.loads(urllib.parse.unquote(query))


class OppoControlApiClientTest(unittest.TestCase):
    def test_extracts_host_from_emby_url_with_port(self):
        self.assertEqual(
            "192.168.1.100",
            extract_host_from_url("http://192.168.1.100:8096"),
        )

    def test_extracts_host_from_url_without_scheme(self):
        self.assertEqual(
            "emby.local",
            extract_host_from_url("emby.local:8096"),
        )

    def test_sign_in_uses_host_from_configured_media_server(self):
        client = RecordingOppoControlApiClient(
            player_host="192.168.1.50",
            media_server_host=extract_host_from_url("http://192.168.1.100:8096"),
        )

        response = client.sign_in()

        self.assertTrue(response.is_successful)
        self.assertEqual("signin", client.last_endpoint)
        self.assertEqual(
            {
                "appIconType": 1,
                "appIpAddress": "192.168.1.100",
            },
            decode_query_payload(client.last_query),
        )

    def test_sign_in_prefers_explicit_app_ip_address(self):
        client = RecordingOppoControlApiClient(
            player_host="192.168.1.50",
            media_server_host="192.168.1.100",
        )

        response = client.sign_in(app_ip_address="192.168.1.150")

        self.assertTrue(response.is_successful)
        self.assertEqual("signin", client.last_endpoint)
        self.assertEqual(
            {
                "appIconType": 1,
                "appIpAddress": "192.168.1.150",
            },
            decode_query_payload(client.last_query),
        )

    def test_from_config_uses_media_server_url_host_as_app_ip_address(self):
        client = OppoControlApiClient.from_config(
            {
                "oppo": {"ip": "192.168.1.50"},
                "media_servers": {
                    "active": "emby",
                    "providers": {"emby": {"server_url": "http://192.168.1.100:8096"}},
                },
            }
        )

        self.assertEqual("192.168.1.50", client.player_host)
        self.assertEqual("192.168.1.100", client.media_server_host)

    def test_from_config_reads_active_provider_from_migrated_shape(self):
        client = OppoControlApiClient.from_config(
            {
                "oppo": {"ip": "192.168.1.50"},
                "media_servers": {
                    "active": "jellyfin",
                    "providers": {
                        "emby": {"server_url": "http://192.168.1.200:8096"},
                        "jellyfin": {"server_url": "http://192.168.1.100:8096"},
                    },
                },
            }
        )

        self.assertEqual("192.168.1.100", client.media_server_host)

    def test_set_play_time_uses_media_control_endpoint_payload(self):
        client = RecordingOppoControlApiClient(player_host="192.168.1.50")

        response = client.set_play_time(3_723_000_0000)

        self.assertTrue(response.is_successful)
        self.assertEqual("setplaytime", client.last_endpoint)
        self.assertEqual(
            {
                "h": 1,
                "m": 2,
                "s": 3,
            },
            decode_query_payload(client.last_query),
        )

    def test_select_audio_track_uses_media_control_endpoint_payload(self):
        client = RecordingOppoControlApiClient(player_host="192.168.1.50")

        response = client.select_audio_track(2)

        self.assertTrue(response.is_successful)
        self.assertEqual("setaudiomenulist", client.last_endpoint)
        self.assertEqual(
            {"cur_index": 2},
            decode_query_payload(client.last_query),
        )

    def test_get_audio_menu_uses_media_control_endpoint(self):
        client = RecordingOppoControlApiClient(player_host="192.168.1.50")

        response = client.get_audio_menu()

        self.assertTrue(response.is_successful)
        self.assertEqual("getaudiomenulist", client.last_endpoint)
        self.assertEqual("", client.last_query)

    def test_select_subtitle_track_uses_media_control_endpoint_payload(self):
        client = RecordingOppoControlApiClient(player_host="192.168.1.50")

        response = client.select_subtitle_track(1)

        self.assertTrue(response.is_successful)
        self.assertEqual("setsubttmenulist", client.last_endpoint)
        self.assertEqual(
            {"cur_index": 1},
            decode_query_payload(client.last_query),
        )

    def test_get_subtitle_menu_uses_media_control_endpoint(self):
        client = RecordingOppoControlApiClient(player_host="192.168.1.50")

        response = client.get_subtitle_menu()

        self.assertTrue(response.is_successful)
        self.assertEqual("getsubtitlemenulist", client.last_endpoint)
        self.assertEqual("", client.last_query)
        self.assertFalse(client.last_suppress_exception_log)

    def test_get_subtitle_menu_suppresses_http_traceback_when_short_timeout_is_used(self):
        client = RecordingOppoControlApiClient(player_host="192.168.1.50")

        response = client.get_subtitle_menu(timeout=1.0)

        self.assertTrue(response.is_successful)
        self.assertEqual("getsubtitlemenulist", client.last_endpoint)
        self.assertEqual(1.0, client.last_timeout)
        self.assertTrue(client.last_suppress_exception_log)

    def test_uses_injected_http_session_for_endpoint_calls(self):
        session = RecordingHttpSession()
        client = OppoControlApiClient(
            player_host="192.168.1.50",
            http_session=session,
        )

        response = client.get_playing_time()

        self.assertTrue(response.is_successful)
        self.assertEqual(
            "http://192.168.1.50:436/getplayingtime",
            session.calls[0]["url"],
        )

    def test_with_http_session_returns_copy_with_injected_session(self):
        session = RecordingHttpSession()
        client = OppoControlApiClient(player_host="192.168.1.50")

        copied = client.with_http_session(session)

        self.assertIsNot(client, copied)
        self.assertIs(session, copied.http_session)


class RecordingHttpSession:
    def __init__(self):
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append({"url": url, "kwargs": kwargs})
        return type(
            "Response",
            (),
            {
                "status_code": 200,
                "text": '{"success":true}',
            },
        )()


if __name__ == "__main__":
    unittest.main()
