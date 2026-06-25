from __future__ import annotations

from home_cinema_control.media_servers.common.playback_event_publisher import (
    PLAYBACK_PROGRESS_INTERVAL_SECONDS,
    MediaServerPlaybackEventPublisher,
)
from home_cinema_control.media_servers.jellyfin.playback_mapper import (
    JellyfinPlaybackPayloadMapper,
)
from home_cinema_control.playback.notification_sender import (
    send_stop_with_delivery_reliability,
    send_with_delivery_reliability,
)


class JellyfinPlaybackEventPublisher(MediaServerPlaybackEventPublisher):
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
            provider_name="Jellyfin",
            bridge_session_id=bridge_session_id,
            context=context,
            payload_mapper=JellyfinPlaybackPayloadMapper(
                bridge_session_id=bridge_session_id,
                context=context,
            ),
            progress_interval_seconds=progress_interval_seconds,
        )

    def _stop_stale_source_client_session(self) -> None:
        """Clear Jellyfin's remote-control screen after OPPO-driven stop.

        Jellyfin Web handles a remote Playstate Stop by forwarding Stop to the
        currently selected player. When that selected player is HCC, this can
        loop the stop command back to the bridge without closing the web/app's
        remote-control screen. Sending Back after Stop exits that screen on the
        source client; the stopped lifecycle report already preserves resume
        position server-side.
        """
        session_id = self.context.source_client_session_id
        send_stop_with_delivery_reliability(
            lambda target_session_id: self._client.stop_session_playback(
                target_session_id, {"Command": "Stop"}
            ),
            session_id,
        )
        send_with_delivery_reliability(
            lambda target_session_id: self._client.send_general_command(
                target_session_id, "Back"
            ),
            session_id,
            command_name="Back",
        )
