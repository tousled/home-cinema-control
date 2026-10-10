from home_cinema_control.telemetry.consumer import TelemetryConsumer
from home_cinema_control.telemetry.events import TelemetryEvent


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


class RecordingTelemetryService:
    def __init__(self):
        self.calls = []

    def emit_async(self, event_name, *, event, event_id, occurred_at):
        self.calls.append((event_name, event, event_id, occurred_at))
