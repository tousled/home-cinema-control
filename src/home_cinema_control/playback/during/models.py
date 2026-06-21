from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Protocol

from home_cinema_control.playback.startup.models import OppoPlaybackState


class PlaybackMonitoringStopReason(Enum):
    PLAYER_IDLE = "player_idle"
    TRANSITION_GRACE_EXCEEDED = "transition_grace_exceeded"
    NATURAL_END = "natural_end"
    EVENT_WATCHDOG_EXPIRED = "event_watchdog_expired"
    OBSERVATION_WINDOW_EXPIRED = "observation_window_expired"


@dataclass(frozen=True)
class PlaybackMonitoringRequest:
    initial_position_seconds: int = 0
    expected_duration_seconds: int = 0
    poll_interval_seconds: float = 1.0
    max_transition_polls: int = 30
    max_end_of_media_polls: int = 3
    progress_interval_seconds: float = 10.0
    event_watchdog_seconds: float = 30.0
    natural_end_reset_tolerance_seconds: int = 30
    monitoring_timeout_seconds: float | None = None
    report_progress: bool = True
    is_paused: bool = False
    is_muted: bool = False
    last_active_state: OppoPlaybackState | None = None


@dataclass(frozen=True)
class PlaybackMonitoringResult:
    position_seconds: int
    duration_seconds: int
    final_state: OppoPlaybackState
    stop_reason: PlaybackMonitoringStopReason = PlaybackMonitoringStopReason.PLAYER_IDLE

    @property
    def played(self) -> bool:
        if self.duration_seconds <= 0:
            return False

        return (self.position_seconds / self.duration_seconds) > 0.95


class DuringPlaybackOrchestratorProtocol(Protocol):
    def monitor_until_stopped(
        self,
        request: PlaybackMonitoringRequest,
    ) -> PlaybackMonitoringResult: ...
