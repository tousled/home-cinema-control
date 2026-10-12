from __future__ import annotations

import logging
import threading

from home_cinema_control.notifications.channels import (
    NotificationChannel,
    NotificationDeliveryStatus,
)
from home_cinema_control.notifications.models import (
    UpdateAvailableEvent,
    UpdateNotification,
)
from home_cinema_control.notifications.state import NotificationStateStore
from home_cinema_control.playback.events import PlaybackEvent, PlaybackEventType

logger = logging.getLogger(__name__)


class UpdateNotificationCoordinator:
    """Coordinates pending update delivery without knowing channel transports."""

    name = "update_notifications"

    def __init__(
        self,
        *,
        state_store: NotificationStateStore,
        channels: list[NotificationChannel],
    ) -> None:
        self._state_store = state_store
        self._channels = tuple(channels)
        self._pending: UpdateNotification | None = None
        self._lock = threading.RLock()

    def consume(self, event) -> None:
        with self._lock:
            if isinstance(event, UpdateAvailableEvent):
                self._pending = event.notification
                self._deliver(deferred=False)
                return

            if isinstance(event, PlaybackEvent) and event.event_type == PlaybackEventType.STARTED:
                self._deliver(deferred=True)

    def _deliver(self, *, deferred: bool) -> None:
        notification = self._pending
        if notification is None:
            return

        for channel in self._channels:
            if channel.defer_until_playback != deferred:
                continue
            if self._state_store.last_notified_version(channel.channel_id) == notification.latest_version:
                continue

            result = channel.deliver(notification)
            if result.status == NotificationDeliveryStatus.DELIVERED:
                self._state_store.mark_notified(
                    channel.channel_id,
                    notification.latest_version,
                )
                continue
            if result.status == NotificationDeliveryStatus.UNSUPPORTED:
                logger.info(
                    "Notification channel unsupported | channel=%s | latest=%s | detail=%s",
                    channel.channel_id,
                    notification.latest_version,
                    result.detail,
                )
                continue
            logger.warning(
                "Notification delivery pending | channel=%s | latest=%s | detail=%s",
                channel.channel_id,
                notification.latest_version,
                result.detail,
            )
