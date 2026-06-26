from __future__ import annotations

from home_cinema_control.media_servers.common.playback_event_publisher import (
    PLAYBACK_PROGRESS_INTERVAL_SECONDS,
    MediaServerPlaybackEventPublisher,
)
from home_cinema_control.media_servers.emby.playback_mapper import EmbyPlaybackPayloadMapper


class EmbyPlaybackEventPublisher(MediaServerPlaybackEventPublisher):
    def __init__(
        self,
        client,
        *,
        bridge_session_id: str,
            context,
        progress_interval_seconds: int = PLAYBACK_PROGRESS_INTERVAL_SECONDS,
    ) -> None:
        super().__init__(
            client,
            provider_name="Emby",
            bridge_session_id=bridge_session_id,
            context=context,
            payload_mapper=EmbyPlaybackPayloadMapper(
                bridge_session_id=bridge_session_id,
                context=context,
            ),
            progress_interval_seconds=progress_interval_seconds,
        )
