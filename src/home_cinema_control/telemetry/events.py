from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


TELEMETRY_SCHEMA_VERSION = 1

TelemetryEventName = Literal[
    "install_opt_in",
    "app_started",
    "heartbeat",
    "playback_started",
    "playback_finished",
    "playback_failed",
    "roadmap_interest_submitted",
]

TelemetryFailureComponent = Literal[
    "oppo",
    "tv",
    "av",
    "path",
    "media_server",
    "cleanup",
    "system",
]

RoadmapInterest = Literal[
    "plex",
    "android_google_tv",
    "sony_tv",
    "philips_tv",
    "samsung_tv",
    "home_assistant",
    "hue_ambilight",
    "kodi_zdmc",
    "zidoo_dune",
    "oppo_chinoppo_xnoppo",
    "trinnov_altitude",
]


class TelemetryDeployment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    docker: bool = True


class TelemetryProductSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    media_server_provider: str
    media_server_configured: bool
    media_player: str = "oppo"
    media_player_configured: bool
    tv_enabled: bool
    tv_model: str
    av_enabled: bool
    av_model: str
    nfs_enabled: bool
    smb_enabled: bool


class TelemetryPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: int = TELEMETRY_SCHEMA_VERSION
    event_name: TelemetryEventName
    event_id: str = Field(default_factory=lambda: str(uuid4()))
    installation_id: str
    occurred_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    hcc_version: str
    language: str
    deployment: TelemetryDeployment
    product: TelemetryProductSnapshot
    event: dict[str, Any] = Field(default_factory=dict)


def new_event_id() -> str:
    return str(uuid4())
