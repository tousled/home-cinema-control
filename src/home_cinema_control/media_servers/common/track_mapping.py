from __future__ import annotations

from home_cinema_control.media_servers.common.media_tracks import (
    MediaTrack,
    MediaTrackKind,
)

def source_audio_to_player_index(
    tracks: list[MediaTrack],
    source_track_id: int,
) -> int:
    return _source_track_to_player_index(
        tracks,
        source_track_id,
        track_kind=MediaTrackKind.AUDIO,
        default=1,
    )


def source_subtitle_to_player_index(
    tracks: list[MediaTrack],
    source_track_id: int,
) -> int:
    if source_track_id < 0:
        return 0

    return _source_track_to_player_index(
        tracks,
        source_track_id,
        track_kind=MediaTrackKind.SUBTITLE,
        default=0,
    )


def player_audio_to_source_track_id(
    tracks: list[MediaTrack],
    player_track_index: int,
) -> int | None:
    return _player_index_to_source_track(
        tracks,
        player_track_index,
        track_kind=MediaTrackKind.AUDIO,
    )


def player_subtitle_to_source_track_id(
    tracks: list[MediaTrack],
    player_track_index: int,
) -> int | None:
    if player_track_index == 0:
        return -1

    return _player_index_to_source_track(
        tracks,
        player_track_index,
        track_kind=MediaTrackKind.SUBTITLE,
    )


def _source_track_to_player_index(
    tracks: list[MediaTrack],
    source_track_id: int,
    *,
    track_kind: MediaTrackKind,
    default: int,
) -> int:
    player_index = 0
    for track in tracks:
        if track.kind != track_kind:
            continue

        player_index += 1
        if track.source_index == source_track_id:
            return player_index

    return default


def _player_index_to_source_track(
    tracks: list[MediaTrack],
    player_track_index: int,
    *,
    track_kind: MediaTrackKind,
) -> int | None:
    if player_track_index <= 0:
        return None

    player_index = 0
    for track in tracks:
        if track.kind != track_kind:
            continue

        player_index += 1
        if player_index == player_track_index:
            return track.source_index

    return None
