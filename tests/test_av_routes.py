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


if __name__ == "__main__":
    unittest.main()
