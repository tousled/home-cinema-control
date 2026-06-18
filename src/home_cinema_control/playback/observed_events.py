from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ObservedPlaybackEventType(StrEnum):
    PLAYBACK_STATE_CHANGED = "playback_state_changed"
    AUDIO_TRACK_CHANGED = "audio_track_changed"
    SUBTITLE_TRACK_CHANGED = "subtitle_track_changed"
    POSITION_UPDATED = "position_updated"


class ObservedPlaybackState(StrEnum):
    PLAYING = "playing"
    PAUSED = "paused"
    STOPPED = "stopped"


@dataclass(frozen=True)
class ObservedPlaybackEvent:
    """Media-player event observed outside the media-server command path."""

    event_type: ObservedPlaybackEventType
    playback_state: ObservedPlaybackState | None = None
    player_audio_track_index: int | None = None
    player_subtitle_track_index: int | None = None
    position_seconds: int | None = None
    raw: str = ""

