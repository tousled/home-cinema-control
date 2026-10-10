from __future__ import annotations

import logging

from home_cinema_control.home_automation.home_assistant_transport import (
    HomeAssistantWebhookClient,
    HomeAssistantWebhookError,
)
from home_cinema_control.notifications.models import UpdateNotification
from home_cinema_control.playback.events import PlaybackEvent

logger = logging.getLogger(__name__)


class HomeAssistantPlaybackConsumer:
    name = "home_assistant_playback"

    def __init__(self, client: HomeAssistantWebhookClient) -> None:
        self._client = client

    def consume(self, event: PlaybackEvent) -> None:
        try:
            self._client.send(
                {
                    "event": event.event_type.value,
                    "event_id": event.event_id,
                    "session_id": event.session_id,
                    "media_type": event.media_type,
                    "title": event.title,
                    "source": event.source,
                    "player": event.player,
                }
            )
        except HomeAssistantWebhookError as exc:
            logger.warning(
                "Home Assistant playback event delivery failed | event=%s | "
                "event_id=%s | status=%s",
                event.event_type,
                event.event_id,
                exc.status_code or "transport_error",
            )
            return
        logger.info(
            "Home Assistant playback event delivered | event=%s | event_id=%s | "
            "session_id=%s",
            event.event_type,
            event.event_id,
            event.session_id,
        )


class HomeAssistantWebhookConsumer(HomeAssistantPlaybackConsumer):
    """Backward-compatible combined consumer for legacy listener wiring."""

    name = "home_assistant"

    def __init__(
        self,
        *,
        base_url: str,
        webhook_id: str,
        timeout_seconds: float = 3.0,
        http_session=None,
    ) -> None:
        self._client = HomeAssistantWebhookClient(
            base_url=base_url,
            webhook_id=webhook_id,
            timeout_seconds=timeout_seconds,
            http_session=http_session,
        )
        super().__init__(self._client)

    def send_update(self, notification: UpdateNotification) -> None:
        self._client.send(
            {
                "event": "hcc_update_available",
                "current_version": notification.current_version,
                "latest_version": notification.latest_version,
                "release_url": notification.release_url,
            }
        )
