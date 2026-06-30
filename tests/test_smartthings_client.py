import unittest
from unittest.mock import Mock, patch

from home_cinema_control.devices.tv.adapters.smartthings_client import (
    SMARTTHINGS_API_BASE,
    SMARTTHINGS_DEVICES_URL,
    SMARTTHINGS_REQUEST_TIMEOUT,
    SmartThingsInputClient,
    _MEDIA_INPUT_CAPABILITY,
)

TOKEN = "test-bearer-token"
DEVICE_ID = "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"


def _client() -> SmartThingsInputClient:
    return SmartThingsInputClient(token_provider=lambda: TOKEN, device_id=DEVICE_ID)


def _ok_response() -> Mock:
    resp = Mock(status_code=200)
    resp.raise_for_status = Mock()
    return resp


class SmartThingsInputClientSetInputTest(unittest.TestCase):
    def _call_set_input(self, input_id: str = "HDMI2"):
        mock_resp = _ok_response()
        with patch(
            "home_cinema_control.devices.tv.adapters.smartthings_client.requests.post"
        ) as mock_post:
            mock_post.return_value = mock_resp
            _client().set_input(input_id)
        return mock_post

    def test_posts_to_commands_endpoint(self):
        mock_post = self._call_set_input()
        url = mock_post.call_args.args[0]
        self.assertIn(DEVICE_ID, url)
        self.assertTrue(url.endswith("/commands"))
        self.assertIn(SMARTTHINGS_API_BASE, url)

    def test_sends_bearer_auth_header(self):
        mock_post = self._call_set_input()
        headers = mock_post.call_args.kwargs["headers"]
        self.assertEqual(f"Bearer {TOKEN}", headers["Authorization"])

    def test_sends_correct_capability_and_command(self):
        mock_post = self._call_set_input("HDMI3")
        payload = mock_post.call_args.kwargs["json"]
        cmd = payload["commands"][0]
        self.assertEqual("main", cmd["component"])
        self.assertEqual("mediaInputSource", cmd["capability"])
        self.assertEqual("setInputSource", cmd["command"])
        self.assertEqual(["HDMI3"], cmd["arguments"])

    def test_passes_correct_timeout(self):
        mock_post = self._call_set_input()
        self.assertEqual(SMARTTHINGS_REQUEST_TIMEOUT, mock_post.call_args.kwargs["timeout"])

    def test_calls_raise_for_status(self):
        mock_resp = _ok_response()
        with patch(
            "home_cinema_control.devices.tv.adapters.smartthings_client.requests.post",
            return_value=mock_resp,
        ):
            _client().set_input("HDMI1")
        mock_resp.raise_for_status.assert_called_once()

    def test_propagates_http_error(self):
        import requests as req_lib
        mock_resp = Mock()
        mock_resp.raise_for_status.side_effect = req_lib.exceptions.HTTPError("403 Forbidden")
        with patch(
            "home_cinema_control.devices.tv.adapters.smartthings_client.requests.post",
            return_value=mock_resp,
        ):
            with self.assertRaises(req_lib.exceptions.HTTPError):
                _client().set_input("HDMI1")

    def test_propagates_connection_error(self):
        import requests as req_lib
        with patch(
            "home_cinema_control.devices.tv.adapters.smartthings_client.requests.post",
            side_effect=req_lib.exceptions.ConnectionError("unreachable"),
        ):
            with self.assertRaises(req_lib.exceptions.ConnectionError):
                _client().set_input("HDMI1")


