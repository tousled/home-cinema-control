from __future__ import annotations

import logging
from typing import Sequence

import requests

from home_cinema_control.telemetry.events import TelemetryPayload

logger = logging.getLogger(__name__)


class TelemetryClient:
    def __init__(self, *, http_client=requests, timeout_seconds: float = 2.0) -> None:
        self._http_client = http_client
        self._timeout_seconds = timeout_seconds

    def send(self, endpoint_url: str, payloads: Sequence[TelemetryPayload]) -> bool:
        if not payloads:
            return True

        body = _serialize_payloads(payloads)
        try:
            response = self._http_client.post(
                endpoint_url,
                json=body,
                timeout=self._timeout_seconds,
            )
            if response.status_code >= 400:
                logger.warning(
                    "Telemetry send failed with HTTP status %s",
                    response.status_code,
                )
                return False
            return True
        except requests.RequestException:
            logger.warning("Telemetry send failed; event will be retried later.")
            return False


def _serialize_payloads(payloads: Sequence[TelemetryPayload]):
    items = [payload.model_dump(mode="json") for payload in payloads]
    if len(items) == 1:
        return items[0]
    return items
