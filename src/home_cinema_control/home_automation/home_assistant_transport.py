from __future__ import annotations

from urllib.parse import quote, urljoin

import requests

from home_cinema_control.home_automation.delivery_status import (
    HomeAssistantDeliveryStatus,
)


class HomeAssistantWebhookError(RuntimeError):
    """Safe transport error that never includes the webhook URL or ID."""

    def __init__(self, *, status_code: int | None = None) -> None:
        self.status_code = status_code
        detail = f"status={status_code}" if status_code is not None else "transport_error"
        super().__init__(f"Home Assistant webhook request failed | {detail}")


class HomeAssistantWebhookClient:
    """Deliver application payloads through the configured HA webhook."""

    def __init__(
        self,
        *,
        base_url: str,
        webhook_id: str,
        timeout_seconds: float = 3.0,
        http_session=None,
        delivery_status: HomeAssistantDeliveryStatus | None = None,
    ) -> None:
        self._url = _webhook_url(base_url, webhook_id)
        self._timeout_seconds = timeout_seconds
        self._http_session = http_session or requests.Session()
        self._delivery_status = delivery_status or HomeAssistantDeliveryStatus()

    def send(self, payload: dict) -> None:
        event_name = str(payload.get("event") or "unknown")
        try:
            response = self._http_session.post(
                self._url,
                json=payload,
                timeout=self._timeout_seconds,
            )
            response.raise_for_status()
        except Exception as exc:
            response = getattr(exc, "response", None)
            status_code = getattr(response, "status_code", None)
            detail = f"status={status_code}" if status_code is not None else "transport_error"
            self._delivery_status.mark_failed(event_name, detail)
            raise HomeAssistantWebhookError(status_code=status_code) from None
        self._delivery_status.mark_delivered(event_name)

def _webhook_url(base_url: str, webhook_id: str) -> str:
    root = base_url.rstrip("/") + "/"
    return urljoin(root, f"api/webhook/{quote(webhook_id, safe='')}")
