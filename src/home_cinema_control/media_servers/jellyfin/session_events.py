from __future__ import annotations

from typing import Any

from home_cinema_control.media_servers.common.models import (
    MediaServerNowPlaying,
    MediaServerSession,
)


def find_monitored_session(
    sessions: list[dict[str, Any]],
    monitored_device_id: str,
) -> MediaServerSession | None:
    """Inbound mapper: Jellyfin Sessions payload -> HCC ``MediaServerSession``."""
    for session in sessions:
        if session.get("DeviceId") == monitored_device_id:
            return _session_from_payload(session)

    return None


def _session_from_payload(session: dict[str, Any]) -> MediaServerSession:
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
        now_playing=mapped_now_playing,
        position_ticks=play_state.get("PositionTicks"),
        media_source_id=play_state.get("MediaSourceId", "") or "",
        audio_stream_index=int(play_state.get("AudioStreamIndex", 1)),
        subtitle_stream_index=int(play_state.get("SubtitleStreamIndex", -1)),
    )
