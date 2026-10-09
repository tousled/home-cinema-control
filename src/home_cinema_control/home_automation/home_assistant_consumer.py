from __future__ import annotations

import logging
from urllib.parse import quote, urljoin

import requests

from home_cinema_control.playback.events import PlaybackEvent

logger = logging.getLogger(__name__)


class HomeAssistantWebhookConsumer:
    name = "home_assistant"

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

    def consume(self, event: PlaybackEvent) -> None:
        response = self._http_session.post(
            self._url,
            json={
                "event": event.event_type.value,
                "event_id": event.event_id,
                "session_id": event.session_id,
                "media_type": event.media_type,
                "title": event.title,
                "source": event.source,
                "player": event.player,
            },
            timeout=self._timeout_seconds,
        )
        response.raise_for_status()
        logger.info(
            "Home Assistant playback event delivered | event=%s | event_id=%s | "
            "session_id=%s",
            event.event_type,
            event.event_id,
            event.session_id,
        )


def _webhook_url(base_url: str, webhook_id: str) -> str:
    root = base_url.rstrip("/") + "/"
    return urljoin(root, f"api/webhook/{quote(webhook_id, safe='')}")
