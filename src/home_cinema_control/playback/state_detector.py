from __future__ import annotations

import threading
from collections.abc import Callable

from home_cinema_control.playback.events import (
    PlaybackEvent,
    PlaybackEventContext,
    PlaybackEventType,
    PlaybackObservation,
    PlaybackObservedState,
    new_playback_event_id,
)


class PlaybackStateDetector:
    """Serializes player observations into canonical lifecycle transitions."""

    def __init__(
        self,
        *,
        event_id_factory: Callable[[], str] = new_playback_event_id,
    ) -> None:
        self._event_id_factory = event_id_factory
        self._lock = threading.RLock()
        self._context: PlaybackEventContext | None = None
        self._state: PlaybackObservedState | None = None

    def start_session(self, context: PlaybackEventContext) -> PlaybackEvent | None:
        with self._lock:
            if self._context is not None:
                return None
            self._context = context
            self._state = PlaybackObservedState.PLAYING
            return self._event(PlaybackEventType.STARTED)

    def observe(self, observation: PlaybackObservation) -> PlaybackEvent | None:
        with self._lock:
            if self._context is None or self._state == observation.state:
                return None

            previous = self._state
            self._state = observation.state
            if previous == PlaybackObservedState.PAUSED:
                event_type = PlaybackEventType.RESUMED
            else:
                event_type = PlaybackEventType.PAUSED
            return self._event(event_type)

    def stop_session(self) -> PlaybackEvent | None:
        with self._lock:
            if self._context is None:
                return None
            event = self._event(PlaybackEventType.STOPPED)
            self._context = None
            self._state = None
            return event

    @property
    def session_id(self) -> str | None:
        with self._lock:
            return self._context.session_id if self._context else None

    def _event(self, event_type: PlaybackEventType) -> PlaybackEvent:
        context = self._context
        assert context is not None
        return PlaybackEvent(
            event_id=self._event_id_factory(),
            session_id=context.session_id,
            event_type=event_type,
            media_type=context.media_type,
            title=context.title,
            source=context.source,
            player=context.player,
        )
