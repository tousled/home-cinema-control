from home_cinema_control.telemetry.client import _to_event_body
from home_cinema_control.telemetry.snapshot import build_telemetry_payload

from tests.test_telemetry_payload import _config


def test_playback_started_flattens_only_safe_startup_metrics():
    config = _config()
    payload = build_telemetry_payload(
        config,
        "playback_started",
        event={
            "startup_metrics": {
                "schema_version": 1,
                "strategy": "sequential",
                "total_ms": 2847,
                "tv_prepare_ms": None,
                "title": "Movie title",
                "path": "/private/Movie.mkv",
            }
        },
    )

    body = _to_event_body(payload)

    assert body["attributes"] == {
        "startup_schema_version": 1,
        "startup_strategy": "sequential",
        "startup_total_ms": 2847,
    }
    assert "Movie title" not in str(body)
    assert "/private/Movie.mkv" not in str(body)


def test_playback_failed_sends_correlations_and_diagnostic_fields():
    config = _config()
    payload = build_telemetry_payload(
        config,
        "playback_failed",
        event={
            "attempt_id": "attempt-1",
            "component": "oppo",
            "error_code": "mount_timeout",
            "title": "Movie title",
            "path": "/private/Movie.mkv",
        },
    )

    body = _to_event_body(payload)

    assert body["attempt_id"] == "attempt-1"
    assert body["event_id"] == payload.event_id
    assert body["schema_version"] == 2
    assert body["attributes"] == {
        "component": "oppo",
        "error_code": "MOUNT_TIMEOUT",
    }
    assert "Movie title" not in str(body)
    assert "/private/Movie.mkv" not in str(body)


def test_playback_rejected_sends_safe_diagnostic_fields_without_handoff_correlation():
    config = _config()
    payload = build_telemetry_payload(
        config,
        "playback_rejected",
        event={
            "component": "media_server",
            "provider": "emby",
            "error_code": "media_server_monitored_device_not_found",
            "title": "Movie title",
            "path": "/private/Movie.mkv",
        },
    )

    body = _to_event_body(payload)

    assert body["event_type"] == "playback_rejected"
    assert body["attempt_id"] is None
    assert body["attributes"] == {
        "component": "media_server",
        "provider": "emby",
        "error_code": "MEDIA_SERVER_MONITORED_DEVICE_NOT_FOUND",
    }
    assert "Movie title" not in str(body)
    assert "/private/Movie.mkv" not in str(body)
