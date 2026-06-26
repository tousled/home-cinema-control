from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class JellyfinPlaybackPayloadMapper:
    """Outbound mapper: HCC playback context -> Jellyfin playback payloads."""

    bridge_session_id: str
    context: object

    def lifecycle_payload(
        self,
        *,
        position_ticks: int,
        runtime_ticks: int = 0,
        is_paused: bool = False,
        is_muted: bool = False,
        audio_track_id: int,
        subtitle_track_id: int,
    ) -> dict:
        payload = {
            "QueueableMediaTypes": ["Video"],
            "CanSeek": True,
            "ItemId": self.context.media_library_item_id,
            "SessionId": self.bridge_session_id,
            "MediaSourceId": self.context.media_source_file_id,
            "AudioStreamIndex": audio_track_id,
            "SubtitleStreamIndex": subtitle_track_id,
            "IsPaused": is_paused,
            "IsMuted": is_muted,
            "PositionTicks": position_ticks,
            "PlayMethod": "DirectPlay",
            "PlaySessionId": self.context.media_server_playback_id,
            "RepeatMode": "RepeatNone",
        }
        if runtime_ticks > 0:
            payload["RunTimeTicks"] = runtime_ticks
        return payload

    def restore_resume_position_payload(self, *, position_ticks: int) -> dict:
        return {
            "ItemId": self.context.media_library_item_id,
            "PlaybackPositionTicks": position_ticks,
            "Played": False,
        }
