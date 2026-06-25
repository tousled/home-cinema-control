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


class PathsTestRouteTest(unittest.TestCase):
    @patch("home_cinema_control.web.paths_routes.check_path_configuration")
    def test_returns_body_on_success(self, mock_check):
        mock_check.return_value = "OK"
        client, _, _ = _make_client()
        body = {"source_path": "/vol/Movies", "player_path": "/NAS/vol/Movies"}

        resp = client.post("/api/v1/paths/test", json=body)

        self.assertEqual(200, resp.status_code)
        self.assertEqual(body, resp.json())

    @patch("home_cinema_control.web.paths_routes.check_path_configuration")
    def test_returns_400_with_diagnostic_on_failure(self, mock_check):
        mock_check.return_value = "OPPO_UNAVAILABLE: OPPO socket is not reachable"
        client, runtime, _ = _make_client()

        resp = client.post("/api/v1/paths/test", json={"source_path": "/vol", "player_path": "/NAS/vol"})

        self.assertEqual(400, resp.status_code)
        data = resp.json()
        self.assertIn("detail", data)
        self.assertIn("diagnostic", data)
        self.assertIn("code", data["diagnostic"])
        self.assertIn("suggestion", data["diagnostic"])
        runtime.set_last_diagnostic.assert_called_once()

    @patch("home_cinema_control.web.paths_routes.check_path_configuration")
    def test_diagnostic_code_identifies_oppo_failure(self, mock_check):
        mock_check.return_value = "OPPO_UNAVAILABLE: OPPO socket is not reachable"
        client, _, _ = _make_client()

        resp = client.post("/api/v1/paths/test", json={"source_path": "/vol", "player_path": "/NAS/vol"})

        self.assertIn("OPPO", resp.json()["diagnostic"]["code"])


class PathsPreviewRouteTest(unittest.TestCase):
    def test_returns_preview_for_valid_mapping(self):
        client, _, _ = _make_client()
        body = {
            "source_path": "/volume1/Video/Movies",
            "player_path": "/192.168.1.10/volume1/Video/Movies",
            "sample_file": "/volume1/Video/Movies/film.mkv",
        }

        resp = client.post("/api/v1/paths/preview", json=body)

        self.assertEqual(200, resp.status_code)
        data = resp.json()
        self.assertIn("server", data)
        self.assertIn("folder", data)
        self.assertEqual("192.168.1.10", data["server"])

    def test_returns_400_for_invalid_player_path(self):
        client, _, _ = _make_client()
        body = {
            "source_path": "/volume1/Video",
            "player_path": "/NAS",
            "sample_file": "/volume1/Video/film.mkv",
        }

        resp = client.post("/api/v1/paths/preview", json=body)

        self.assertEqual(400, resp.status_code)

    def test_returns_400_for_missing_source_path(self):
        client, _, _ = _make_client()

        resp = client.post("/api/v1/paths/preview", json={"source_path": "", "player_path": "/NAS/vol"})

        self.assertEqual(400, resp.status_code)


if __name__ == "__main__":
    unittest.main()
