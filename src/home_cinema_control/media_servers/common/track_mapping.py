from __future__ import annotations

from typing import Any


def source_audio_to_player_index(
    media_streams: list[dict[str, Any]],
    source_track_id: int,
) -> int:
    return _source_track_to_player_index(
        media_streams,
        source_track_id,
        stream_type="Audio",
        default=1,
    )


def source_subtitle_to_player_index(
    media_streams: list[dict[str, Any]],
    source_track_id: int,
) -> int:
    if source_track_id < 0:
        return 0

    return _source_track_to_player_index(
        media_streams,
        source_track_id,
        stream_type="Subtitle",
        default=0,
    )


def player_audio_to_source_track_id(
    media_streams: list[dict[str, Any]],
    player_track_index: int,
) -> int | None:
    return _player_index_to_source_track(
        media_streams,
        player_track_index,
        stream_type="Audio",
    )


def player_subtitle_to_source_track_id(
    media_streams: list[dict[str, Any]],
    player_track_index: int,
) -> int | None:
    if player_track_index == 0:
        return -1

    return _player_index_to_source_track(
        media_streams,
        player_track_index,
        stream_type="Subtitle",
    )


def _source_track_to_player_index(
    media_streams: list[dict[str, Any]],
    source_track_id: int,
    *,
    stream_type: str,
    default: int,
) -> int:
    player_index = 0
    for stream in media_streams:
        if stream.get("Type") != stream_type:
            continue

        player_index += 1
        if int(stream.get("Index", -1)) == source_track_id:
            return player_index

    return default


def _player_index_to_source_track(
    media_streams: list[dict[str, Any]],
    player_track_index: int,
    *,
    stream_type: str,
) -> int | None:
    if player_track_index <= 0:
        return None

    player_index = 0
    for stream in media_streams:
        if stream.get("Type") != stream_type:
            continue

        player_index += 1
        if player_index == player_track_index:
            return int(stream["Index"])

    return None
