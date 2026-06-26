from __future__ import annotations

import logging

from home_cinema_control.playback.observed_event_reporter import (
    ObservedPlaybackEventReporter,
)
from home_cinema_control.playback.state import BridgePlaybackState

logger = logging.getLogger(__name__)


class ObservedPlaybackSessionSink:
    """Adapter from observed OPPO events to the active media-server publisher.

    The observed event reporter speaks in neutral playback events. The active
    Emby publisher still expects current bridge pause/free state and Emby track
    ids. This sink keeps that translation in one place and avoids putting Emby
    details inside OPPO listeners.
    """

    def __init__(self, *, playback_state: BridgePlaybackState, publisher) -> None:
        self._state = playback_state
        self._publisher = publisher

    @property
    def last_position_ticks(self) -> int:
        return self._publisher.last_position_ticks

    def report_event(
        self,
        event_name: str,
        *,
        position_ticks: int,
        is_paused: bool = False,
        audio_track_id: int | None = None,
        subtitle_track_id: int | None = None,
    ):
        if event_name == "Pause":
            self._state.playstate = "Paused"
        elif event_name == "Unpause":
            self._state.playstate = "Playing"

        return self._publisher.report_event(
            event_name,
            position_ticks=position_ticks,
            is_paused=is_paused,
            audio_track_id=audio_track_id,
            subtitle_track_id=subtitle_track_id,
        )

    def stopped(
        self,
        *,
        position_seconds: int,
        duration_seconds: int = 0,
        is_paused: bool = False,
        is_muted: bool = False,
        played: bool = True,
    ):
        self._state.playstate = "Free"
        return self._publisher.stopped(
            position_seconds=position_seconds,
            duration_seconds=duration_seconds,
            is_paused=is_paused,
            is_muted=is_muted,
            played=played,
        )

    def progress(self, *, position_seconds: int, duration_seconds: int = 0):
        return self._publisher.progress(
            position_seconds=position_seconds,
            duration_seconds=duration_seconds,
            is_paused=self._state.playstate == "Paused",
        )


def configure_oppo_observed_event_reporting(
    *,
    playback_state: BridgePlaybackState,
    playback_wiring,
        track_mapper,
) -> bool:
    """Wire OPPO observed-event reporting into the active during-playback flow."""
    reporter = ObservedPlaybackEventReporter(
        sink=ObservedPlaybackSessionSink(
            playback_state=playback_state,
            publisher=playback_wiring.playback_event_publisher,
        ),
        track_mapper=track_mapper,
    )
    during_set_reporter = getattr(
        playback_wiring.during_playback_orchestrator,
        "set_observed_event_reporter",
        None,
    )
    if during_set_reporter is not None:
        during_set_reporter(reporter)
        logger.info("OPPO observed event reporting configured")
        return True

    logger.warning("OPPO observed event reporting is not supported by playback wiring.")
    return False
