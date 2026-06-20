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


class ConfigReadinessRouteTest(unittest.TestCase):
    def test_returns_readiness_payload_shape(self):
        client, _, _ = _make_client(config={
            "media_server": {"access_token_configured": True, "server_url": "http://emby"},
            "media_player": {"oppo": {"ip": "192.168.1.10"}},
        })

        resp = client.get("/api/config/readiness")

        self.assertEqual(200, resp.status_code)
        data = resp.json()
        for key in ("media_server", "media_player", "media_paths", "tv", "av"):
            self.assertIn(key, data, f"missing key: {key}")
            self.assertIn("status", data[key])

    def test_returns_incomplete_when_server_not_configured(self):
        client, _, _ = _make_client()

        resp = client.get("/api/config/readiness")

        self.assertEqual(200, resp.status_code)
        self.assertEqual("incomplete", resp.json()["media_server"]["status"])

    def test_returns_configured_when_server_and_player_are_set(self):
        client, _, _ = _make_client(config={
            "media_server": {"access_token_configured": True, "server_url": "http://emby"},
            "oppo": {"ip": "192.168.1.10"},
        })

        resp = client.get("/api/config/readiness")

        self.assertEqual("configured", resp.json()["media_server"]["status"])
        self.assertEqual("configured", resp.json()["media_player"]["status"])


class ConfigSectionRouteTest(unittest.TestCase):
    def test_full_config_post_is_not_supported(self):
        client, _, _ = _make_client()

        resp = client.post("/api/config", json={"app": {"language": "es-ES"}})

        self.assertEqual(405, resp.status_code)

    def test_patch_config_section_saves_section_over_latest_config(self):
        client, _, config_service = _make_client(config={
            "oppo": {"ip": "192.168.1.10", "always_on": True},
            "tv": {"enabled": True, "model": "LG"},
        })

        resp = client.patch("/api/config/oppo", json={"ip": "192.168.1.11"})

        self.assertEqual(200, resp.status_code)
        saved = config_service.save_config.call_args.args[0]
        self.assertEqual("192.168.1.11", saved["oppo"]["ip"])
        self.assertTrue(saved["oppo"]["always_on"])
        self.assertEqual({"enabled": True, "model": "LG"}, saved["tv"])

    def test_patch_config_section_merges_existing_secrets_before_saving(self):
        client, _, config_service = _make_client(config={
            "smb": {"username": "nas", "password": "stored-secret"},
            "oppo": {"pre_mount_smb": False},
        })

        def _prepare(config):
            config["smb"]["password"] = "stored-secret"
            return config

        config_service.prepare_submitted_config.side_effect = _prepare

        resp = client.patch("/api/config/network-access", json={
            "smb": {"username": "nas", "password": ""},
            "oppo": {"pre_mount_smb": True},
        })

        self.assertEqual(200, resp.status_code)
        saved = config_service.save_config.call_args.args[0]
        self.assertEqual("stored-secret", saved["smb"]["password"])
        self.assertTrue(saved["oppo"]["pre_mount_smb"])

    def test_patch_media_server_section_without_provider_change_keeps_auth(self):
        client, _, config_service = _make_client(config={
            "media_server": {"type": "emby", "server_url": "http://old", "display_name": "Pedro"},
        })

        resp = client.patch("/api/config/media-server", json={
            "media_server": {"type": "emby", "server_url": "http://new"},
        })

        self.assertEqual(200, resp.status_code)
        config_service.clear_media_server_auth.assert_not_called()
        saved = config_service.save_config.call_args.args[0]
        self.assertEqual("http://new", saved["media_server"]["server_url"])

    def test_patch_media_server_section_with_provider_change_clears_auth(self):
        client, _, config_service = _make_client(config={
            "media_server": {"type": "emby", "server_url": "http://old", "display_name": "Pedro"},
            "playback": {"hcc_controlled_device": "emby-device"},
        })

        resp = client.patch("/api/config/media-server", json={
            "media_server": {"type": "jellyfin", "server_url": "http://jellyfin.local"},
        })

        self.assertEqual(200, resp.status_code)
        config_service.clear_media_server_auth.assert_called_once()
        saved = config_service.save_config.call_args.args[0]
        self.assertEqual("jellyfin", saved["media_server"]["type"])
        self.assertEqual("http://jellyfin.local", saved["media_server"]["server_url"])

    def test_patch_unknown_config_section_returns_404(self):
        client, _, _ = _make_client()

        resp = client.patch("/api/config/unknown", json={})

        self.assertEqual(404, resp.status_code)


