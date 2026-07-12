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


class AvSourcesRouteTest(unittest.TestCase):
    @patch("home_cinema_control.web.av_routes.list_av_hdmi_inputs")
    def test_av_sources_saves_and_returns_detected_inputs(self, mock_sources):
        from home_cinema_control.config.models import AvInputSource
        mock_sources.return_value = [
            AvInputSource(id=1, name="BD", param="SIBD\n"),
        ]
        client, _, config_service = _make_client(config={"av": {"enabled": True, "model": "Denon"}})

        resp = client.get("/api/v1/av/sources")

        self.assertEqual(200, resp.status_code)
        inputs = resp.json()["av"]["available_hdmi_inputs"]
        self.assertEqual(1, len(inputs))
        self.assertEqual("BD", inputs[0]["name"])
        self.assertEqual("SIBD\n", inputs[0]["param"])
        config_service.save_config.assert_called_once()

    @patch("home_cinema_control.web.av_routes.list_av_hdmi_inputs")
    def test_av_sources_post_uses_submitted_config(self, mock_sources):
        from home_cinema_control.config.models import AvInputSource
        mock_sources.return_value = [
            AvInputSource(id=2, name="Source/profile 2", param="profile 2\n"),
        ]
        client, _, config_service = _make_client(
            config={"av": {"enabled": True, "model": "DENON", "ip": "192.168.1.20"}}
        )
        submitted = {"av": {"enabled": True, "model": "TRINNOV", "ip": "192.168.1.50"}}

        resp = client.post("/api/v1/av/sources", json=submitted)

        self.assertEqual(200, resp.status_code)
        mock_sources.assert_called_once()
        detected_config = mock_sources.call_args.args[0]
        self.assertEqual("TRINNOV", detected_config["av"]["model"])
        self.assertEqual("192.168.1.50", detected_config["av"]["ip"])
        self.assertEqual("TRINNOV", resp.json()["av"]["model"])
        self.assertEqual("profile 2\n", resp.json()["av"]["available_hdmi_inputs"][0]["param"])
        config_service.save_config.assert_called_once()
        saved_config = config_service.save_config.call_args.args[0]
        self.assertEqual("profile 2\n", saved_config["av"]["available_hdmi_inputs"][0]["param"])


if __name__ == "__main__":
    unittest.main()
