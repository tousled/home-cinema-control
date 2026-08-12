from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from home_cinema_control.playback.intent import PlaybackIntent
from home_cinema_control.playback.time_units import TICKS_PER_SECOND


def build_playback_intent_from_play_command(
    data: dict[str, Any],
    *,
    load_item_info: Callable[[str, str], dict[str, Any]],
) -> PlaybackIntent | None:
    if data.get("PlayCommand") != "PlayNow":
        return None

    item_id = _requested_item_id(data)
    controlling_user_id = data.get("ControllingUserId", "")
    item_info = load_item_info(controlling_user_id, item_id)
    if _is_theme_audio_item(item_info):
        logging.info("Ignoring Jellyfin theme audio play command | item_id=%s", item_id)
        return None

    start_position_ticks = data.get("StartPositionTicks")
    if start_position_ticks is None:
        start_position_ticks = data.get("SavedPlaybackPositionTicks")
    if start_position_ticks is None or int(start_position_ticks) < 0:
        start_position_ticks = int(
            item_info.get("UserData", {}).get("PlaybackPositionTicks", 0)
        )

    return PlaybackIntent(
        media_item_id=item_id,
        media_source_id=data.get("MediaSourceId", ""),
        source_user_id=controlling_user_id,
        source_client_session_id=data.get("SessionID"),
        source_device_id=data.get("Device_Id", "") or data.get("DeviceId", ""),
        source_device_name=data.get("DeviceName", ""),
        start_position_seconds=int(start_position_ticks) // TICKS_PER_SECOND,
        selected_audio_track_id=int(data.get("AudioStreamIndex", 1)),
        selected_subtitle_track_id=int(data.get("SubtitleStreamIndex", -1)),
    )


def parse_playback_request_payload(
    data: dict[str, Any],
    *,
    load_item_info: Callable[[str, str], dict[str, Any]],
) -> dict[str, Any]:
    item_id = _requested_item_id(data)
    controlling_user_id = data.get("ControllingUserId", "")

    start_position_ticks = data.get("StartPositionTicks")
    if start_position_ticks is None:
        start_position_ticks = data.get("SavedPlaybackPositionTicks")
    if start_position_ticks is None:
        start_position_ticks = -1
    start_position_ticks = int(start_position_ticks)

    if start_position_ticks < 0:
        item_info = load_item_info(controlling_user_id, item_id)
        start_position_ticks = int(
            item_info.get("UserData", {}).get("PlaybackPositionTicks", 0)
        )

    params = {
        "item_id": item_id,
        "auto_resume": start_position_ticks,
        "media_source_id": data.get("MediaSourceId", ""),
        "subtitle_stream_index": data.get("SubtitleStreamIndex", -1),
        "audio_stream_index": data.get("AudioStreamIndex", 1),
        "ControllingUserId": controlling_user_id,
        "Session_id": data.get("SessionID") or data.get("Id"),
        "play_session_id": data.get("PlaySessionId", ""),
        "DeviceName": data.get("DeviceName", ""),
        "Device_Id": data.get("Device_Id", "") or data.get("DeviceId", ""),
    }

    logging.info(
        "Jellyfin playback params | item_id=%s | auto_resume=%s | "
        "media_source_id=%s | audio=%s | subtitle=%s | device=%s",
        params.get("item_id"),
        params.get("auto_resume"),
        params.get("media_source_id"),
        params.get("audio_stream_index"),
        params.get("subtitle_stream_index"),
        params.get("DeviceName"),
    )

    return params


def _requested_item_id(data: dict[str, Any]) -> str:
    item_ids = data["ItemIds"]
    start_index = int(data.get("StartIndex", 0))

    if isinstance(item_ids, list):
        if 0 <= start_index < len(item_ids):
            return str(item_ids[start_index])
        return str(item_ids[0])

    return str(item_ids)


def _is_theme_audio_item(item_info: dict[str, Any] | None) -> bool:
    item_info = item_info or {}
    item_path = str(item_info.get("Path") or "").lower()
    item_name = str(item_info.get("Name") or "").lower()
    item_type = str(item_info.get("Type") or "").lower()
    container = str(item_info.get("Container") or "").lower()
    return (
        _path_basename(item_path) == "theme.mp3"
        or (item_name == "theme" and item_type == "audio" and container == "mp3")
    )


def _path_basename(path: str) -> str:
    return path.replace("\\", "/").rsplit("/", 1)[-1]
