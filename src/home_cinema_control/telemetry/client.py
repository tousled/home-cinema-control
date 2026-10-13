from __future__ import annotations

import logging
from typing import Sequence

import requests

from home_cinema_control.telemetry.events import TelemetryPayload

logger = logging.getLogger(__name__)

_PING_PATH = "/api/v1/telemetry/ping"
_EVENT_PATH = "/api/v1/telemetry/event"
_EVENT_SCHEMA_VERSION = 2

_EVENT_TYPE_MAP: dict[str, str] = {
    "install_opt_in": "install_opt_in",
    "app_started": "app_started",
    "playback_attempted": "playback_attempted",
    "playback_rejected": "playback_rejected",
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
    attempt_id = _safe_correlation_id(payload.event.get("attempt_id"))
    if payload.event_name == "playback_failed":
        attributes["component"] = str(payload.event.get("component", "system"))
        error_code = str(payload.event.get("error_code") or "").strip()
        if error_code:
            attributes["error_code"] = error_code
    elif payload.event_name == "playback_rejected":
        attributes["component"] = str(payload.event.get("component", "system"))
        provider = str(payload.event.get("provider") or "").strip()
        if provider:
            attributes["provider"] = provider
        error_code = str(payload.event.get("error_code") or "").strip()
        if error_code:
            attributes["error_code"] = error_code
    elif payload.event_name == "roadmap_interest_submitted":
        interests = payload.event.get("interests", [])
        attributes["interests"] = ",".join(str(i) for i in interests)
    elif payload.event_name == "playback_started":
        startup_metrics = payload.event.get("startup_metrics")
        if isinstance(startup_metrics, dict):
            for metric_name, attribute_name in _STARTUP_ATTRIBUTE_NAMES.items():
                value = startup_metrics.get(metric_name)
                if isinstance(value, (str, int)) and not isinstance(value, bool):
                    attributes[attribute_name] = value
    return {
        "event_id": payload.event_id,
        "schema_version": _EVENT_SCHEMA_VERSION,
        "instance_id": payload.installation_id,
        "event_type": event_type,
        "hcc_version": payload.hcc_version,
        "install_type": "docker" if payload.deployment.docker else "native",
        "attempt_id": attempt_id,
        "attributes": attributes,
    }


def _safe_correlation_id(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    value = value.strip()
    return value[:80] if value else None


_STARTUP_ATTRIBUTE_NAMES = {
    "schema_version": "startup_schema_version",
    "strategy": "startup_strategy",
    "total_ms": "startup_total_ms",
    "media_prepare_ms": "startup_media_prepare_ms",
    "tv_prepare_ms": "startup_tv_prepare_ms",
    "av_prepare_ms": "startup_av_prepare_ms",
    "oppo_prepare_ms": "startup_oppo_prepare_ms",
    "oppo_commit_ms": "startup_oppo_commit_ms",
    "oppo_confirm_ms": "startup_oppo_confirm_ms",
    "post_start_ms": "startup_post_start_ms",
}