class SmartThingsInputClientGetSupportedInputsTest(unittest.TestCase):
    def _call_get_inputs(self, sources: list[str]) -> tuple[Mock, list[str]]:
        mock_resp = _ok_response()
        mock_resp.json.return_value = {
            "supportedInputSources": {"value": sources}
        }
        with patch(
            "home_cinema_control.devices.tv.adapters.smartthings_client.requests.get"
        ) as mock_get:
            mock_get.return_value = mock_resp
            result = _client().get_supported_inputs()
        return mock_get, result

    def test_gets_from_status_endpoint(self):
        mock_get, _ = self._call_get_inputs(["HDMI1"])
        url = mock_get.call_args.args[0]
        self.assertIn(DEVICE_ID, url)
        self.assertIn("mediaInputSource/status", url)

    def test_sends_bearer_auth_header(self):
        mock_get, _ = self._call_get_inputs(["HDMI1"])
        headers = mock_get.call_args.kwargs["headers"]
        self.assertEqual(f"Bearer {TOKEN}", headers["Authorization"])

    def test_returns_list_of_input_ids(self):
        _, result = self._call_get_inputs(["HDMI1", "HDMI2", "digitalTv"])
        self.assertEqual(["HDMI1", "HDMI2", "digitalTv"], result)

    def test_returns_empty_list_when_no_sources(self):
        mock_resp = _ok_response()
        mock_resp.json.return_value = {}
        with patch(
            "home_cinema_control.devices.tv.adapters.smartthings_client.requests.get",
            return_value=mock_resp,
        ):
            result = _client().get_supported_inputs()
        self.assertEqual([], result)

    def test_passes_correct_timeout(self):
        mock_get, _ = self._call_get_inputs([])
        self.assertEqual(SMARTTHINGS_REQUEST_TIMEOUT, mock_get.call_args.kwargs["timeout"])

    def test_propagates_http_error(self):
        import requests as req_lib
        mock_resp = Mock()
        mock_resp.raise_for_status.side_effect = req_lib.exceptions.HTTPError("401 Unauthorized")
        with patch(
            "home_cinema_control.devices.tv.adapters.smartthings_client.requests.get",
            return_value=mock_resp,
        ):
            with self.assertRaises(req_lib.exceptions.HTTPError):
                _client().get_supported_inputs()


class SmartThingsInputClientListDevicesTest(unittest.TestCase):
    def _call_list_devices(self, items: list[dict]) -> tuple[Mock, list[dict]]:
        mock_resp = _ok_response()
        mock_resp.json.return_value = {"items": items}
        with patch(
            "home_cinema_control.devices.tv.adapters.smartthings_client.requests.get"
        ) as mock_get:
            mock_get.return_value = mock_resp
            result = _client().list_devices()
        return mock_get, result

    def test_gets_from_devices_url(self):
        mock_get, _ = self._call_list_devices([])
        self.assertEqual(SMARTTHINGS_DEVICES_URL, mock_get.call_args.args[0])

    def test_sends_capability_filter(self):
        mock_get, _ = self._call_list_devices([])
        params = mock_get.call_args.kwargs["params"]
        self.assertEqual(_MEDIA_INPUT_CAPABILITY, params["capability"])

    def test_sends_bearer_auth_header(self):
        mock_get, _ = self._call_list_devices([])
        headers = mock_get.call_args.kwargs["headers"]
        self.assertEqual(f"Bearer {TOKEN}", headers["Authorization"])

    def test_returns_id_and_label(self):
        _, result = self._call_list_devices([
            {"deviceId": "aaa", "label": "Samsung QN90B"},
        ])
        self.assertEqual([{"id": "aaa", "label": "Samsung QN90B"}], result)

    def test_falls_back_to_name_when_label_absent(self):
        _, result = self._call_list_devices([
            {"deviceId": "bbb", "name": "Samsung TV"},
        ])
        self.assertEqual([{"id": "bbb", "label": "Samsung TV"}], result)

    def test_returns_sorted_by_label(self):
        _, result = self._call_list_devices([
            {"deviceId": "z", "label": "Zed TV"},
            {"deviceId": "a", "label": "Alpha TV"},
        ])
        self.assertEqual(["Alpha TV", "Zed TV"], [d["label"] for d in result])

    def test_returns_empty_when_no_items(self):
        mock_resp = _ok_response()
        mock_resp.json.return_value = {}
        with patch(
            "home_cinema_control.devices.tv.adapters.smartthings_client.requests.get",
            return_value=mock_resp,
        ):
            result = _client().list_devices()
        self.assertEqual([], result)

    def test_propagates_http_error_on_401(self):
        import requests as req_lib
        mock_resp = Mock()
        mock_resp.raise_for_status.side_effect = req_lib.exceptions.HTTPError("401 Unauthorized")
        with patch(
            "home_cinema_control.devices.tv.adapters.smartthings_client.requests.get",
            return_value=mock_resp,
        ):
            with self.assertRaises(req_lib.exceptions.HTTPError):
                _client().list_devices()

    def test_passes_correct_timeout(self):
        mock_get, _ = self._call_list_devices([])
        self.assertEqual(SMARTTHINGS_REQUEST_TIMEOUT, mock_get.call_args.kwargs["timeout"])


if __name__ == "__main__":
    unittest.main()
