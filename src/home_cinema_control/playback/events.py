from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from uuid import uuid4


class PlaybackEventType(StrEnum):
    STARTED = "started"
    PAUSED = "paused"
    RESUMED = "resumed"
    STOPPED = "stopped"


class PlaybackObservedState(StrEnum):
    PLAYING = "playing"
    PAUSED = "paused"


@dataclass(frozen=True)
class PlaybackEventContext:
    session_id: str
    media_type: str | None = None
    title: str | None = None
    source: str | None = None
    player: str | None = None


@dataclass(frozen=True)
class PlaybackObservation:
    state: PlaybackObservedState
    source: str = ""


@dataclass(frozen=True)
class PlaybackEvent:
    event_id: str
    session_id: str
    event_type: PlaybackEventType
    media_type: str | None = None
    title: str | None = None
    source: str | None = None
    player: str | None = None


def new_playback_session_id() -> str:
    return uuid4().hex


def new_playback_event_id() -> str:
    return uuid4().hex
