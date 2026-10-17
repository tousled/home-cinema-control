from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any
from uuid import uuid4


class PlaybackEventType(StrEnum):
    DETECTED = "detected"
    STARTED = "started"
    PAUSED = "paused"
    RESUMED = "resumed"
    STOPPED = "stopped"


class PlaybackObservedState(StrEnum):
    PLAYING = "playing"
    PAUSED = "paused"


class PlaybackDomainEvent:
    """Marker base for facts emitted by the playback domain."""

    event_id: str
    event_type: str


@dataclass(frozen=True)
class PlaybackEventContext:
    session_id: str
    media_type: str | None = None
    title: str | None = None
    source: str | None = None
    player: str | None = None
    startup_metrics: dict[str, Any] | None = None
    attempt_id: str | None = None


@dataclass(frozen=True)
class PlaybackObservation:
    state: PlaybackObservedState
    source: str = ""


@dataclass(frozen=True)
class PlaybackEvent(PlaybackDomainEvent):
    event_id: str
    session_id: str
    event_type: PlaybackEventType
    media_type: str | None = None
    title: str | None = None
    source: str | None = None
    player: str | None = None
    startup_metrics: dict[str, Any] | None = None
    attempt_id: str | None = None


@dataclass(frozen=True)
class PlaybackHandoffFinalizedEvent(PlaybackDomainEvent):
    """Fact published after the synchronous handoff cleanup has completed."""

    event_id: str
    handoff_id: str
    origin: str
    successful: bool
    media_item_id: str
    media_source_id: str
    playback_session_id: str | None = None
    diagnostic_component: str | None = None
    diagnostic_code: str | None = None
    event_type: str = "handoff_finalized"
    attempt_id: str | None = None


@dataclass(frozen=True)
class PlaybackHandoffAttemptedEvent(PlaybackDomainEvent):
    """Fact published when a playback handoff is admitted for execution."""

    event_id: str
    attempt_id: str
    origin: str
    event_type: str = "handoff_attempted"


@dataclass(frozen=True)
class PlaybackRejectedEvent(PlaybackDomainEvent):
    """Fact published when observed playback is rejected before handoff."""

    event_id: str
    component: str
    diagnostic_code: str
    provider: str
    event_type: str = "playback_rejected"


def new_playback_session_id() -> str:
    return uuid4().hex


def new_playback_handoff_id() -> str:
    return uuid4().hex


def new_playback_event_id() -> str:
    return uuid4().hex
