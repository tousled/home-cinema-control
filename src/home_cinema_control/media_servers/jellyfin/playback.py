from __future__ import annotations

import logging

from home_cinema_control.media_servers.common.constants import DEVICE_ID
from home_cinema_control.media_servers.common.models import (
    MediaServerSession,
    find_stale_playback_session_ids,
)
from home_cinema_control.media_servers.common.playback_event_publisher import (
    PLAYBACK_PROGRESS_INTERVAL_SECONDS,
    MediaServerPlaybackEventPublisher,
)
from home_cinema_control.media_servers.jellyfin.playback_mapper import (
    JellyfinPlaybackPayloadMapper,
)
from home_cinema_control.media_servers.jellyfin.session_events import session_from_payload
from home_cinema_control.playback.notification_sender import (
    send_stop_with_delivery_reliability,
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

        The stopped lifecycle report already preserves resume position
        server-side; the remote Stop commands are only a best-effort client UI
        cleanup for Jellyfin sessions that may still show HCC playback.
        Playstate Stop signals the stopped state but does not navigate clients
        away from the queue/player screen; GeneralCommand Back does that without
        the Playstate-forwarding side-effect that remote-control mode can trigger.
        """
        for session_id in self._stale_playback_session_ids():
            send_stop_with_delivery_reliability(
                lambda target_session_id: self._client.stop_session_playback(
                    target_session_id, {"Command": "Stop"}
                ),
                session_id,
            )
        self._navigate_user_sessions_back()

    def _navigate_user_sessions_back(self) -> None:
        for session in self._active_user_sessions():
            if session.device_id == DEVICE_ID or not session.client_session_id:
                continue
            try:
                self._client.send_general_command(session.client_session_id, "Back")
            except Exception:
                logging.debug(
                    "Failed to send Back navigation to Jellyfin session | session_id=%s",
                    session.client_session_id,
                )

    def _stale_playback_session_ids(self) -> list[str]:
        mapped_sessions = self._active_user_sessions()
        session_ids = find_stale_playback_session_ids(
            mapped_sessions,
            controlling_user_id=self.context.media_server_user_id,
            media_library_item_id=self.context.media_library_item_id,
            own_device_id=DEVICE_ID,
            source_client_session_id=self.context.source_client_session_id,
        )
        logging.info(
            "Jellyfin stale playback session cleanup targets | sessions=%s | "
            "item_id=%s | source_session_id=%s",
            session_ids,
            self.context.media_library_item_id,
            self.context.source_client_session_id,
        )
        logging.debug(
            "Jellyfin stale playback session candidates | sessions=%s",
            [
                {
                    "session_id": session.client_session_id,
                    "device_id": session.device_id,
                    "device_name": session.device_name,
                    "client_name": session.client_name,
                    "user_id": session.user_id,
                    "item_id": session.now_playing.item_id if session.now_playing else "",
                }
                for session in mapped_sessions
            ],
        )
        return session_ids

    def _active_user_sessions(self) -> list[MediaServerSession]:
        try:
            sessions = self._client.get_sessions_by_user(self.context.media_server_user_id)
            return [
                session_from_payload(session)
                for session in sessions
                if isinstance(session, dict)
            ] if isinstance(sessions, list) else []
        except Exception:
            logging.exception(
                "Unable to resolve Jellyfin stale playback sessions; "
                "falling back to source session only | source_session_id=%s",
                self.context.source_client_session_id,
            )
            return []
