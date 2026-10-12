from __future__ import annotations

import sqlite3
import threading
from pathlib import Path


class NotificationStateStore:
    """Persist the last successfully delivered release for each local channel."""

    def __init__(self, database_path: str | Path) -> None:
        self._database_path = Path(database_path)
        self._lock = threading.RLock()
        self._initialize()

    def last_notified_version(self, channel: str) -> str | None:
        with self._lock, self._connect() as connection:
            row = connection.execute(
                "SELECT version FROM notification_delivery WHERE channel = ?",
                (channel,),
            ).fetchone()
        return row[0] if row else None

    def mark_notified(self, channel: str, version: str) -> None:
        with self._lock, self._connect() as connection:
            connection.execute(
                """
                INSERT INTO notification_delivery(channel, version)
                VALUES (?, ?)
                ON CONFLICT(channel) DO UPDATE SET version = excluded.version
                """,
                (channel, version),
            )
            connection.commit()

    def _initialize(self) -> None:
        self._database_path.parent.mkdir(parents=True, exist_ok=True)
        with self._lock, self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS notification_delivery (
                    channel TEXT PRIMARY KEY,
                    version TEXT NOT NULL
                )
                """
            )
            connection.commit()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._database_path, timeout=5)

