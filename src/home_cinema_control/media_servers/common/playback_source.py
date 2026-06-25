from __future__ import annotations

from dataclasses import dataclass

from home_cinema_control.playback.content_kind import MediaContentKind
from home_cinema_control.playback.time_units import TICKS_PER_SECOND

# Emby and Jellyfin (a fork of Emby) share the same `Type` vocabulary for the
# values relevant here, so providers map through this one table rather than
# each keeping their own copy.
_ITEM_TYPE_TO_CONTENT_KIND = {
    "Movie": MediaContentKind.MOVIE,
    "Episode": MediaContentKind.EPISODE,
    "MusicVideo": MediaContentKind.CONCERT,
    "LiveTvProgram": MediaContentKind.LIVE_TV,
    "Recording": MediaContentKind.LIVE_TV,
    "TvChannel": MediaContentKind.LIVE_TV,
    "LiveTvChannel": MediaContentKind.LIVE_TV,
}


def content_kind_from_item_type(item_type: str | None) -> MediaContentKind:
    return _ITEM_TYPE_TO_CONTENT_KIND.get(item_type, MediaContentKind.OTHER)


@dataclass(frozen=True)
class MediaServerPlaybackSource:
    """The resolved file + metadata for what's actually being played.

    The counterpart to `MediaServerPlaybackContext`: context is the request,
    source is what got resolved. Each provider maps its own raw `Item`/
    `MediaSource` wire dict into this at the adapter edge — policy code reads
    these typed fields and never a provider's own field names.
    """

    path: str
    container: str
    duration_seconds: int
    production_year: int | None
    title: str
    content_kind: MediaContentKind


def find_media_source(item_data: dict, media_source_id: str) -> dict:
    for media_source in item_data.get("MediaSources", []):
        if media_source.get("Id") == media_source_id:
            return media_source

    return item_data


def duration_seconds_from_runtime_ticks(media_source: dict) -> int:
    try:
        return max(0, int(media_source.get("RunTimeTicks", 0)) // TICKS_PER_SECOND)
    except (TypeError, ValueError):
        return 0


def media_server_playback_source_from_item(
    item_data: dict,
    media_source_id: str,
) -> MediaServerPlaybackSource:
    media_source = find_media_source(item_data, media_source_id)

    return MediaServerPlaybackSource(
        path=media_source.get("Path", ""),
        container=media_source.get("Container", ""),
        duration_seconds=duration_seconds_from_runtime_ticks(media_source),
        production_year=item_data.get("ProductionYear"),
        title=item_data.get("Name", ""),
        content_kind=content_kind_from_item_type(item_data.get("Type")),
    )
