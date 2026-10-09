from __future__ import annotations

from collections.abc import Mapping, Sequence

from home_cinema_control.playback.startup.models import PlayerMediaFileLocation


class PlayerMediaFileLocationError(ValueError):
    pass


def resolve_player_media_file_location(
    *,
    emby_media_path: str,
    playback_file_format: str,
    playback_file_name: str | None = None,
    path_mappings: Sequence[Mapping[str, str]],
) -> PlayerMediaFileLocation:
    player_path, network_protocol = _apply_path_mappings(
        _normalize_path_separators(emby_media_path), path_mappings
    )

    return _parse_player_media_file_location(
        player_path=player_path,
        playback_file_format=playback_file_format,
        playback_file_name=playback_file_name,
        network_protocol=network_protocol,
    )


def _apply_path_mappings(
    media_path: str,
    path_mappings: Sequence[Mapping[str, str]],
) -> tuple[str, str | None]:
    player_path = media_path
    network_protocol = None

    for mapping in path_mappings:
        emby_path = _normalize_path_separators(mapping["source_path"])
        if _path_mapping_matches(player_path, emby_path):
            player_path = _replace_path_prefix(
                player_path,
                emby_path,
                _normalize_path_separators(mapping["player_path"]),
            )
            network_protocol = mapping.get("protocol") or network_protocol

    return player_path, network_protocol


def _normalize_path_separators(path: str) -> str:
    return path.replace("\\\\", "\\").replace("\\", "/")


def _path_mapping_matches(media_path: str, source_path: str) -> bool:
    source_prefix = source_path.rstrip("/")
    return media_path == source_prefix or media_path.startswith(source_prefix + "/")


def _replace_path_prefix(media_path: str, source_path: str, player_path: str) -> str:
    source_prefix = source_path.rstrip("/")
    suffix = media_path[len(source_prefix) :].lstrip("/")
    player_prefix = player_path.rstrip("/")
    return player_prefix if not suffix else f"{player_prefix}/{suffix}"


def _parse_player_media_file_location(
    *,
    player_path: str,
    playback_file_format: str,
    playback_file_name: str | None = None,
    network_protocol: str | None = None,
) -> PlayerMediaFileLocation:
    path_parts = player_path.strip("/").split("/")

    if len(path_parts) < 3:
        raise PlayerMediaFileLocationError(
            f"Player media path must include server, folder and file: {player_path}"
        )

    content_server = path_parts[0]
    content_directory = "/".join(path_parts[1:-1])
    resolved_playback_file_name = playback_file_name or path_parts[-1]

    if not content_server or not content_directory or not resolved_playback_file_name:
        raise PlayerMediaFileLocationError(
            f"Player media path must include server, folder and file: {player_path}"
        )

    if "/" in resolved_playback_file_name or "\\" in resolved_playback_file_name:
        raise PlayerMediaFileLocationError(
            "Playback filename must be a basename, not a path."
        )

    return PlayerMediaFileLocation(
        content_server=content_server,
        content_directory=content_directory,
        playback_file_name=resolved_playback_file_name,
        playback_file_format=playback_file_format,
        network_protocol=network_protocol,
    )
