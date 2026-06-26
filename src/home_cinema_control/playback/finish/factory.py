from __future__ import annotations

from typing import Any

from home_cinema_control.devices.av.factory import create_av_receiver_or_none
from home_cinema_control.devices.tv.factory import create_tv_controller_or_none
from home_cinema_control.playback.finish.orchestrator import FinishPlaybackOrchestrator
from home_cinema_control.playback.ports import MediaPlayerPort

def create_finish_playback_orchestrator(
    config: dict[str, Any],
        playback_event_publisher,
    *,
    media_player: MediaPlayerPort | None = None,
) -> FinishPlaybackOrchestrator:
    return FinishPlaybackOrchestrator(
        stopped_reporter=playback_event_publisher,
        television=create_tv_controller_or_none(config),
        av_receiver=create_av_receiver_or_none(config),
        media_player=media_player,
    )
