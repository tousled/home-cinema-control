from __future__ import annotations

from pathlib import Path
from typing import Any

from home_cinema_control.config.manager import active_media_server_config
from home_cinema_control.config.models import HccConfig
from home_cinema_control.telemetry.events import (
    TELEMETRY_SCHEMA_VERSION,
    RoadmapInterest,
    TelemetryDeployment,
    TelemetryEventName,
    TelemetryFailureComponent,
    TelemetryPayload,
    TelemetryProductSnapshot,
    new_event_id,
)


_UNKNOWN = "unknown"
_NONE = "none"

_TV_MODEL_LABELS = {
    "lg": ("lg", "webos"),
    "android_google_tv": ("android", "google", "bravia", "sony", "philips"),
    "scripts": ("script", "scripts"),
}

_AV_MODEL_LABELS = {
    "denon": ("denon",),
    "marantz": ("marantz",),
    "nad": ("nad",),
    "onkyo": ("onkyo",),
    "yamaha": ("yamaha",),
    "scripts": ("script", "scripts"),
}

_FAILURE_COMPONENTS: set[str] = set(TelemetryFailureComponent.__args__)
_ROADMAP_INTERESTS: set[str] = set(RoadmapInterest.__args__)


def build_telemetry_payload(
    config: dict[str, Any] | HccConfig,
    event_name: TelemetryEventName,
    *,
    event: dict[str, Any] | None = None,
    event_id: str | None = None,
    occurred_at: str | None = None,
) -> TelemetryPayload:
    validated = config if isinstance(config, HccConfig) else HccConfig.model_validate(config)
    telemetry = validated.telemetry
    if not telemetry.installation_id:
        raise ValueError("Telemetry installation_id is required to build a payload.")

    payload = TelemetryPayload(
        schema_version=TELEMETRY_SCHEMA_VERSION,
        event_name=event_name,
        event_id=event_id or new_event_id(),
        installation_id=telemetry.installation_id,
        hcc_version=str((validated.model_extra or {}).get("Version") or "unknown"),
        language=validated.app.language,
        deployment=TelemetryDeployment(docker=Path("/.dockerenv").exists()),
        product=build_product_snapshot(validated),
        event=_normalize_event(event_name, event or {}),
    )
    if occurred_at is not None:
        payload.occurred_at = occurred_at
    return payload


def build_product_snapshot(config: HccConfig) -> TelemetryProductSnapshot:
    active_provider = active_media_server_config(config)
    protocols = {
        str(mapping.protocol or "").strip().lower()
        for mapping in active_provider.playback.path_mappings
    }

    return TelemetryProductSnapshot(
        media_server_provider=str(config.media_servers.active),
        media_server_configured=bool(
            active_provider.server_url and active_provider.access_token
        ),
        media_player="oppo",
        media_player_configured=bool(config.oppo.ip),
        tv_enabled=config.tv.enabled,
        tv_model=_normalize_model(config.tv.model, _TV_MODEL_LABELS, enabled=config.tv.enabled),
        av_enabled=config.av.enabled,
        av_model=_normalize_model(config.av.model, _AV_MODEL_LABELS, enabled=config.av.enabled),
        nfs_enabled="nfs" in protocols,
        smb_enabled=bool({"smb", "cifs"} & protocols) or config.oppo.use_smb,
    )


def _normalize_model(
    value: str,
    labels: dict[str, tuple[str, ...]],
    *,
    enabled: bool,
) -> str:
    if not enabled:
        return _NONE

    normalized = str(value or "").strip().lower()
    if not normalized:
        return _UNKNOWN

    for label, needles in labels.items():
        if label == "scripts" and normalized in needles:
            return label
        if label != "scripts" and any(needle in normalized for needle in needles):
            return label
    return _UNKNOWN


def _normalize_event(event_name: str, event: dict[str, Any]) -> dict[str, Any]:
    if event_name == "playback_finished":
        return {"result": "finished"}
    if event_name == "playback_failed":
        component = str(event.get("component") or "system")
        if component not in _FAILURE_COMPONENTS:
            component = "system"
        result: dict[str, Any] = {"result": "failed", "component": component}
        code = str(event.get("code") or "").strip().upper()
        if code:
            result["error_code"] = code
        return result
    if event_name == "roadmap_interest_submitted":
        submitted = event.get("interests") or []
        interests = []
        for interest in submitted:
            interest_id = str(interest)
            if interest_id in _ROADMAP_INTERESTS and interest_id not in interests:
                interests.append(interest_id)
        return {"interests": interests}
    return {}
