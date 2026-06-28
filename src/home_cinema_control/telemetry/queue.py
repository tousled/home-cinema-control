from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from home_cinema_control.telemetry.events import TelemetryPayload


class TelemetryQueue:
    def __init__(
        self,
        queue_file: str | Path,
        *,
        max_events: int = 100,
        max_age_days: int = 7,
    ) -> None:
        self._queue_file = Path(queue_file)
        self._max_events = max(0, int(max_events))
        self._max_age = timedelta(days=max(0, int(max_age_days)))

    def load(self) -> list[TelemetryPayload]:
        raw_items = self._read_raw_items()
        payloads = []
        for item in raw_items:
            try:
                payloads.append(TelemetryPayload.model_validate(item))
            except ValidationError:
                continue
        return self._prune(payloads)

    def enqueue(self, payload: TelemetryPayload) -> None:
        payloads = self.load()
        payloads.append(payload)
        self.replace(payloads)

    def replace(self, payloads: list[TelemetryPayload]) -> None:
        pruned = self._prune(payloads)
        self._queue_file.parent.mkdir(parents=True, exist_ok=True)
        self._queue_file.write_text(
            json.dumps(
                [payload.model_dump(mode="json") for payload in pruned],
                indent=2,
                sort_keys=True,
            ),
            encoding="utf-8",
        )

    def clear(self) -> None:
        try:
            self._queue_file.unlink()
        except FileNotFoundError:
            pass

    def count(self) -> int:
        return len(self.load())

    def _read_raw_items(self) -> list[dict[str, Any]]:
        try:
            data = json.loads(self._queue_file.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            return []

        if not isinstance(data, list):
            return []
        return [item for item in data if isinstance(item, dict)]

    def _prune(self, payloads: list[TelemetryPayload]) -> list[TelemetryPayload]:
        now = datetime.now(timezone.utc)
        fresh = [payload for payload in payloads if _is_fresh(payload, now, self._max_age)]
        if self._max_events == 0:
            return []
        return fresh[-self._max_events :]


def _is_fresh(payload: TelemetryPayload, now: datetime, max_age: timedelta) -> bool:
    try:
        occurred_at = datetime.fromisoformat(payload.occurred_at)
    except ValueError:
        return False
    if occurred_at.tzinfo is None:
        occurred_at = occurred_at.replace(tzinfo=timezone.utc)
    return now - occurred_at <= max_age
