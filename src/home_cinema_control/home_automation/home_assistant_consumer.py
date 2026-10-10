from __future__ import annotations

import logging
from urllib.parse import quote, urljoin

import requests

from home_cinema_control.notifications.models import UpdateNotification
from home_cinema_control.playback.events import PlaybackEvent

logger = logging.getLogger(__name__)


class HomeAssistantWebhookClient:

    def __init__(
        self,
        *,
        base_url: str,
        webhook_id: str,
        timeout_seconds: float = 3.0,
        http_session=None,
    ) -> None:
        self._url = _webhook_url(base_url, webhook_id)
        self._timeout_seconds = timeout_seconds
        self._http_session = http_session or requests.Session()

    def send(self, payload: dict) -> None:
        response = self._http_session.post(
            self._url,
            json=payload,
            timeout=self._timeout_seconds,
        )
        response.raise_for_status()

    def send_update(self, notification: UpdateNotification) -> None:
        self.send(
            {
                "event": "hcc_update_available",
                "current_version": notification.current_version,
                "latest_version": notification.latest_version,
                "release_url": notification.release_url,
            }
        )
        logger.info(
            "Home Assistant update notification delivered | current=%s | latest=%s",
            notification.current_version,
            notification.latest_version,
        )


class HomeAssistantPlaybackConsumer:
    name = "home_assistant_playback"

    def __init__(self, client: HomeAssistantWebhookClient) -> None:
        self._client = client

    def consume(self, event: PlaybackEvent) -> None:
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
        self._client.send_update(notification)


def _webhook_url(base_url: str, webhook_id: str) -> str:
    root = base_url.rstrip("/") + "/"
    return urljoin(root, f"api/webhook/{quote(webhook_id, safe='')}")
