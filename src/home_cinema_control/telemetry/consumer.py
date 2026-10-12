from __future__ import annotations

import logging

from home_cinema_control.telemetry.events import TelemetryEvent
from home_cinema_control.telemetry.service import TelemetryService
from home_cinema_control.playback.events import (
    PlaybackDomainEvent,
    PlaybackEvent,
    PlaybackEventType,
    PlaybackHandoffFinalizedEvent,
)

logger = logging.getLogger(__name__)


class TelemetryConsumer:
    """Delivers telemetry application events outside the producer's flow."""

    name = "telemetry"

    def __init__(self, telemetry_service: TelemetryService) -> None:
        self._telemetry_service = telemetry_service

    def consume(self, event: TelemetryEvent | PlaybackDomainEvent) -> None:
        try:
            if isinstance(event, PlaybackEvent):
                self._consume_playback_event(event)
                return
            if isinstance(event, PlaybackHandoffFinalizedEvent):
                self._consume_handoff_finalized(event)
                return
            self._telemetry_service.emit_async(
                event.event_name,
                event=dict(event.attributes),
                event_id=event.event_id,
                occurred_at=event.occurred_at,
            )
        except Exception:
            logger.exception(
                "Telemetry event consumer failed | event=%s | event_id=%s",
                getattr(event, "event_name", getattr(event, "event_type", "unknown")),
                getattr(event, "event_id", "unknown"),
            )

    def _consume_playback_event(self, event: PlaybackEvent) -> None:
        if event.event_type != PlaybackEventType.STARTED:
            return

        attributes = {
            "session_id": event.session_id,
            "title": event.title,
            "source": event.source,
            "player": event.player,
        }
        if event.startup_metrics is not None:
            attributes["startup_metrics"] = dict(event.startup_metrics)
        self._telemetry_service.emit_async(
            "playback_started",
            event=attributes,
            event_id=event.event_id,
            occurred_at=None,
        )

    def _consume_handoff_finalized(self, event: PlaybackHandoffFinalizedEvent) -> None:
        if event.successful:
            self._telemetry_service.emit_async(
                "playback_finished",
                event={
                    "handoff_id": event.handoff_id,
                    "media_item_id": event.media_item_id,
                    "media_source_id": event.media_source_id,
                },
                event_id=event.event_id,
                occurred_at=None,
            )
            return

        attributes = {
            "component": event.diagnostic_component or "system",
            "handoff_id": event.handoff_id,
            "media_item_id": event.media_item_id,
            "media_source_id": event.media_source_id,
        }
        if event.diagnostic_code is not None:
            attributes["code"] = event.diagnostic_code
        self._telemetry_service.emit_async(
            "playback_failed",
            event=attributes,
            event_id=event.event_id,
            occurred_at=None,
        )
