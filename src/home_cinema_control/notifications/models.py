from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import uuid4


@dataclass(frozen=True)
class UpdateNotification:
    current_version: str
    latest_version: str
    release_url: str
    title: str
    message: str


@dataclass(frozen=True)
class UpdateAvailableEvent:
    notification: UpdateNotification
    event_id: str = ""
    occurred_at: datetime | None = None
    event_type: str = "hcc_update_available"

    def __post_init__(self) -> None:
        if not self.event_id:
            object.__setattr__(self, "event_id", uuid4().hex)
        if self.occurred_at is None:
            object.__setattr__(self, "occurred_at", datetime.now(timezone.utc))

