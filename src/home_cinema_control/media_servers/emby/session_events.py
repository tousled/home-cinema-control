from __future__ import annotations

from typing import Any

from home_cinema_control.media_servers.common.models import (
    MediaServerNowPlaying,
    MediaServerSession,
)


def playback_request_media_item_id(data: dict[str, Any] | None) -> str | None:
    if not data:
        return None

    item_ids = data.get("ItemIds")
    if item_ids is None:
        return None

    if isinstance(item_ids, list):
        if not item_ids:
            return None

        start_index = int(data.get("StartIndex", 0))
        if 0 <= start_index < len(item_ids):
            return str(item_ids[start_index])

        return str(item_ids[0])

    return str(item_ids)


def is_same_media_item_request(
    current_data: dict[str, Any] | None,
    next_data: dict[str, Any] | None,
) -> bool:
    current_item_id = playback_request_media_item_id(current_data)
    next_item_id = playback_request_media_item_id(next_data)
    return current_item_id is not None and current_item_id == next_item_id


def find_monitored_session(
    sessions: list[dict[str, Any]],
    monitored_device_id: str,
) -> MediaServerSession | None:
    """Inbound mapper: Emby Sessions payload -> HCC ``MediaServerSession``."""
    for session in sessions:
        if session.get("DeviceId") == monitored_device_id:
            return session_from_payload(session)

    return None


def session_from_payload(session: dict[str, Any]) -> MediaServerSession:
    now_playing = session.get("NowPlayingItem")
    play_state = session.get("PlayState") or {}

    mapped_now_playing = None
    if now_playing:
        mapped_now_playing = MediaServerNowPlaying(
            item_id=str(now_playing.get("Id", "")),
            name=now_playing.get("Name", "") or "",
            path=now_playing.get("Path", "") or "",
            item_type=now_playing.get("Type"),
            container=now_playing.get("Container"),
            video_type=now_playing.get("VideoType"),
        )

    return MediaServerSession(
        device_id=session.get("DeviceId", "") or "",
        device_name=session.get("DeviceName", "") or "",
        user_id=session.get("UserId", "") or "",
        client_session_id=session.get("Id"),
        last_activity_at=session.get("LastActivityDate", "") or "",
        now_playing=mapped_now_playing,
        position_ticks=play_state.get("PositionTicks"),
        media_source_id=play_state.get("MediaSourceId", "") or "",
        audio_stream_index=int(play_state.get("AudioStreamIndex", 1)),
        subtitle_stream_index=int(play_state.get("SubtitleStreamIndex", -1)),
    )
