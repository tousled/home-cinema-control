from datetime import datetime, timedelta, timezone

from home_cinema_control.telemetry.events import (
    TelemetryDeployment,
    TelemetryPayload,
    TelemetryProductSnapshot,
)
from home_cinema_control.telemetry.queue import TelemetryQueue


def _payload(event_id: str, occurred_at: str | None = None) -> TelemetryPayload:
    return TelemetryPayload(
        event_name="heartbeat",
        event_id=event_id,
        installation_id="11111111-1111-4111-8111-111111111111",
        occurred_at=occurred_at or datetime.now(timezone.utc).isoformat(),
        hcc_version="1.2.3",
        language="es-ES",
        deployment=TelemetryDeployment(docker=True),
        product=TelemetryProductSnapshot(
            media_server_provider="emby",
            media_server_configured=True,
            media_player="oppo",
            media_player_configured=True,
            tv_enabled=False,
            tv_model="none",
            av_enabled=False,
            av_model="none",
            nfs_enabled=True,
            smb_enabled=False,
        ),
    )


def test_queue_persists_and_loads_payloads(tmp_path):
    queue = TelemetryQueue(tmp_path / "telemetry_queue.json")
    payload = _payload("22222222-2222-4222-8222-222222222222")

    queue.enqueue(payload)

    loaded = queue.load()
    assert len(loaded) == 1
    assert loaded[0].event_id == payload.event_id


def test_queue_discards_oldest_when_max_count_is_exceeded(tmp_path):
    queue = TelemetryQueue(tmp_path / "telemetry_queue.json", max_events=2)

    queue.enqueue(_payload("11111111-1111-4111-8111-111111111111"))
    queue.enqueue(_payload("22222222-2222-4222-8222-222222222222"))
    queue.enqueue(_payload("33333333-3333-4333-8333-333333333333"))

    assert [payload.event_id for payload in queue.load()] == [
        "22222222-2222-4222-8222-222222222222",
        "33333333-3333-4333-8333-333333333333",
    ]


def test_queue_discards_expired_events(tmp_path):
    old = (datetime.now(timezone.utc) - timedelta(days=8)).isoformat()
    queue = TelemetryQueue(tmp_path / "telemetry_queue.json", max_age_days=7)

    queue.enqueue(_payload("11111111-1111-4111-8111-111111111111", old))
    queue.enqueue(_payload("22222222-2222-4222-8222-222222222222"))

    assert [payload.event_id for payload in queue.load()] == [
        "22222222-2222-4222-8222-222222222222"
    ]


def test_queue_ignores_corrupt_file(tmp_path):
    queue_file = tmp_path / "telemetry_queue.json"
    queue_file.write_text("not-json", encoding="utf-8")

    queue = TelemetryQueue(queue_file)

    assert queue.load() == []


def test_clear_removes_queue_file(tmp_path):
    queue_file = tmp_path / "telemetry_queue.json"
    queue = TelemetryQueue(queue_file)
    queue.enqueue(_payload("22222222-2222-4222-8222-222222222222"))

    queue.clear()

    assert not queue_file.exists()
