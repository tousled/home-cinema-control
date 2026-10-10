from __future__ import annotations

import logging

from home_cinema_control.telemetry.events import TelemetryEvent
from home_cinema_control.telemetry.service import TelemetryService

logger = logging.getLogger(__name__)


class TelemetryConsumer:
    """Delivers telemetry application events outside the producer's flow."""

    name = "telemetry"

    def __init__(self, telemetry_service: TelemetryService) -> None:
        self._telemetry_service = telemetry_service

    def consume(self, event: TelemetryEvent) -> None:
        try:
            self._telemetry_service.emit_async(
                event.event_name,
                event=dict(event.attributes),
                event_id=event.event_id,
                occurred_at=event.occurred_at,
            )
        except Exception:
            logger.exception(
                "Telemetry event consumer failed | event=%s | event_id=%s",
                event.event_name,
                event.event_id,
            )
