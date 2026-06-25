import copy
import json
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from home_cinema_control.web.api_app import create_api_app
from home_cinema_control.web.config_service import WebConfigService
from home_cinema_control.web.api_runtime import WebApiRuntime


pytestmark = pytest.mark.integration


def test_section_save_preserves_smb_secret_through_real_api_service(tmp_path, monkeypatch):
    client, runtime = _client(tmp_path, monkeypatch, config={
        "oppo": {
            "ip": "192.168.1.10",
            "always_on": True,
            "pre_mount_smb": False,
        },
        "smb": {"username": "nas-user"},
        "media_servers": {
            "active": "emby",
            "providers": {
                "emby": {
                    "playback": {
                        "path_mappings": [
                            {
                                "source_path": "/volume1/Video/Trailers",
                                "player_path": "/NAS-SMB/Trailers",
                                "protocol": "cifs",
                                "verified": True,
                            }
                        ]
                    }
                }
            },
        },
    }, secrets={"smb": {"password": "stored-secret"}})

    response = client.patch("/api/config/network-access", json={
        "oppo": {"pre_mount_smb": True},
        "smb": {"username": "nas-user", "password": ""},
        "path_mappings": [
            {
                "source_path": "/volume1/Video/Trailers",
                "player_path": "/NAS-SMB/Trailers",
                "protocol": "cifs",
                "verified": False,
            }
        ],
    })

    assert response.status_code == 200
    assert runtime.config["smb"]["password"] == "stored-secret"
    assert runtime.config["oppo"]["pre_mount_smb"] is True
    emby_path_mappings = runtime.config["media_servers"]["providers"]["emby"]["playback"]["path_mappings"]
    assert emby_path_mappings[0]["verified"] is False
    assert response.json()["smb"]["password_configured"] is True
    assert "password" not in response.json()["smb"]


def test_oppo_check_marks_saved_player_verified_then_section_edit_makes_it_stale(tmp_path, monkeypatch):
    client, runtime = _client(tmp_path, monkeypatch, config={
        "oppo": {
            "ip": "192.168.1.10",
            "always_on": True,
            "connection_timeout_seconds": 3,
            "playback_start_timeout_seconds": 30,
            "nfs_mount_timeout_seconds": 60,
        },
        "playback": {"path_mappings": []},
        "media_server": {"server_url": "", "access_token": ""},
    })

    with patch("home_cinema_control.web.api_app.check_oppo_control_api", return_value=0):
        response = client.post("/api/oppo/check", json=copy.deepcopy(runtime.config))

    assert response.status_code == 200
    assert response.json()["verification_persisted"] is True
    assert client.get("/api/config/readiness").json()["media_player"]["status"] == "verified"

    response = client.patch("/api/config/oppo", json={"ip": "192.168.1.11"})

    assert response.status_code == 200
    assert client.get("/api/config/readiness").json()["media_player"]["status"] == "stale"


def test_detect_sources_returns_detected_tv_data_without_saving(tmp_path, monkeypatch):
    client, runtime = _client(tmp_path, monkeypatch, config={
        "tv": {"enabled": True, "model": "LG", "ip": "192.168.1.20"},
        "oppo": {"ip": "192.168.1.10"},
        "playback": {"path_mappings": []},
    })

    def _mutate_sources(config):
        config.setdefault("tv", {})["available_hdmi_inputs"] = [
            {"id": "HDMI_1", "appId": "hdmi1"}
        ]
        return "OK"

    with patch("home_cinema_control.web.api_app.detect_tv_sources", side_effect=_mutate_sources):
        response = client.post("/api/tv/sources", json=copy.deepcopy(runtime.config))

    assert response.status_code == 200
    assert response.json()["tv"]["available_hdmi_inputs"] == [
        {"id": "HDMI_1", "appId": "hdmi1"}
    ]
    assert "available_hdmi_inputs" not in runtime.config["tv"]


class MutableRuntime:
    def __init__(self, config):
        self.config = copy.deepcopy(config)
        self.last_diagnostic = None

    def load_config(self):
        return copy.deepcopy(self.config)

    def save_config(self, config):
        self.config = copy.deepcopy(config)

    def get_state(self):
        return {"Playstate": "Playing"}

    def restart_process(self):
        raise AssertionError("restart_process should not run in these tests")

    def set_last_diagnostic(self, diagnostic):
        self.last_diagnostic = diagnostic

    def get_last_diagnostic(self):
        return self.last_diagnostic


def _client(tmp_path: Path, monkeypatch, *, config, secrets=None):
    config_file = tmp_path / "config.json"
    secrets_file = tmp_path / "secrets.json"
    config_file.write_text(json.dumps(config), encoding="utf-8")
    secrets_file.write_text(json.dumps(secrets or {}), encoding="utf-8")
    monkeypatch.setenv("HCC_SECRETS_FILE_PATH", str(secrets_file))

    runtime = MutableRuntime(config)
    service = WebConfigService(runtime=runtime, config_file=config_file)
    api_runtime = WebApiRuntime(
        runtime=runtime,
        config_service=service,
        config_file=config_file,
        log_file=tmp_path / "emby_xnoppo_client_logging.log",
        frontend_dist_dir=tmp_path / "frontend" / "dist",
    )
    client = TestClient(create_api_app(api_runtime))

    return client, runtime
