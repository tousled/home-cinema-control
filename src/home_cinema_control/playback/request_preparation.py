from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from home_cinema_control.config.manager import (
    active_media_server_config,
    active_media_server_type,
)
from home_cinema_control.media_servers.common.playback_source import (
    MediaServerPlaybackSource,
)
from home_cinema_control.playback.intent import PlaybackIntent
from home_cinema_control.playback.media_player_factory import (
    configured_media_player_type,
)
from home_cinema_control.playback.media_location import resolve_player_media_file_location
from home_cinema_control.devices.tv.models import TvInputTarget
from home_cinema_control.playback.startup.completion import PlayMediaItemRequest
from home_cinema_control.playback.startup.models import (
    MediaPlayerStartRequest,
    PlaybackOutputSwitchRequest,
    PlaybackOutputRoute,
    PlayerMediaFileLocation,
)

PLAYBACK_START_POLL_INTERVAL_SECONDS = 0.5


@dataclass(frozen=True)
class PreparedPlaybackRequests:
    """All orchestrator request objects derived from one media-server intent.

    The application service receives a provider-mapped item plus config data.
    This value object groups the clean requests consumed by playback
    orchestrators plus the resolved media location used for user-facing
    logs/messages.
    """

    media_location: PlayerMediaFileLocation
    movie_path: str
    output_switch_request: PlaybackOutputSwitchRequest
    media_player_start_request: MediaPlayerStartRequest
    startup_completion_request: PlayMediaItemRequest


def prepare_playback_requests(
    *,
    config: dict[str, Any],
    intent: PlaybackIntent,
        item_info: MediaServerPlaybackSource,
    previous_tv_app_id_override: str | None,
) -> PreparedPlaybackRequests:
    """Translate config, selected media item, and playback intent into requests."""
    player_type = configured_media_player_type(config).value
    path_mappings = _path_mappings_for_player(
        active_media_server_config(config).playback.path_mappings,
        player_type=player_type,
    )
    media_location = resolve_player_media_file_location(
        emby_media_path=item_info.path,
        playback_file_format=item_info.container,
        playback_file_name=item_info.playback_file_name,
        path_mappings=[mapping.model_dump() for mapping in path_mappings],
    )
    output_switch_request = _output_switch_request(
        config,
        previous_tv_app_id_override=previous_tv_app_id_override,
    )
    media_player_start_request = _media_player_start_request(
        config,
        media_location=media_location,
        requested_start_position_seconds=intent.start_position_seconds,
    )
    startup_completion_request = PlayMediaItemRequest(
        start_position_seconds=intent.start_position_seconds,
        expected_duration_seconds=item_info.duration_seconds,
        source_user_id=intent.source_user_id,
        media_item_id=intent.media_item_id,
        media_source_id=intent.media_source_id,
        selected_source_audio_track_id=intent.selected_audio_track_id,
        selected_source_subtitle_track_id=intent.selected_subtitle_track_id,
    )

    return PreparedPlaybackRequests(
        media_location=media_location,
        movie_path=item_info.path,
        output_switch_request=output_switch_request,
        media_player_start_request=media_player_start_request,
        startup_completion_request=startup_completion_request,
    )


def _output_switch_request(
    config: dict[str, Any],
    *,
    previous_tv_app_id_override: str | None,
) -> PlaybackOutputSwitchRequest:
    tv = config.get("tv") or {}
    av = config.get("av") or {}
    media_player = config.get("media_player") or {}
    output_route = _resolve_output_route(media_player.get("output_route"))

    return PlaybackOutputSwitchRequest(
        tv_input=_resolve_tv_input_target(tv),
        av_input_id=av.get("player_hdmi_input"),
        tv_enabled=tv.get("enabled") is True,
        av_enabled=av.get("enabled") is True,
        route=output_route,
        player_app_id=media_player.get("app_id") or None,
        previous_tv_app_id_override=previous_tv_app_id_override,
        active_media_server_provider_type=_active_provider_type_for_tv_restore(config),
    )


def _active_provider_type_for_tv_restore(config: dict[str, Any]) -> str | None:
    if not active_media_server_config(config).server_url:
        return None
    return str(active_media_server_type(config))


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


def _media_player_start_request(
    config: dict[str, Any],
    *,
    media_location: PlayerMediaFileLocation,
    requested_start_position_seconds: int,
) -> MediaPlayerStartRequest:
    media_player = config.get("media_player") or {}
    legacy_oppo = config.get("oppo") or {}
    always_on = media_player.get("always_on")
    if always_on is None:
        always_on = legacy_oppo.get("always_on", True)
    startup_timeout = media_player.get("playback_start_timeout_seconds")
    if startup_timeout is None:
        startup_timeout = legacy_oppo.get("playback_start_timeout_seconds", 30)
    poll_interval = media_player.get("start_poll_interval_seconds")
    if poll_interval is None:
        poll_interval = PLAYBACK_START_POLL_INTERVAL_SECONDS

    return MediaPlayerStartRequest(
        media_location=media_location,
        requested_start_position_seconds=max(0, requested_start_position_seconds),
        network_protocol=media_location.network_protocol,
        assume_player_already_on=always_on is True,
        startup_timeout_seconds=startup_timeout,
        poll_interval_seconds=poll_interval,
    )


def _resolve_output_route(value: str | None) -> PlaybackOutputRoute:
    normalized = str(value or PlaybackOutputRoute.HDMI.value).strip().lower()
    try:
        return PlaybackOutputRoute(normalized)
    except ValueError:
        return PlaybackOutputRoute.HDMI


def _path_mappings_for_player(path_mappings, *, player_type: str):
    scoped = [
        mapping
        for mapping in path_mappings
        if str(getattr(mapping, "media_player_type", "") or "").strip().lower()
        == player_type
    ]
    if scoped:
        return scoped

    return [
        mapping
        for mapping in path_mappings
        if not getattr(mapping, "media_player_type", "")
    ]
