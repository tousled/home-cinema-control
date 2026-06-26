from __future__ import annotations

from home_cinema_control.media_servers.common.media_tracks import (
    MediaTrack,
    MediaTrackKind,
)
from home_cinema_control.media_servers.common.models import (
    MediaServerItemPlaybackInfo,
)
from home_cinema_control.media_servers.common.playback_source import (
    MediaServerPlaybackSource,
)
from home_cinema_control.playback.content_kind import MediaContentKind
from home_cinema_control.playback.time_units import TICKS_PER_SECOND

_ITEM_TYPE_TO_CONTENT_KIND = {
    "Movie": MediaContentKind.MOVIE,
    "Episode": MediaContentKind.EPISODE,
    "MusicVideo": MediaContentKind.CONCERT,
    "LiveTvProgram": MediaContentKind.LIVE_TV,
    "Recording": MediaContentKind.LIVE_TV,
    "TvChannel": MediaContentKind.LIVE_TV,
    "LiveTvChannel": MediaContentKind.LIVE_TV,
}

_STREAM_TYPE_TO_TRACK_KIND = {
    "Video": MediaTrackKind.VIDEO,
    "Audio": MediaTrackKind.AUDIO,
    "Subtitle": MediaTrackKind.SUBTITLE,
}


def media_server_playback_source_from_item(
    item_data: dict,
    media_source_id: str,
) -> MediaServerPlaybackSource:
    media_source = _find_media_source(item_data, media_source_id)

    return MediaServerPlaybackSource(
        path=media_source.get("Path", ""),
        container=media_source.get("Container", ""),
        duration_seconds=_duration_seconds_from_runtime_ticks(media_source),
        production_year=item_data.get("ProductionYear"),
        title=item_data.get("Name", ""),
        content_kind=_content_kind_from_item_type(item_data.get("Type")),
    )


def media_server_item_playback_info_from_item(
    item_data: dict | None,
    *,
    media_source_id: str | None,
) -> MediaServerItemPlaybackInfo:
    item_data = item_data or {}
    user_data = item_data.get("UserData") or {}
    media_source = _selected_media_source(
        item_data.get("MediaSources") or [],
        media_source_id,
    )
    saved_position_ticks = user_data.get("PlaybackPositionTicks")

    return MediaServerItemPlaybackInfo(
        saved_position_ticks=(
            int(saved_position_ticks) if saved_position_ticks is not None else None
        ),
        played=user_data.get("Played"),
        play_count=user_data.get("PlayCount"),
        playback_percentage=user_data.get("PlayedPercentage"),
        media_source_container=(media_source or {}).get("Container"),
        media_source_video_type=(media_source or {}).get("VideoType"),
    )


def media_tracks_from_item(item_data: dict | None) -> list[MediaTrack]:
    item_data = item_data or {}
    tracks: list[MediaTrack] = []
    for stream in item_data.get("MediaStreams") or []:
        try:
            source_index = int(stream.get("Index", -1))
        except (TypeError, ValueError):
            source_index = -1
        tracks.append(
            MediaTrack(
                kind=_STREAM_TYPE_TO_TRACK_KIND.get(
                    stream.get("Type"),
                    MediaTrackKind.OTHER,
                ),
                source_index=source_index,
            )
        )
    return tracks


def _find_media_source(item_data: dict, media_source_id: str) -> dict:
    for media_source in item_data.get("MediaSources", []):
        if media_source.get("Id") == media_source_id:
            return media_source

    return item_data


def _selected_media_source(
    media_sources: list[dict],
    media_source_id: str | None,
) -> dict | None:
    if media_source_id:
        for media_source in media_sources:
            if media_source.get("Id") == media_source_id:
                return media_source

    if media_sources:
        return media_sources[0]

    return None


def _duration_seconds_from_runtime_ticks(media_source: dict) -> int:
    try:
        return max(0, int(media_source.get("RunTimeTicks", 0)) // TICKS_PER_SECOND)
    except (TypeError, ValueError):
        return 0


def _content_kind_from_item_type(item_type: str | None) -> MediaContentKind:
    return _ITEM_TYPE_TO_CONTENT_KIND.get(item_type, MediaContentKind.OTHER)

