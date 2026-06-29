from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable
from uuid import uuid4

from home_cinema_control.config.models import HccConfig, TelemetryConfig
from home_cinema_control.telemetry.client import TelemetryClient
from home_cinema_control.telemetry.events import TelemetryEventName
from home_cinema_control.telemetry.queue import TelemetryQueue
from home_cinema_control.telemetry.snapshot import build_telemetry_payload

logger = logging.getLogger(__name__)


class TelemetryService:
    def __init__(
        self,
        *,
        config_file: str | Path,
        load_config: Callable[[], dict[str, Any]],
        save_config: Callable[[dict[str, Any]], None],
        client: TelemetryClient | None = None,
    ) -> None:
        self._config_file = Path(config_file)
        self._load_config = load_config
        self._save_config = save_config
        self._client = client or TelemetryClient()

    def status(self) -> dict[str, Any]:
        config = HccConfig.model_validate(self._load_config())
        queue = self._queue(config.telemetry)
        return {
            "enabled": config.telemetry.enabled,
            "installation_id_configured": bool(config.telemetry.installation_id),
            "ingest_key_configured": bool(_effective_ingest_key(config.telemetry)),
            "consent_prompted": config.telemetry.consent_prompted,
            "endpoint_url": _effective_endpoint_url(config.telemetry),
            "schema_version": config.telemetry.schema_version,
            "last_heartbeat_at": config.telemetry.last_heartbeat_at,
            "queue_count": queue.count(),
        }

    def enable(self) -> dict[str, Any]:
        config = HccConfig.model_validate(self._load_config())
        telemetry = config.telemetry
        installation_id = telemetry.installation_id or str(uuid4())
        updated = config.model_copy(
            update={
                "telemetry": telemetry.model_copy(
                    update={
                        "enabled": True,
                        "installation_id": installation_id,
                        "consent_prompted": True,
                    }
                )
            }
        )
        self._save_config(updated.model_dump())
        self.emit("install_opt_in", config=updated)
        return self.status()

    def dismiss_prompt(self) -> dict[str, Any]:
        config = HccConfig.model_validate(self._load_config())
        updated = config.model_copy(
            update={
                "telemetry": config.telemetry.model_copy(
                    update={"consent_prompted": True}
                )
            }
        )
        self._save_config(updated.model_dump())
        return self.status()

    def disable(self, *, reset_identity: bool = False) -> dict[str, Any]:
        config = HccConfig.model_validate(self._load_config())
        telemetry = config.telemetry.model_copy(
            update={
                "enabled": False,
                "installation_id": "" if reset_identity else config.telemetry.installation_id,
            }
        )
        updated = config.model_copy(update={"telemetry": telemetry})
        self._queue(config.telemetry).clear()
        self._save_config(updated.model_dump())
        return self.status()

    def reset_installation_id(self) -> dict[str, Any]:
        config = HccConfig.model_validate(self._load_config())
        telemetry = config.telemetry.model_copy(update={"installation_id": str(uuid4())})
        updated = config.model_copy(update={"telemetry": telemetry})
        self._queue(config.telemetry).clear()
        self._save_config(updated.model_dump())
        return self.status()

    def clear_queue(self) -> dict[str, Any]:
        config = HccConfig.model_validate(self._load_config())
        self._queue(config.telemetry).clear()
        return self.status()

    def emit(
        self,
        event_name: TelemetryEventName,
        *,
        event: dict[str, Any] | None = None,
        config: HccConfig | dict[str, Any] | None = None,
    ) -> bool:
        validated = self._validated_config(config)
        if not validated.telemetry.enabled:
            return False
        if not validated.telemetry.installation_id:
            return False

        payload = build_telemetry_payload(validated, event_name, event=event)
        queue = self._queue(validated.telemetry)
        self._flush_queue(validated, queue)
        endpoint_url = _effective_endpoint_url(validated.telemetry)
        ingest_key = _effective_ingest_key(validated.telemetry)
        if self._client.send(endpoint_url, ingest_key, [payload]):
            return True
        queue.enqueue(payload)
        return False

    def emit_heartbeat_if_due(self) -> bool:
        config = HccConfig.model_validate(self._load_config())
        if not config.telemetry.enabled:
            return False
        if not _heartbeat_due(config.telemetry.last_heartbeat_at):
            return False

        emitted = self.emit("heartbeat", config=config)
        updated_config = HccConfig.model_validate(self._load_config())
        updated = updated_config.model_copy(
            update={
                "telemetry": updated_config.telemetry.model_copy(
                    update={"last_heartbeat_at": _now_iso()}
                )
            }
        )
        self._save_config(updated.model_dump())
        return emitted

    def _flush_queue(self, config: HccConfig, queue: TelemetryQueue) -> bool:
        queued = queue.load()
        if not queued:
            return True
        endpoint_url = _effective_endpoint_url(config.telemetry)
        ingest_key = _effective_ingest_key(config.telemetry)
        if self._client.send(endpoint_url, ingest_key, queued):
            queue.clear()
            return True
        queue.replace(queued)
        return False

    def _queue(self, telemetry: TelemetryConfig) -> TelemetryQueue:
        return TelemetryQueue(
            self._config_file.with_name("telemetry_queue.json"),
            max_events=telemetry.queue_max_events,
            max_age_days=telemetry.queue_max_age_days,
        )

    def _validated_config(self, config: HccConfig | dict[str, Any] | None) -> HccConfig:
        if config is None:
            return HccConfig.model_validate(self._load_config())
        if isinstance(config, HccConfig):
            return config
        return HccConfig.model_validate(config)


def _heartbeat_due(last_heartbeat_at: str) -> bool:
    if not last_heartbeat_at:
        return True
    try:
        last = datetime.fromisoformat(last_heartbeat_at)
    except ValueError:
        return True
    if last.tzinfo is None:
        last = last.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc) - last >= timedelta(hours=24)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _effective_endpoint_url(telemetry: TelemetryConfig) -> str:
    return os.environ.get("HCC_TELEMETRY_ENDPOINT_URL") or telemetry.endpoint_url


def _effective_ingest_key(telemetry: TelemetryConfig) -> str:
    return os.environ.get("HCC_TELEMETRY_INGEST_KEY") or telemetry.ingest_key
