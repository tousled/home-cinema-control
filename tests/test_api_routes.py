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
    config_service.with_app_updates.side_effect = (
        lambda current_config, **updates: {
            **current_config,
            "app": {**(current_config.get("app") or {}), **updates},
        }
    )

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
            "media_servers": {
                "active": "emby",
                "providers": {
                    "emby": {"access_token_configured": True, "server_url": "http://emby"}
                },
            },
            "media_player": {"oppo": {"ip": "192.168.1.10"}},
        })

        resp = client.get("/api/v1/config/readiness")

        self.assertEqual(200, resp.status_code)
        data = resp.json()
        for key in ("media_server", "media_player", "media_paths", "tv", "av"):
            self.assertIn(key, data, f"missing key: {key}")
            self.assertIn("status", data[key])

    def test_returns_incomplete_when_server_not_configured(self):
        client, _, _ = _make_client()

        resp = client.get("/api/v1/config/readiness")

        self.assertEqual(200, resp.status_code)
        self.assertEqual("incomplete", resp.json()["media_server"]["status"])

    def test_returns_configured_when_server_and_player_are_set(self):
        client, _, _ = _make_client(config={
            "media_servers": {
                "active": "emby",
                "providers": {
                    "emby": {"access_token_configured": True, "server_url": "http://emby"}
                },
            },
            "oppo": {"ip": "192.168.1.10"},
        })

        resp = client.get("/api/v1/config/readiness")

        self.assertEqual("configured", resp.json()["media_server"]["status"])
        self.assertEqual("configured", resp.json()["media_player"]["status"])


class ConfigSectionRouteTest(unittest.TestCase):
    def test_full_config_post_is_not_supported(self):
        client, _, _ = _make_client()

        resp = client.post("/api/v1/config", json={"app": {"language": "es-ES"}})

        self.assertEqual(405, resp.status_code)

    def test_patch_config_section_saves_section_over_latest_config(self):
        client, _, config_service = _make_client(config={
            "oppo": {"ip": "192.168.1.10", "always_on": True},
            "tv": {"enabled": True, "model": "LG"},
        })

        resp = client.patch("/api/v1/config/oppo", json={"ip": "192.168.1.11"})

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

        resp = client.patch("/api/v1/config/network-access", json={
            "smb": {"username": "nas", "password": ""},
            "oppo": {"pre_mount_smb": True},
        })

        self.assertEqual(200, resp.status_code)
        saved = config_service.save_config.call_args.args[0]
        self.assertEqual("stored-secret", saved["smb"]["password"])
        self.assertTrue(saved["oppo"]["pre_mount_smb"])

    def test_patch_unknown_config_section_returns_404(self):
        client, _, _ = _make_client()

        resp = client.patch("/api/v1/config/unknown", json={})

        self.assertEqual(404, resp.status_code)


class MigrationImportLegacyRouteTest(unittest.TestCase):
    @patch("home_cinema_control.web.api_app.import_legacy_config")
    def test_returns_ok_on_successful_import(self, mock_import):
        client, _, _ = _make_client()

        resp = client.post("/api/v1/migration/import-legacy", json={"emby_server": "http://emby.local"})

        self.assertEqual(200, resp.status_code)
        self.assertEqual({"ok": True}, resp.json())
        mock_import.assert_called_once()

    @patch("home_cinema_control.web.api_app.import_legacy_config")
    def test_returns_400_when_payload_is_not_a_legacy_config(self, mock_import):
        mock_import.side_effect = ValueError("Not a recognizable legacy config")
        client, _, _ = _make_client()

        resp = client.post("/api/v1/migration/import-legacy", json={"unrelated": "json"})

        self.assertEqual(400, resp.status_code)

    @patch("home_cinema_control.web.api_app.import_legacy_config")
    def test_returns_500_on_unexpected_failure(self, mock_import):
        mock_import.side_effect = RuntimeError("disk full")
        client, _, _ = _make_client()

        resp = client.post("/api/v1/migration/import-legacy", json={"emby_server": "http://emby.local"})

        self.assertEqual(500, resp.status_code)


class SaveConfigSectionLoggingTest(unittest.TestCase):
    @patch("home_cinema_control.web.api_app.configure_logging")
    def test_reapplies_logging_live_when_app_section_saved(self, mock_configure):
        client, _runtime, _config_service = _make_client(config={"app": {"log_level": 0}})

        resp = client.patch("/api/v1/config/app", json={"log_level": 2})

        self.assertEqual(200, resp.status_code)
        mock_configure.assert_called_once()
        saved_config = mock_configure.call_args.args[0]
        self.assertEqual(2, saved_config["app"]["log_level"])

    @patch("home_cinema_control.web.api_app.configure_logging")
    def test_does_not_reapply_logging_for_other_sections(self, mock_configure):
        client, _runtime, _config_service = _make_client(config={"oppo": {"ip": ""}})

        resp = client.patch("/api/v1/config/oppo", json={"ip": "192.168.50.35"})

        self.assertEqual(200, resp.status_code)
        mock_configure.assert_not_called()


if __name__ == "__main__":
    unittest.main()
