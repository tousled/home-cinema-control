import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from home_cinema_control.web.api_app import create_api_app
from home_cinema_control.web.api_runtime import WebApiRuntime


def _make_client(*, config=None, sanitized=None):
    config = config or {}
    sanitized = sanitized or config

    runtime = MagicMock()
    runtime.has_active_playback.return_value = False
    config_service = MagicMock()
    config_service.load_config.return_value = config
    config_service.sanitize.side_effect = lambda x: x
    config_service.prepare_submitted_config.side_effect = lambda x: x

    api_runtime = WebApiRuntime(
        runtime=runtime,
        config_service=config_service,
        config_file=Path("/tmp/config.json"),
        log_file=Path("/tmp/emby_xnoppo_client_logging.log"),
        frontend_dist_dir=Path("/tmp/frontend/dist"),
    )
    return TestClient(create_api_app(api_runtime)), runtime, config_service


_ST_STORE = "home_cinema_control.devices.tv.adapters.smartthings_oauth.SmartThingsTokenStore"
_ST_OAUTH = "home_cinema_control.devices.tv.adapters.smartthings_oauth.SmartThingsOAuthClient"
_ST_DEVICES_CLIENT = "home_cinema_control.devices.tv.adapters.smartthings_client.make_smartthings_devices_client"
_CONFIG_PATH = "home_cinema_control.config.manager.get_config_path"
_SECRETS_PATH = "home_cinema_control.config.manager.get_secrets_path"


def _make_st_store(*, connected: bool):
    store = MagicMock()
    if connected:
        st = MagicMock()
        st.refresh_token = "rt"
        st.client_id = "cid"
        st.client_secret = "cs"
        store.load.return_value = st
    else:
        store.load.return_value = None
    return store


class SamsungOauthDevicesRouteTest(unittest.TestCase):
    def _devices_call(self, *, connected=True, devices=None, http_status=None):
        import requests as req_lib
        client, runtime, _ = _make_client()
        store = _make_st_store(connected=connected)
        mock_st_client = MagicMock()
        if http_status is not None:
            err_resp = MagicMock()
            err_resp.status_code = http_status
            mock_st_client.list_devices.side_effect = req_lib.exceptions.HTTPError(
                response=err_resp
            )
        else:
            mock_st_client.list_devices.return_value = devices if devices is not None else []

        patches = [
            patch(_CONFIG_PATH, return_value="/tmp/c.json"),
            patch(_SECRETS_PATH, return_value="/tmp/s.json"),
            patch(_ST_STORE, return_value=store),
            patch(_ST_OAUTH),
            patch(_ST_DEVICES_CLIENT, return_value=mock_st_client),
        ]
        with patches[0], patches[1], patches[2], patches[3], patches[4]:
            resp = client.get("/api/v1/tv/samsung/oauth/devices")
        return resp, runtime

    def test_returns_400_no_diagnostic_when_not_connected(self):
        client, runtime, _ = _make_client()
        store = _make_st_store(connected=False)
        with (
            patch(_CONFIG_PATH, return_value="/tmp/c.json"),
            patch(_SECRETS_PATH, return_value="/tmp/s.json"),
            patch(_ST_STORE, return_value=store),
        ):
            resp = client.get("/api/v1/tv/samsung/oauth/devices")
        self.assertEqual(400, resp.status_code)
        runtime.set_last_diagnostic.assert_not_called()

    def test_returns_401_and_writes_diagnostic_on_token_rejected(self):
        resp, runtime = self._devices_call(http_status=401)
        self.assertEqual(401, resp.status_code)
        runtime.set_last_diagnostic.assert_called_once()
        self.assertEqual("SMARTTHINGS_TOKEN_REJECTED",
                         runtime.set_last_diagnostic.call_args[0][0].code)

    def test_returns_401_and_writes_diagnostic_on_403(self):
        resp, runtime = self._devices_call(http_status=403)
        self.assertEqual(401, resp.status_code)
        runtime.set_last_diagnostic.assert_called_once()
        self.assertEqual("SMARTTHINGS_TOKEN_REJECTED",
                         runtime.set_last_diagnostic.call_args[0][0].code)

    def test_returns_devices_and_no_diagnostic(self):
        devices = [{"id": "abc", "label": "Samsung QN90B"}]
        resp, runtime = self._devices_call(devices=devices)
        self.assertEqual(200, resp.status_code)
        self.assertEqual(devices, resp.json())
        runtime.set_last_diagnostic.assert_not_called()

    def test_writes_no_devices_diagnostic_on_empty_list(self):
        resp, runtime = self._devices_call(devices=[])
        self.assertEqual(200, resp.status_code)
        self.assertEqual([], resp.json())
        runtime.set_last_diagnostic.assert_called_once()
        self.assertEqual("SMARTTHINGS_NO_DEVICES",
                         runtime.set_last_diagnostic.call_args[0][0].code)


class TvSourcesRouteTest(unittest.TestCase):
    @patch("home_cinema_control.web.tv_routes.detect_tv_sources")
    def test_tv_sources_returns_detected_config_without_saving(self, mock_sources):
        def _mutate(config):
            config.setdefault("tv", {})["available_hdmi_inputs"] = [{"id": "HDMI_1"}]
            return "OK"

        mock_sources.side_effect = _mutate
        client, _, config_service = _make_client()

        resp = client.post("/api/v1/tv/sources", json={"tv": {"enabled": True, "model": "LG"}})

        self.assertEqual(200, resp.status_code)
        self.assertEqual([{"id": "HDMI_1"}], resp.json()["tv"]["available_hdmi_inputs"])
        config_service.save_config.assert_not_called()


if __name__ == "__main__":
    unittest.main()
