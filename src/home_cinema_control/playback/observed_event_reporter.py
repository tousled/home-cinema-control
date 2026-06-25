from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Protocol

from home_cinema_control.playback.time_units import TICKS_PER_SECOND
from home_cinema_control.playback.observed_events import (
    ObservedPlaybackEvent,
    ObservedPlaybackEventType,
    ObservedPlaybackState,
)

logger = logging.getLogger(__name__)


class ObservedPlaybackEventSink(Protocol):
    @property
    def last_position_ticks(self) -> int: ...

    def report_event(
        self,
        event_name: str,
        *,
        position_ticks: int,
        is_paused: bool = False,
        audio_track_id: int | None = None,
        subtitle_track_id: int | None = None,
    ): ...

    def stopped(
        self,
        *,
        position_seconds: int,
        duration_seconds: int = 0,
        is_paused: bool = False,
        is_muted: bool = False,
        played: bool = True,
    ): ...

    def progress(self, *, position_seconds: int, duration_seconds: int = 0): ...


class ObservedPlaybackPositionProvider(Protocol):
    def current_position_ticks(self) -> int: ...


class ObservedPlaybackTrackMapper(Protocol):
    def player_audio_to_source_track_id(
        self,
        player_track_index: int,
    ) -> int | None: ...

    def player_subtitle_to_source_track_id(
        self,
        player_track_index: int,
    ) -> int | None: ...


@dataclass(frozen=True)
class ObservedPlaybackReportResult:
    reported: bool
    event_name: str | None = None
    detail: str = ""


class ObservedPlaybackEventReporter:
    """Reports observed player-side events back through the media-server boundary."""

    def __init__(
        self,
        *,
        sink: ObservedPlaybackEventSink,
        position_provider: ObservedPlaybackPositionProvider | None = None,
        track_mapper: ObservedPlaybackTrackMapper,
    ) -> None:
        self._sink = sink
        self._position_provider = position_provider
        self._track_mapper = track_mapper
        self._last_position_seconds: int | None = None

    def report(self, event: ObservedPlaybackEvent) -> ObservedPlaybackReportResult:
        if event.event_type == ObservedPlaybackEventType.POSITION_UPDATED:
            return self._report_position_update(event)

        if event.event_type == ObservedPlaybackEventType.PLAYBACK_STATE_CHANGED:
            return self._report_playback_state(event)

        if event.event_type == ObservedPlaybackEventType.AUDIO_TRACK_CHANGED:
            return self._report_audio_track(event)

        if event.event_type == ObservedPlaybackEventType.SUBTITLE_TRACK_CHANGED:
            return self._report_subtitle_track(event)

        return ObservedPlaybackReportResult(False, detail="Unsupported observed event.")

    def _report_playback_state(
        self,
        event: ObservedPlaybackEvent,
    ) -> ObservedPlaybackReportResult:
        if event.playback_state == ObservedPlaybackState.PAUSED:
            self._sink.report_event(
                "Pause",
                position_ticks=self._position_ticks(),
                is_paused=True,
            )
            return ObservedPlaybackReportResult(True, event_name="Pause")

        if event.playback_state == ObservedPlaybackState.PLAYING:
            self._sink.report_event(
                "Unpause",
                position_ticks=self._position_ticks(),
                is_paused=False,
            )
            return ObservedPlaybackReportResult(True, event_name="Unpause")

        if event.playback_state == ObservedPlaybackState.STOPPED:
            position_seconds = int(self._position_ticks() / TICKS_PER_SECOND)
            self._sink.stopped(position_seconds=position_seconds, played=False)
            return ObservedPlaybackReportResult(True, event_name="Stopped")

        return ObservedPlaybackReportResult(False, detail="Missing playback state.")

    def _report_audio_track(
        self,
        event: ObservedPlaybackEvent,
    ) -> ObservedPlaybackReportResult:
        if event.player_audio_track_index is None:
            return ObservedPlaybackReportResult(
                False,
                detail="Missing audio track index.",
            )

        source_track_id = self._track_mapper.player_audio_to_source_track_id(
            event.player_audio_track_index
        )
        if source_track_id is None:
            logger.warning(
                "Observed audio track could not be mapped to source track | "
                "player_index=%s",
                event.player_audio_track_index,
            )
            return ObservedPlaybackReportResult(False, detail="Unknown audio track.")

        self._sink.report_event(
            "AudioTrackChange",
            position_ticks=self._position_ticks(),
            audio_track_id=source_track_id,
        )
        return ObservedPlaybackReportResult(True, event_name="AudioTrackChange")

    def _report_subtitle_track(
        self,
        event: ObservedPlaybackEvent,
    ) -> ObservedPlaybackReportResult:
        if event.player_subtitle_track_index is None:
            return ObservedPlaybackReportResult(
                False,
                detail="Missing subtitle track index.",
            )

        source_track_id = self._track_mapper.player_subtitle_to_source_track_id(
            event.player_subtitle_track_index
        )
        if source_track_id is None:
            logger.warning(
                "Observed subtitle track could not be mapped to source track | "
                "player_index=%s",
                event.player_subtitle_track_index,
            )
            return ObservedPlaybackReportResult(False, detail="Unknown subtitle track.")

        self._sink.report_event(
            "SubtitleTrackChange",
            position_ticks=self._position_ticks(),
            subtitle_track_id=source_track_id,
        )
        return ObservedPlaybackReportResult(True, event_name="SubtitleTrackChange")

    def _report_position_update(
        self,
        event: ObservedPlaybackEvent,
    ) -> ObservedPlaybackReportResult:
        if event.position_seconds is None:
            return ObservedPlaybackReportResult(False, detail="Missing position_seconds.")
        self._last_position_seconds = event.position_seconds
        self._sink.progress(position_seconds=event.position_seconds)
        return ObservedPlaybackReportResult(True, event_name="PositionUpdate")

    def _position_ticks(self) -> int:
        if self._last_position_seconds is not None:
            return self._last_position_seconds * TICKS_PER_SECOND
        if hasattr(self._sink, "last_position_ticks"):
            return self._sink.last_position_ticks
        if self._position_provider is not None:
            return self._position_provider.current_position_ticks()
        return 0
