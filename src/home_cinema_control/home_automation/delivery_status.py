from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from threading import Lock


@dataclass(frozen=True)
class HomeAssistantDeliverySnapshot:
    status: str
    last_event: str | None = None
    last_attempt_at: str | None = None
    detail: str | None = None

    def to_dict(self) -> dict[str, str | None]:
        return {
            "status": self.status,
            "last_event": self.last_event,
            "last_attempt_at": self.last_attempt_at,
            "detail": self.detail,
        }


class HomeAssistantDeliveryStatus:
    """Status of the latest real Home Assistant delivery."""

    def __init__(self, store=None, configuration_fingerprint: str | None = None) -> None:
        self._store = store
        self._configuration_fingerprint = configuration_fingerprint
        self._snapshot = (
            store.load(configuration_fingerprint) if store is not None else None
        ) or HomeAssistantDeliverySnapshot(status="pending")
        self._lock = Lock()

    def mark_delivered(self, event_name: str) -> None:
        self._set(
            status="delivered",
            event_name=event_name,
            detail=None,
        )

    def mark_failed(self, event_name: str, detail: str) -> None:
        self._set(
            status="failed",
            event_name=event_name,
            detail=detail,
        )

    def snapshot(self) -> dict[str, str | None]:
        with self._lock:
            return self._snapshot.to_dict()

    def _set(self, *, status: str, event_name: str, detail: str | None) -> None:
        snapshot = HomeAssistantDeliverySnapshot(
            status=status,
            last_event=event_name,
            last_attempt_at=_now_iso(),
            detail=detail,
        )
        with self._lock:
            self._snapshot = snapshot
        if self._store is not None:
            self._store.save(snapshot, self._configuration_fingerprint)


def home_assistant_configuration_fingerprint(base_url: str, webhook_id: str) -> str:
    """Return a non-reversible identity for one Home Assistant configuration."""
    canonical = f"{base_url.strip().rstrip('/')}\x00{webhook_id.strip()}"
    return sha256(canonical.encode("utf-8")).hexdigest()


def _now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
