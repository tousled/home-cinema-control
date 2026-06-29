from __future__ import annotations

import logging
from typing import Sequence

import requests

from home_cinema_control.telemetry.events import TelemetryPayload

logger = logging.getLogger(__name__)

_PING_PATH = "/api/v1/telemetry/ping"
_EVENT_PATH = "/api/v1/telemetry/event"

_EVENT_TYPE_MAP: dict[str, str] = {
    "install_opt_in": "install_opt_in",
    "app_started": "app_started",
    "playback_started": "playback_started",
    "playback_finished": "playback_finished",
    "playback_failed": "playback_failed",
    "roadmap_interest_submitted": "roadmap_interest_submitted",
}


class TelemetryClient:
    def __init__(self, *, http_client=requests, timeout_seconds: float = 2.0) -> None:
        self._http_client = http_client
        self._timeout_seconds = timeout_seconds

    def send(
        self,
        base_url: str,
        ingest_key: str,
        payloads: Sequence[TelemetryPayload],
    ) -> bool:
        if not base_url or not ingest_key:
            return False
        if not payloads:
            return True

        headers = {"X-HCC-Telemetry-Key": ingest_key}
        success = True
        for payload in payloads:
            if payload.event_name == "heartbeat":
                ok = self._post(base_url.rstrip("/") + _PING_PATH, _to_ping_body(payload), headers)
            else:
                ok = self._post(base_url.rstrip("/") + _EVENT_PATH, _to_event_body(payload), headers)
            if not ok:
                success = False
        return success

    def _post(self, url: str, body: dict, headers: dict) -> bool:
        try:
            response = self._http_client.post(
                url,
                json=body,
                headers=headers,
                timeout=self._timeout_seconds,
            )
            if response.status_code >= 400:
                logger.warning("Telemetry send failed with HTTP status %s", response.status_code)
                return False
            return True
        except requests.RequestException:
            logger.warning("Telemetry send failed; event will be retried later.")
            return False


def _to_ping_body(payload: TelemetryPayload) -> dict:
    features: list[str] = []
    if payload.product.nfs_enabled:
        features.append("nfs")
    if payload.product.smb_enabled:
        features.append("smb")
    if payload.product.tv_enabled:
        features.append("tv")
    if payload.product.av_enabled:
        features.append("av")

    return {
        "instance_id": payload.installation_id,
        "hcc_version": payload.hcc_version,
        "install_type": "docker" if payload.deployment.docker else "native",
        "media_server_types": (
            [payload.product.media_server_provider]
            if payload.product.media_server_configured
            else []
        ),
        "playback_targets": (
            [payload.product.media_player]
            if payload.product.media_player_configured
            else []
        ),
        "tv_providers": (
            [payload.product.tv_model]
            if payload.product.tv_enabled
            and payload.product.tv_model not in ("none", "unknown", "")
            else []
        ),
        "features_enabled": features,
        "setup_completed": (
            payload.product.media_server_configured and payload.product.media_player_configured
        ),
    }


def _to_event_body(payload: TelemetryPayload) -> dict:
    event_type = _EVENT_TYPE_MAP.get(payload.event_name, "app_started")
    attributes: dict[str, str | int | float | bool] = {}
    if payload.event_name == "playback_failed":
        attributes["error_category"] = str(payload.event.get("component", "system"))
    elif payload.event_name == "roadmap_interest_submitted":
        interests = payload.event.get("interests", [])
        attributes["interests"] = ",".join(str(i) for i in interests)
    return {
        "instance_id": payload.installation_id,
        "event_type": event_type,
        "hcc_version": payload.hcc_version,
        "install_type": "docker" if payload.deployment.docker else "native",
        "attributes": attributes,
    }