class PathsTestRouteTest(unittest.TestCase):
    @patch("home_cinema_control.web.api_app.check_path_configuration")
    def test_returns_body_on_success(self, mock_check):
        mock_check.return_value = "OK"
        client, _, _ = _make_client()
        body = {"source_path": "/vol/Movies", "player_path": "/NAS/vol/Movies"}

        resp = client.post("/api/paths/test", json=body)

        self.assertEqual(200, resp.status_code)
        self.assertEqual(body, resp.json())

    @patch("home_cinema_control.web.api_app.check_path_configuration")
    def test_returns_400_with_diagnostic_on_failure(self, mock_check):
        mock_check.return_value = "OPPO_UNAVAILABLE: OPPO socket is not reachable"
        client, runtime, _ = _make_client()

        resp = client.post("/api/paths/test", json={"source_path": "/vol", "player_path": "/NAS/vol"})

        self.assertEqual(400, resp.status_code)
        data = resp.json()
        self.assertIn("detail", data)
        self.assertIn("diagnostic", data)
        self.assertIn("code", data["diagnostic"])
        self.assertIn("suggestion", data["diagnostic"])
        runtime.set_last_diagnostic.assert_called_once()

    @patch("home_cinema_control.web.api_app.check_path_configuration")
    def test_diagnostic_code_identifies_oppo_failure(self, mock_check):
        mock_check.return_value = "OPPO_UNAVAILABLE: OPPO socket is not reachable"
        client, _, _ = _make_client()

        resp = client.post("/api/paths/test", json={"source_path": "/vol", "player_path": "/NAS/vol"})

        self.assertIn("OPPO", resp.json()["diagnostic"]["code"])


class PathsPreviewRouteTest(unittest.TestCase):
    def test_returns_preview_for_valid_mapping(self):
        client, _, _ = _make_client()
        body = {
            "source_path": "/volume1/Video/Movies",
            "player_path": "/192.168.1.10/volume1/Video/Movies",
            "sample_file": "/volume1/Video/Movies/film.mkv",
        }

        resp = client.post("/api/paths/preview", json=body)

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

        resp = client.post("/api/paths/preview", json=body)

        self.assertEqual(400, resp.status_code)

    def test_returns_400_for_missing_source_path(self):
        client, _, _ = _make_client()

        resp = client.post("/api/paths/preview", json={"source_path": "", "player_path": "/NAS/vol"})

        self.assertEqual(400, resp.status_code)


class LibraryPathsRouteTest(unittest.TestCase):
    @patch("home_cinema_control.media_servers.emby.web_config.fetch_library_paths")
    def test_returns_library_paths_on_success(self, mock_fetch):
        mock_fetch.return_value = ["/volume1/Video/Movies", "/volume1/Video/Series"]
        client, _, _ = _make_client()

        resp = client.get("/api/media-server/library-paths")

        self.assertEqual(200, resp.status_code)
        self.assertEqual(["/volume1/Video/Movies", "/volume1/Video/Series"], resp.json())
        # The setup-service boundary receives the raw config dict (with secrets and
        # arbitrary keys), not a pruned Pydantic model. Guards the candidate-1 regression.
        mock_fetch.assert_called_once()
        self.assertIsInstance(mock_fetch.call_args.args[0], dict)

    @patch("home_cinema_control.media_servers.emby.web_config.fetch_library_paths")
    def test_returns_502_when_emby_unreachable(self, mock_fetch):
        mock_fetch.side_effect = Exception("Connection refused")
        client, runtime, _ = _make_client()

        resp = client.get("/api/media-server/library-paths")

        self.assertEqual(502, resp.status_code)
        runtime.set_last_diagnostic.assert_called_once()


class DeviceSetupActionRouteTest(unittest.TestCase):
    @patch("home_cinema_control.web.api_app.detect_tv_sources")
    def test_tv_sources_returns_detected_config_without_saving(self, mock_sources):
        def _mutate(config):
            config.setdefault("tv", {})["available_hdmi_inputs"] = [{"id": "HDMI_1"}]
            return "OK"

        mock_sources.side_effect = _mutate
        client, _, config_service = _make_client()

        resp = client.post("/api/tv/sources", json={"tv": {"enabled": True, "model": "LG"}})

        self.assertEqual(200, resp.status_code)
        self.assertEqual([{"id": "HDMI_1"}], resp.json()["tv"]["available_hdmi_inputs"])
        config_service.save_config.assert_not_called()

    @patch("home_cinema_control.web.api_app.list_av_hdmi_inputs")
    def test_av_sources_returns_detected_config_without_saving(self, mock_sources):
        mock_sources.return_value = [{"Name": "Blu-ray", "Param": "BD"}]
        client, _, config_service = _make_client()

        resp = client.post("/api/av/sources", json={"av": {"enabled": True, "model": "Denon"}})

        self.assertEqual(200, resp.status_code)
        self.assertEqual([{"Name": "Blu-ray", "Param": "BD"}], resp.json()["av"]["available_hdmi_inputs"])
        config_service.save_config.assert_not_called()


class OppoAdvancedDefaultsRouteTest(unittest.TestCase):
    def test_returns_pydantic_model_defaults(self):
        client, _, _ = _make_client()

        resp = client.get("/api/oppo/advanced-defaults")

        self.assertEqual(200, resp.status_code)
        self.assertEqual(
            {
                "connection_timeout_seconds": 10.0,
                "playback_start_timeout_seconds": 30.0,
                "nfs_mount_timeout_seconds": 30.0,
                "autoscript": False,
            },
            resp.json(),
        )


if __name__ == "__main__":
    unittest.main()
