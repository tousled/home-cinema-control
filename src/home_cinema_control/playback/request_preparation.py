from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from home_cinema_control.media_servers.emby.playback import MediaServerPlaybackSource
from home_cinema_control.playback.intent import PlaybackIntent
from home_cinema_control.playback.media_location import resolve_player_media_file_location
from home_cinema_control.devices.tv.models import TvInputTarget
from home_cinema_control.playback.startup.completion import PlayMediaItemRequest
from home_cinema_control.playback.startup.models import (
    OppoPlaybackStartRequest,
    PlaybackOutputSwitchRequest,
    PlayerMediaFileLocation,
)

PLAYBACK_START_POLL_INTERVAL_SECONDS = 0.5


@dataclass(frozen=True)
class PreparedPlaybackRequests:
    """All orchestrator request objects derived from one media-server intent.

    The application service receives Emby-flavoured item/config data. This value
    object groups the clean requests consumed by playback orchestrators plus the
    resolved media location used for user-facing logs/messages.
    """

    media_location: PlayerMediaFileLocation
    movie_path: str
    output_switch_request: PlaybackOutputSwitchRequest
    oppo_playback_start_request: OppoPlaybackStartRequest
    startup_completion_request: PlayMediaItemRequest


def prepare_playback_requests(
    *,
    config: dict[str, Any],
    intent: PlaybackIntent,
        item_info: MediaServerPlaybackSource,
    previous_tv_app_id_override: str | None,
) -> PreparedPlaybackRequests:
    """Translate config, selected media item, and playback intent into requests."""
    media_location = resolve_player_media_file_location(
        emby_media_path=item_info.path,
        playback_file_format=item_info.container,
        path_mappings=config["playback"]["path_mappings"],
    )
    output_switch_request = _output_switch_request(
        config,
        previous_tv_app_id_override=previous_tv_app_id_override,
    )
    oppo_playback_start_request = _oppo_playback_start_request(
        config,
        media_location=media_location,
    )
    startup_completion_request = PlayMediaItemRequest(
        start_position_seconds=intent.start_position_seconds,
        expected_duration_seconds=item_info.duration_seconds,
        source_user_id=intent.source_user_id,
        media_item_id=intent.media_item_id,
        selected_source_audio_track_id=intent.selected_audio_track_id,
        selected_source_subtitle_track_id=intent.selected_subtitle_track_id,
    )

    return PreparedPlaybackRequests(
        media_location=media_location,
        movie_path=item_info.path,
        output_switch_request=output_switch_request,
        oppo_playback_start_request=oppo_playback_start_request,
        startup_completion_request=startup_completion_request,
    )


def _output_switch_request(
    config: dict[str, Any],
    *,
    previous_tv_app_id_override: str | None,
) -> PlaybackOutputSwitchRequest:
    tv = config.get("tv") or {}
    av = config.get("av") or {}

    return PlaybackOutputSwitchRequest(
        tv_input=_resolve_tv_input_target(tv),
        av_input_id=av.get("player_hdmi_input"),
        tv_enabled=tv.get("enabled") is True,
        av_enabled=av.get("enabled") is True,
        previous_tv_app_id_override=previous_tv_app_id_override,
    )


def _resolve_tv_input_target(tv: dict) -> TvInputTarget:
    try:
        source_index = int(tv.get("player_hdmi_input_id", 0))
    except (ValueError, TypeError):
        return TvInputTarget(input_id="")

    sources = tv.get("available_hdmi_inputs") or []

    if not sources or not (0 <= source_index < len(sources)):
        return TvInputTarget(input_id="")

    selected = sources[source_index]
    return TvInputTarget(
        input_id=selected.get("id", ""),
        confirmation_app_id=selected.get("appId") or None,
    )


def _oppo_playback_start_request(
    config: dict[str, Any],
    *,
    media_location: PlayerMediaFileLocation,
) -> OppoPlaybackStartRequest:
    oppo = config["oppo"]

    return OppoPlaybackStartRequest(
        media_location=media_location,
        network_protocol=media_location.network_protocol,
        assume_player_already_on=oppo["always_on"] is True,
        startup_timeout_seconds=oppo["playback_start_timeout_seconds"],
        poll_interval_seconds=PLAYBACK_START_POLL_INTERVAL_SECONDS,
    )
