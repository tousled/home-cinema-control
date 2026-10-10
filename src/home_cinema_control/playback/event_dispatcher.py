"""Compatibility imports for the application event bus."""

from home_cinema_control.application_events import (
    ApplicationEventBus,
    ApplicationEventConsumer,
    EventPublisher,
)
from home_cinema_control.playback.events import PlaybackEvent

ApplicationEventDispatcher = ApplicationEventBus
PlaybackEventConsumer = ApplicationEventConsumer


class PlaybackEventDispatcher(ApplicationEventBus):
    """Compatibility adapter that keeps the legacy playback-only contract."""

    def register(self, consumer: PlaybackEventConsumer) -> None:
        self.subscribe(
            PlaybackEvent,
            consumer,
            ordering_key=lambda event: event.session_id,
        )

__all__ = [
    "ApplicationEventBus",
    "ApplicationEventConsumer",
    "ApplicationEventDispatcher",
    "EventPublisher",
    "PlaybackEventConsumer",
    "PlaybackEventDispatcher",
]
