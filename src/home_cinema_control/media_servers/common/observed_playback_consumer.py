from __future__ import annotations

from home_cinema_control.playback.state import BridgePlaybackState


class MediaServerObservedPlaybackConsumer:
    """Translate neutral player observations into media-server reports."""

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
