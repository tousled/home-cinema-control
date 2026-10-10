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
