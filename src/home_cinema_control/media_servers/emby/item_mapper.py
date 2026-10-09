from __future__ import annotations

from pathlib import PurePosixPath
from urllib.parse import unquote, urlsplit

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
    media_sources = item_data.get("MediaSources") or []
    media_source = _selected_media_source(media_sources, media_source_id)
    physical_path = _physical_media_path(item_data, media_source)
    container = _resolved_container(
        item_data,
        media_source,
        physical_path=physical_path,
    )
    playback_file_name = _resolved_playback_file_name(
        physical_path=physical_path,
        container=container,
        media_source=media_source,
    )

    return MediaServerPlaybackSource(
        path=physical_path,
        container=container,
        duration_seconds=_duration_seconds_from_runtime_ticks(
            media_source or item_data
        ),
        production_year=item_data.get("ProductionYear"),
        title=item_data.get("Name", ""),
        content_kind=_content_kind_from_item_type(item_data.get("Type")),
        playback_file_name=playback_file_name,
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


def _physical_media_path(
    item_data: dict,
    media_source: dict | None,
) -> str:
    item_path = str(item_data.get("Path") or "")
    source_path = str((media_source or {}).get("Path") or "")

    if _is_strm_path(item_path) or _is_strm_container(item_data.get("Container")):
        return item_path or source_path

    return source_path or item_path


def _resolved_container(
    item_data: dict,
    media_source: dict | None,
    *,
    physical_path: str,
) -> str:
    source_container = _normalize_container((media_source or {}).get("Container"))
    if source_container and not _is_strm_container(source_container):
        return source_container

    item_container = _normalize_container(item_data.get("Container"))
    if item_container and not _is_strm_container(item_container):
        return item_container

    inferred_container = _container_from_target_path(
        str((media_source or {}).get("Path") or "")
    )
    if inferred_container:
        return inferred_container

    if not (
        _is_strm_path(physical_path)
        or _is_strm_container(source_container)
        or _is_strm_container(item_container)
    ):
        return source_container or item_container

    raise ValueError(
        "Could not resolve a playable container for an Emby STRM media source."
    )


def _resolved_playback_file_name(
    *,
    physical_path: str,
    container: str,
    media_source: dict | None,
) -> str | None:
    if not _is_strm_path(physical_path):
        return None

    stem = _basename(physical_path)
    if not stem:
        raise ValueError("Could not resolve a playable filename for an Emby STRM item.")

    if stem.lower().endswith(".strm"):
        stem = stem[:-5]

    extension = _container_extension(container)
    if not extension:
        extension = _container_from_target_path(
            str((media_source or {}).get("Path") or "")
        )
    if not extension:
        raise ValueError("Could not resolve a playable filename for an Emby STRM item.")

    return f"{stem}.{extension}"


def _container_from_target_path(target_path: str) -> str | None:
    if not target_path or _is_strm_path(target_path):
        return None

    parsed = urlsplit(target_path.replace("\\", "/"))
    path = unquote(parsed.path or parsed.geturl())
    suffix = PurePosixPath(path).suffix.lstrip(".").strip().lower()
    return suffix or None


def _container_extension(container: str) -> str | None:
    normalized = _normalize_container(container)
    if not normalized or _is_strm_container(normalized):
        return None
    return normalized.lstrip(".")


def _normalize_container(container: object) -> str:
    return str(container or "").strip().lower().lstrip(".")


def _is_strm_container(container: object) -> bool:
    return _normalize_container(container) == "strm"


def _is_strm_path(path: str) -> bool:
    return _basename(path).lower().endswith(".strm")


def _basename(path: str) -> str:
    normalized = str(path or "").replace("\\", "/")
    return normalized.rsplit("/", 1)[-1]


def _duration_seconds_from_runtime_ticks(media_source: dict) -> int:
    try:
        return max(0, int(media_source.get("RunTimeTicks", 0)) // TICKS_PER_SECOND)
    except (TypeError, ValueError):
        return 0


def _content_kind_from_item_type(item_type: str | None) -> MediaContentKind:
    return _ITEM_TYPE_TO_CONTENT_KIND.get(item_type, MediaContentKind.OTHER)
