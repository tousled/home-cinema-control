from __future__ import annotations

import logging
import threading
from collections.abc import Callable

from home_cinema_control import __version__
from home_cinema_control.notifications.models import UpdateAvailableEvent
from home_cinema_control.notifications.service_helpers import build_update_notification
from home_cinema_control.web.version_update import get_cached_version_info

logger = logging.getLogger(__name__)


class UpdateMonitor:
    """Checks for releases away from startup, playback, and web requests."""

    def __init__(
        self,
        *,
        load_config: Callable[[], dict],
        publish: Callable[[object], None],
        current_version: str = __version__,
        check_version: Callable = get_cached_version_info,
    ) -> None:
        self._load_config = load_config
        self._publish = publish
        self._current_version = current_version
        self._check_version = check_version
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._thread = threading.Thread(
            target=self._run,
            name="hcc-update-monitor",
            daemon=True,
        )
        self._thread.start()

    def stop(self, *, timeout_seconds: float = 2.0) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=timeout_seconds)

    def _run(self) -> None:
        while not self._stop_event.is_set():
            config = self._safe_load_config()
            interval_hours = _interval_hours(config)
            self._check_once(config)
            self._stop_event.wait(interval_hours * 3600)

    def _check_once(self, config: dict) -> None:
        try:
            info = self._check_version(config, self._current_version)
            if not info.new_version:
                return
            notification = build_update_notification(
                info,
                language=str((config.get("app") or {}).get("language", "es-ES")),
            )
            self._publish(UpdateAvailableEvent(notification=notification))
            logger.info(
                "Update available | current=%s | latest=%s",
                notification.current_version,
                notification.latest_version,
            )
        except Exception:
            logger.exception("Background update check failed")

    def _safe_load_config(self) -> dict:
        try:
            return self._load_config()
        except Exception:
            logger.exception("Unable to load config for background update check")
            return {"app": {}}


def _interval_hours(config: dict) -> float:
    try:
        return max(0.01, float((config.get("app") or {}).get("version_check_interval_hours", 24)))
    except (TypeError, ValueError):
        return 24.0
