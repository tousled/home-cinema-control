from __future__ import annotations

import sqlite3
import threading
from pathlib import Path

from home_cinema_control.home_automation.delivery_status import (
    HomeAssistantDeliverySnapshot,
)


class HomeAssistantDeliveryStatusStore:
    """Persists only the latest safe Home Assistant delivery result."""

    def __init__(self, database_path: str | Path) -> None:
        self._database_path = Path(database_path)
        self._lock = threading.RLock()
        self._initialize()

    def load(
        self,
        configuration_fingerprint: str | None = None,
    ) -> HomeAssistantDeliverySnapshot | None:
        with self._lock, self._connect() as connection:
            row = connection.execute(
                "SELECT status, last_event, last_attempt_at, detail, configuration_fingerprint "
                "FROM home_assistant_delivery_status WHERE id = 1"
            ).fetchone()
        if row is None:
            return None
        if configuration_fingerprint is not None and row[4] != configuration_fingerprint:
            return None
        return HomeAssistantDeliverySnapshot(
            status=row[0],
            last_event=row[1],
            last_attempt_at=row[2],
            detail=row[3],
        )

    def save(
        self,
        snapshot: HomeAssistantDeliverySnapshot,
        configuration_fingerprint: str | None = None,
    ) -> None:
        with self._lock, self._connect() as connection:
            connection.execute(
                """
                INSERT INTO home_assistant_delivery_status(
                    id, status, last_event, last_attempt_at, detail, configuration_fingerprint
                )
                VALUES (1, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    status = excluded.status,
                    last_event = excluded.last_event,
                    last_attempt_at = excluded.last_attempt_at,
                    detail = excluded.detail,
                    configuration_fingerprint = excluded.configuration_fingerprint
                """,
                (
                    snapshot.status,
                    snapshot.last_event,
                    snapshot.last_attempt_at,
                    snapshot.detail,
                    configuration_fingerprint or "",
                ),
            )
            connection.commit()

    def _initialize(self) -> None:
        self._database_path.parent.mkdir(parents=True, exist_ok=True)
        with self._lock, self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS home_assistant_delivery_status (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    status TEXT NOT NULL,
                    last_event TEXT,
                    last_attempt_at TEXT,
                    detail TEXT,
                    configuration_fingerprint TEXT NOT NULL DEFAULT ''
                )
                """
            )
            columns = {
                row[1]
                for row in connection.execute(
                    "PRAGMA table_info(home_assistant_delivery_status)"
                ).fetchall()
            }
            if "configuration_fingerprint" not in columns:
                connection.execute(
                    "ALTER TABLE home_assistant_delivery_status "
                    "ADD COLUMN configuration_fingerprint TEXT NOT NULL DEFAULT ''"
                )
            connection.commit()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._database_path, timeout=5)
