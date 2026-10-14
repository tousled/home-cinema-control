from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from home_cinema_control.media_servers.common.path_matching import (
    longest_matching_mapping,
    normalize_path,
)
from home_cinema_control.playback.startup.models import PlayerMediaFileLocation


class PlayerMediaFileLocationError(ValueError):
    diagnostic_code = "PATH_RESOLUTION_FAILED"
    diagnostic_details: dict[str, Any] = {}

    def __init__(
        self,
        message: str,
        *,
        diagnostic_code: str = "PATH_RESOLUTION_FAILED",
        diagnostic_details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.diagnostic_code = diagnostic_code
        self.diagnostic_details = diagnostic_details or {}


def resolve_player_media_file_location(
    *,
    emby_media_path: str,
    playback_file_format: str,
    playback_file_name: str | None = None,
    path_mappings: Sequence[Mapping[str, Any]],
) -> PlayerMediaFileLocation:
    player_path, network_protocol = _apply_path_mappings(
        normalize_path(emby_media_path), path_mappings
    )

    return _parse_player_media_file_location(
        player_path=player_path,
        playback_file_format=playback_file_format,
        playback_file_name=playback_file_name,
        network_protocol=network_protocol,
    )


def _apply_path_mappings(
    media_path: str,
    path_mappings: Sequence[Mapping[str, Any]],
) -> tuple[str, str | None]:
    media_path = normalize_path(media_path)
    mapping = longest_matching_mapping(media_path, path_mappings)
    if mapping is None:
        raise PlayerMediaFileLocationError(
            f"No verified path mapping matches media path: {media_path}",
            diagnostic_code="PATH_MAPPING_NOT_FOUND",
            diagnostic_details={"item_path": media_path},
        )

    if mapping.get("verified") is not True:
        source_path = normalize_path(mapping.get("source_path"))
        raise PlayerMediaFileLocationError(
            f"Path mapping is not verified for media path: {source_path}",
            diagnostic_code="PATH_MAPPING_NOT_VERIFIED",
            diagnostic_details={
                "item_path": media_path,
                "source_path": source_path,
            },
        )

    source_path = normalize_path(mapping.get("source_path"))
    player_path = _replace_path_prefix(
        media_path,
        source_path,
        normalize_path(mapping.get("player_path")),
    )
    return player_path, mapping.get("protocol") or None


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
