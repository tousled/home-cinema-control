from home_cinema_control.telemetry.consumer import TelemetryConsumer
from home_cinema_control.telemetry.events import TelemetryEvent
from home_cinema_control.playback.events import (
    PlaybackEvent,
    PlaybackEventType,
    PlaybackHandoffAttemptedEvent,
    PlaybackHandoffFinalizedEvent,
)


def test_consumer_forwards_event_identity_and_attributes_without_network_work():
    service = RecordingTelemetryService()
    event = TelemetryEvent(
        event_name="playback_failed",
        attributes={"component": "oppo", "code": "OPPO_UNAVAILABLE"},
        event_id="event-1",
        occurred_at="2026-10-10T12:00:00+00:00",
    )

    TelemetryConsumer(service).consume(event)

    assert service.calls == [
        (
            "playback_failed",
            {"component": "oppo", "code": "OPPO_UNAVAILABLE"},
            "event-1",
            "2026-10-10T12:00:00+00:00",
        )
    ]


def test_consumer_maps_playback_started_domain_fact_to_telemetry():
    service = RecordingTelemetryService()
    event = PlaybackEvent(
        event_id="event-started",
        session_id="playback-1",
        event_type=PlaybackEventType.STARTED,
        title="Movie",
        source="emby",
        player="oppo",
        startup_metrics={"prepare": 0.4},
    )

    TelemetryConsumer(service).consume(event)

    assert service.calls == [
        (
            "playback_started",
            {
                "session_id": "playback-1",
                "title": "Movie",
                "source": "emby",
                "player": "oppo",
                "startup_metrics": {"prepare": 0.4},
            },
            "event-started",
            None,
        )
    ]


def test_consumer_maps_failed_handoff_fact_to_telemetry():
    service = RecordingTelemetryService()
    event = PlaybackHandoffFinalizedEvent(
        event_id="event-finalized",
        handoff_id="handoff-1",
        origin="observed_tv_client",
        successful=False,
        media_item_id="item-1",
        media_source_id="source-1",
        diagnostic_component="oppo",
        diagnostic_code="OPPO_UNAVAILABLE",
    )

    TelemetryConsumer(service).consume(event)

    assert service.calls == [
        (
            "playback_failed",
            {
                "component": "oppo",
                "handoff_id": "handoff-1",
                "media_item_id": "item-1",
                "media_source_id": "source-1",
                    "error_code": "OPPO_UNAVAILABLE",
            },
            "event-finalized",
            None,
        )
    ]


def test_consumer_maps_handoff_attempt_to_telemetry():
    service = RecordingTelemetryService()
    event = PlaybackHandoffAttemptedEvent(
        event_id="event-attempted",
        attempt_id="attempt-1",
        origin="observed_tv_client",
    )

    TelemetryConsumer(service).consume(event)

    assert service.calls == [
        (
            "playback_attempted",
            {"attempt_id": "attempt-1"},
            "event-attempted",
            None,
        )
    ]


class RecordingTelemetryService:
    def __init__(self):
        self.calls = []

    def emit_async(self, event_name, *, event, event_id, occurred_at):
        self.calls.append((event_name, event, event_id, occurred_at))
