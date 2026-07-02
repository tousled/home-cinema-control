import copy
import json
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from home_cinema_control.runtime import HomeCinemaControlRuntime, build_runtime_paths
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

    response = client.patch("/api/v1/config/network-access", json={
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

    with patch("home_cinema_control.web.oppo_routes.check_oppo_control_api", return_value=0):
        response = client.post("/api/v1/oppo/check", json=copy.deepcopy(runtime.config))

    assert response.status_code == 200
    assert response.json()["verification_persisted"] is True
    assert client.get("/api/v1/config/readiness").json()["media_player"]["status"] == "verified"

    response = client.patch("/api/v1/config/oppo", json={"ip": "192.168.1.11"})

    assert response.status_code == 200
    assert client.get("/api/v1/config/readiness").json()["media_player"]["status"] == "stale"


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

    with patch("home_cinema_control.web.tv_routes.detect_tv_sources", side_effect=_mutate_sources):
        response = client.post("/api/v1/tv/sources", json=copy.deepcopy(runtime.config))

    assert response.status_code == 200
    assert response.json()["tv"]["available_hdmi_inputs"] == [
        {"id": "HDMI_1", "appId": "hdmi1"}
    ]
    assert "available_hdmi_inputs" not in runtime.config["tv"]


def test_first_time_sony_setup_persists_psk_on_test_connection_before_any_save(
    tmp_path, monkeypatch
):
    """Reproduces the real report end-to-end: a user configuring a Sony TV for
    the first time (nothing saved yet) fills in ip+psk, clicks "Probar
    conexión", then "Detectar fuentes" — without ever hitting the separate
    "Guardar" button, which sits further down the page. The old
    fingerprint-gated persist_verification_if_submitted_matches_saved never
    persists on a first-time submission (saved tv.ip is empty, so it never
    equals the submitted one), so the PSK was validated live against the TV
    but never written to secrets.json — leaving the very next call with
    nothing to refill.

    Uses the real HomeCinemaControlRuntime (not the in-memory MutableRuntime
    used elsewhere in this file) because the bug only reproduces through an
    actual secrets.json round trip: test-connection must really persist to
    disk for the following /sources call to have anything to merge back in.
    """
    config_file = tmp_path / "config.json"
    secrets_file = tmp_path / "secrets.json"
    config_file.write_text(json.dumps({
        "oppo": {"ip": "192.168.1.10"},
        "playback": {"path_mappings": []},
    }), encoding="utf-8")
    secrets_file.write_text("{}", encoding="utf-8")
    monkeypatch.setenv("HCC_SECRETS_FILE_PATH", str(secrets_file))

    runtime = HomeCinemaControlRuntime(
        paths=build_runtime_paths(tmp_path, config_file),
        version="test",
    )
    service = WebConfigService(runtime=runtime, config_file=config_file)
    api_runtime = WebApiRuntime(
        runtime=runtime,
        config_service=service,
        config_file=config_file,
        log_file=tmp_path / "emby_xnoppo_client_logging.log",
        frontend_dist_dir=tmp_path / "frontend" / "dist",
    )
    client = TestClient(create_api_app(api_runtime))

    with patch("home_cinema_control.web.tv_routes.test_tv_connection", return_value="OK"):
        test_response = client.post("/api/v1/tv/test-connection", json={
            "tv": {"enabled": True, "model": "SONY", "ip": "192.168.0.17", "sony_psk": "user-typed-psk"}
        })

    assert test_response.status_code == 200
    assert "sony_psk" not in test_response.json()["tv"]
    assert test_response.json()["tv"]["sony_psk_configured"] is True
    assert json.loads(secrets_file.read_text())["tv"]["sony_psk"] == "user-typed-psk"

    seen_psk = {}

    def _mutate_sources(config):
        seen_psk["value"] = config.get("tv", {}).get("sony_psk")
        config.setdefault("tv", {})["available_hdmi_inputs"] = [{"id": "HDMI_1"}]
        return "OK"

    # The frontend feeds the sanitized tv section from the response above
    # straight into the next call, so sony_psk arrives empty here too.
    with patch("home_cinema_control.web.tv_routes.detect_tv_sources", side_effect=_mutate_sources):
        sources_response = client.post("/api/v1/tv/sources", json={
            "tv": {"enabled": True, "model": "SONY", "ip": "192.168.0.17", "sony_psk": ""}
        })

    assert sources_response.status_code == 200
    assert seen_psk["value"] == "user-typed-psk"


def test_detect_sources_refills_sony_psk_redacted_by_earlier_test_connection_response(
    tmp_path, monkeypatch
):
    """Reproduces a real report: "TV test connection succeeded" followed by
    "TV configuration error while refreshing Sony TV inputs: tv.sony_psk is
    not configured". The setup wizard's test-connection response strips
    sony_psk from what it hands back (sanitized_submitted_section), and the
    frontend feeds that stripped tv section straight into the next call
    (getTvSources). The /sources route must refill the persisted PSK before
    calling the Sony adapter, the same way /config/network-access refills
    smb.password."""
    client, runtime = _client(tmp_path, monkeypatch, config={
        "tv": {"enabled": True, "model": "SONY", "ip": "192.168.0.17"},
        "oppo": {"ip": "192.168.1.10"},
        "playback": {"path_mappings": []},
    }, secrets={"tv": {"sony_psk": "stored-psk"}})

    seen_psk = {}

    def _mutate_sources(config):
        seen_psk["value"] = config.get("tv", {}).get("sony_psk")
        config.setdefault("tv", {})["available_hdmi_inputs"] = [{"id": "HDMI_1"}]
        return "OK"

    with patch("home_cinema_control.web.tv_routes.detect_tv_sources", side_effect=_mutate_sources):
        response = client.post("/api/v1/tv/sources", json={
            "tv": {"enabled": True, "model": "SONY", "ip": "192.168.0.17", "sony_psk": ""}
        })

    assert response.status_code == 200
    assert seen_psk["value"] == "stored-psk"
    assert "sony_psk" not in response.json()["tv"]


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
