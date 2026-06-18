from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from home_cinema_control.devices.av.factory import create_av_receiver_or_none
from home_cinema_control.devices.oppo.playback_adapters import (
    create_oppo_playback_adapter,
)
from home_cinema_control.devices.tv.factory import create_tv_controller_or_none
from home_cinema_control.playback.ports import OppoPlaybackPort
from home_cinema_control.playback.startup.orchestrator import (
    PlaybackStartupOrchestrator,
)


@dataclass(frozen=True)
class PlaybackStartupWiring:
    startup_orchestrator: PlaybackStartupOrchestrator
    oppo_playback: OppoPlaybackPort


def create_playback_startup_wiring(
    config: dict[str, Any],
) -> PlaybackStartupWiring:
    oppo_playback = create_oppo_playback_adapter(config)
    startup_orchestrator = PlaybackStartupOrchestrator(
        television=create_tv_controller_or_none(config),
        av_receiver=create_av_receiver_or_none(config),
        oppo_playback=oppo_playback,
    )
    return PlaybackStartupWiring(
        startup_orchestrator=startup_orchestrator,
        oppo_playback=oppo_playback,
    )
