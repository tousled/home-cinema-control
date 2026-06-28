import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from home_cinema_control.web.api_app import create_api_app
from home_cinema_control.web.api_runtime import WebApiRuntime


class FakeTelemetryClient:
    def send(self, base_url, ingest_key, payloads):
        return True


def _config(enabled=False, installation_id=""):
    return {
        "Version": "1.2.3",
        "app": {"language": "es-ES"},
        "telemetry": {
            "enabled": enabled,
            "installation_id": installation_id,
            "endpoint_url": "https://telemetry.example",
            "ingest_key": "test-ingest-key",
        },
        "media_servers": {
            "active": "emby",
            "providers": {
                "emby": {
                    "server_url": "http://emby.local",
                    "access_token": "secret",
                }
            },
        },
        "oppo": {"ip": "192.168.1.50"},
    }


def _make_client(initial_config):
    temp_dir = tempfile.TemporaryDirectory()
    state = {"config": initial_config, "temp_dir": temp_dir}

    runtime = MagicMock()
    config_service = MagicMock()
    config_service.load_config.side_effect = lambda: state["config"]
    config_service.save_config.side_effect = lambda config: state.update(config=config)

    api_runtime = WebApiRuntime(
        runtime=runtime,
        config_service=config_service,
        config_file=Path(temp_dir.name) / "config.json",
        log_file=Path(temp_dir.name) / "emby_xnoppo_client_logging.log",
        frontend_dist_dir=Path("/tmp/frontend/dist"),
    )
    return TestClient(create_api_app(api_runtime)), state, config_service


@patch("home_cinema_control.telemetry.service.TelemetryClient")
def test_get_telemetry_status_returns_safe_shape(client_class):
    client_class.return_value = FakeTelemetryClient()
    client, _, _ = _make_client(_config(enabled=False))

    resp = client.get("/api/v1/telemetry")

    assert resp.status_code == 200
    data = resp.json()
    assert data["enabled"] is False
    assert data["installation_id_configured"] is False
    assert data["ingest_key_configured"] is True
    assert data["consent_prompted"] is False
    assert data["endpoint_url"] == "https://telemetry.example"
    assert data["schema_version"] == 1
    assert data["queue_count"] == 0


@patch("home_cinema_control.telemetry.service.TelemetryClient")
def test_enable_telemetry_saves_enabled_config(client_class):
    client_class.return_value = FakeTelemetryClient()
    client, state, config_service = _make_client(_config(enabled=False))

    resp = client.post("/api/v1/telemetry/enable")

    assert resp.status_code == 200
    assert resp.json()["enabled"] is True
    assert resp.json()["installation_id_configured"] is True
    assert state["config"]["telemetry"]["enabled"] is True
    assert state["config"]["telemetry"]["installation_id"]
    config_service.save_config.assert_called()


@patch("home_cinema_control.telemetry.service.TelemetryClient")
def test_disable_telemetry_can_reset_identity(client_class):
    client_class.return_value = FakeTelemetryClient()
    client, state, _ = _make_client(
        _config(
            enabled=True,
            installation_id="11111111-1111-4111-8111-111111111111",
        )
    )

    resp = client.post("/api/v1/telemetry/disable", json={"reset_identity": True})

    assert resp.status_code == 200
    assert resp.json()["enabled"] is False
    assert resp.json()["installation_id_configured"] is False
    assert state["config"]["telemetry"]["installation_id"] == ""


@patch("home_cinema_control.telemetry.service.TelemetryClient")
def test_roadmap_interest_accepts_allowlisted_values(client_class):
    client_class.return_value = FakeTelemetryClient()
    client, _, _ = _make_client(
        _config(
            enabled=True,
            installation_id="11111111-1111-4111-8111-111111111111",
        )
    )

    resp = client.post(
        "/api/v1/telemetry/roadmap-interest",
        json={"interests": ["plex", "home_assistant"]},
    )

    assert resp.status_code == 200


@patch("home_cinema_control.telemetry.service.TelemetryClient")
def test_roadmap_interest_rejects_unknown_values(client_class):
    client_class.return_value = FakeTelemetryClient()
    client, _, _ = _make_client(
        _config(
            enabled=True,
            installation_id="11111111-1111-4111-8111-111111111111",
        )
    )

    resp = client.post(
        "/api/v1/telemetry/roadmap-interest",
        json={"interests": ["plex", "/private/path"]},
    )

    assert resp.status_code == 422
