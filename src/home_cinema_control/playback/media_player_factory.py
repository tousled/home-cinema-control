from __future__ import annotations

from enum import StrEnum
from typing import Any

from home_cinema_control.devices.oppo.playback_adapters import (
    create_oppo_playback_adapter,
)
from home_cinema_control.devices.oppo.playback_command_control import (
    create_oppo_playback_command_control,
)
from home_cinema_control.devices.oppo.observation_mode import (
    OppoObservationMode,
    resolve_oppo_observation_mode,
)
from home_cinema_control.devices.oppo.playback_command_control import (
    create_oppo_total_seconds_reader,
)
from home_cinema_control.playback.during import (
    DuringPlaybackOrchestrator,
    PollingPlaybackObservationStrategy,
)
from home_cinema_control.playback.ports import MediaPlayerCommandPort, MediaPlayerPort


class MediaPlayerType(StrEnum):
    OPPO = "oppo"
    KODI = "kodi"


def configured_media_player_type(config: dict[str, Any]) -> MediaPlayerType:
    configured = (config.get("media_player") or {}).get("type")
    if not configured:
        return MediaPlayerType.OPPO

    try:
        return MediaPlayerType(str(configured).strip().lower())
    except ValueError as exc:
        supported = ", ".join(player_type.value for player_type in MediaPlayerType)
        raise ValueError(
            f"Unsupported media player type {configured!r}; supported types: {supported}."
        ) from exc


def create_media_player_adapter(
    config: dict[str, Any], *, step_timer=None
) -> MediaPlayerPort:
    player_type = configured_media_player_type(config)
    if player_type == MediaPlayerType.OPPO:
        return create_oppo_playback_adapter(config, step_timer=step_timer)

    raise NotImplementedError(
        "Kodi media-player support is not implemented yet; keep media_player.type="
        "'oppo' until the Kodi adapter is available."
    )


def create_media_player_command_control(
    config: dict[str, Any],
    *,
    on_verbose_preamble=None,
) -> MediaPlayerCommandPort:
    player_type = configured_media_player_type(config)
    if player_type == MediaPlayerType.OPPO:
        return create_oppo_playback_command_control(
            config,
            on_verbose_preamble=on_verbose_preamble,
        )

    raise NotImplementedError(
        "Kodi media-player command control is not implemented yet."
    )


def create_media_player_observation_orchestrator(
    *,
    config: dict[str, Any],
    media_player: MediaPlayerPort,
    progress_reporter,
    playback_state_observer=None,
):
    polling_orchestrator = PollingPlaybackObservationStrategy(
        media_player=media_player,
        progress_reporter=progress_reporter,
        playback_state_observer=playback_state_observer,
    )

    if configured_media_player_type(config) != MediaPlayerType.OPPO:
        return polling_orchestrator

    if resolve_oppo_observation_mode(config) == OppoObservationMode.POLLING:
        return polling_orchestrator

    return DuringPlaybackOrchestrator(
        config=config,
        polling_orchestrator=polling_orchestrator,
        progress_reporter=progress_reporter,
        playback_state_observer=playback_state_observer,
        oppo_total_provider=create_oppo_total_seconds_reader(config),
    )
