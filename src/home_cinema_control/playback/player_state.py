from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class PlayerPlaybackLifecyclePhase(str, Enum):
    ACTIVE = "ACTIVE"
    IDLE = "IDLE"
    TRANSITION = "TRANSITION"
    UNKNOWN = "UNKNOWN"


class PlayerPlaybackStatus(str, Enum):
    PLAY = "PLAY"
    PAUSE = "PAUSE"
    DISC_MENU = "DISC_MENU"
    FFWD = "FFWD"
    FREV = "FREV"
    SFWD = "SFWD"
    SREV = "SREV"
    STEP = "STEP"

    HOME_MENU = "HOME_MENU"
    SCREEN_SAVER = "SCREEN_SAVER"
    MEDIA_CENTER = "MEDIA_CENTER"
    NO_DISC = "NO_DISC"

    STOP = "STOP"
    OPEN = "OPEN"
    CLOSE = "CLOSE"
    LOADING = "LOADING"

    UNKNOWN = "UNKNOWN"


ACTIVE_PLAYBACK_STATUSES = {
    PlayerPlaybackStatus.PLAY,
    PlayerPlaybackStatus.PAUSE,
    PlayerPlaybackStatus.DISC_MENU,
    PlayerPlaybackStatus.FFWD,
    PlayerPlaybackStatus.FREV,
    PlayerPlaybackStatus.SFWD,
    PlayerPlaybackStatus.SREV,
    PlayerPlaybackStatus.STEP,
}

IDLE_STATUSES = {
    PlayerPlaybackStatus.HOME_MENU,
    PlayerPlaybackStatus.SCREEN_SAVER,
    PlayerPlaybackStatus.MEDIA_CENTER,
    PlayerPlaybackStatus.NO_DISC,
}

TRANSITION_STATUSES = {
    PlayerPlaybackStatus.STOP,
    PlayerPlaybackStatus.OPEN,
    PlayerPlaybackStatus.CLOSE,
    PlayerPlaybackStatus.LOADING,
}


@dataclass(frozen=True)
class PlayerPlaybackState:
    status: PlayerPlaybackStatus
    lifecycle_phase: PlayerPlaybackLifecyclePhase
    raw_response: str
    ok: bool

    @property
    def is_paused(self) -> bool:
        return self.status == PlayerPlaybackStatus.PAUSE

    @property
    def is_playing(self) -> bool:
        return self.status == PlayerPlaybackStatus.PLAY

    @property
    def is_idle(self) -> bool:
        return self.lifecycle_phase == PlayerPlaybackLifecyclePhase.IDLE


@dataclass(frozen=True)
class PlayerPlaybackPosition:
    current_seconds: int
    total_seconds: int
    raw_response: str | None = None

    @property
    def has_valid_position(self) -> bool:
        return self.total_seconds > 0 and self.current_seconds > 0


@dataclass(frozen=True)
class PlayerPlaybackStartResult:
    media_mounted: bool
    playback_command_accepted: bool
    playback_started_on_device: bool
    detail: str | None = None
    mounted_path: str | None = None
    playback_state: PlayerPlaybackState | None = None
    mount_protocol: str | None = None

    @property
    def successful(self) -> bool:
        return (
            self.media_mounted
            and self.playback_command_accepted
            and self.playback_started_on_device
        )


def lifecycle_phase_for_status(
    status: str | PlayerPlaybackStatus,
) -> PlayerPlaybackLifecyclePhase:
    playback_status = (
        status if isinstance(status, PlayerPlaybackStatus) else _status_from_string(status)
    )

    if playback_status in ACTIVE_PLAYBACK_STATUSES:
        return PlayerPlaybackLifecyclePhase.ACTIVE

    if playback_status in IDLE_STATUSES:
        return PlayerPlaybackLifecyclePhase.IDLE

    if playback_status in TRANSITION_STATUSES:
        return PlayerPlaybackLifecyclePhase.TRANSITION

    return PlayerPlaybackLifecyclePhase.UNKNOWN


def _status_from_string(status: str) -> PlayerPlaybackStatus:
    try:
        return PlayerPlaybackStatus(status)
    except ValueError:
        return PlayerPlaybackStatus.UNKNOWN
