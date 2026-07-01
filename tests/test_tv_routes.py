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
