from datetime import datetime, timedelta, timezone

from home_cinema_control.telemetry.service import TelemetryService


class FakeTelemetryClient:
    def __init__(self, result=True):
        self.result = result
        self.calls = []

    def send(self, endpoint_url, payloads):
        self.calls.append((endpoint_url, list(payloads)))
        return self.result


def _config(enabled=False, installation_id="", last_heartbeat_at=""):
    return {
        "Version": "1.2.3",
        "app": {"language": "es-ES"},
        "telemetry": {
            "enabled": enabled,
            "installation_id": installation_id,
            "endpoint_url": "https://telemetry.example/v1/events",
            "last_heartbeat_at": last_heartbeat_at,
        },
        "media_servers": {
            "active": "emby",
            "providers": {
                "emby": {
                    "server_url": "http://emby.local",
                    "access_token": "secret",
                    "playback": {
                        "path_mappings": [
                            {
                                "source_path": "/private",
                                "player_path": "/mnt/private",
                                "protocol": "nfs",
                            }
                        ]
                    },
                }
            },
        },
        "oppo": {"ip": "192.168.1.50"},
    }


def _service(tmp_path, config, client):
    state = {"config": config}

    def load_config():
        return state["config"]

    def save_config(updated):
        state["config"] = updated

    return (
        TelemetryService(
            config_file=tmp_path / "config.json",
            load_config=load_config,
            save_config=save_config,
            client=client,
        ),
        state,
    )


def test_disabled_telemetry_emits_nothing(tmp_path):
    client = FakeTelemetryClient()
    service, _ = _service(tmp_path, _config(enabled=False), client)

    assert service.emit("heartbeat") is False
    assert client.calls == []


def test_enable_generates_installation_id_and_sends_opt_in(tmp_path):
    client = FakeTelemetryClient()
    service, state = _service(tmp_path, _config(enabled=False), client)

    status = service.enable()

    assert status["enabled"] is True
    assert status["installation_id_configured"] is True
    assert state["config"]["telemetry"]["enabled"] is True
    assert state["config"]["telemetry"]["installation_id"]
    assert client.calls[0][1][0].event_name == "install_opt_in"


def test_failed_send_is_queued_without_raising(tmp_path):
    client = FakeTelemetryClient(result=False)
    service, _ = _service(
        tmp_path,
        _config(
            enabled=True,
            installation_id="11111111-1111-4111-8111-111111111111",
        ),
        client,
    )

    assert service.emit("heartbeat") is False
    assert service.status()["queue_count"] == 1


def test_successful_emit_flushes_existing_queue(tmp_path):
    failing_client = FakeTelemetryClient(result=False)
    service, state = _service(
        tmp_path,
        _config(
            enabled=True,
            installation_id="11111111-1111-4111-8111-111111111111",
        ),
        failing_client,
    )
    service.emit("heartbeat")

    successful_client = FakeTelemetryClient(result=True)
    service, _ = _service(tmp_path, state["config"], successful_client)

    assert service.emit("app_started") is True
    assert service.status()["queue_count"] == 0
    assert len(successful_client.calls) == 2
    assert successful_client.calls[0][1][0].event_name == "heartbeat"
    assert successful_client.calls[1][1][0].event_name == "app_started"


def test_disable_clears_pending_queue(tmp_path):
    client = FakeTelemetryClient(result=False)
    service, _ = _service(
        tmp_path,
        _config(
            enabled=True,
            installation_id="11111111-1111-4111-8111-111111111111",
        ),
        client,
    )
    service.emit("heartbeat")

    status = service.disable()

    assert status["enabled"] is False
    assert status["queue_count"] == 0


def test_disable_can_reset_identity(tmp_path):
    client = FakeTelemetryClient()
    service, state = _service(
        tmp_path,
        _config(
            enabled=True,
            installation_id="11111111-1111-4111-8111-111111111111",
        ),
        client,
    )

    service.disable(reset_identity=True)

    assert state["config"]["telemetry"]["installation_id"] == ""


def test_heartbeat_is_throttled(tmp_path):
    recent = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    client = FakeTelemetryClient()
    service, _ = _service(
        tmp_path,
        _config(
            enabled=True,
            installation_id="11111111-1111-4111-8111-111111111111",
            last_heartbeat_at=recent,
        ),
        client,
    )

    assert service.emit_heartbeat_if_due() is False
    assert client.calls == []


def test_due_heartbeat_updates_timestamp(tmp_path):
    old = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()
    client = FakeTelemetryClient()
    service, state = _service(
        tmp_path,
        _config(
            enabled=True,
            installation_id="11111111-1111-4111-8111-111111111111",
            last_heartbeat_at=old,
        ),
        client,
    )

    assert service.emit_heartbeat_if_due() is True
    assert state["config"]["telemetry"]["last_heartbeat_at"] != old
