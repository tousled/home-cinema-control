from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from home_cinema_control.home_automation.home_assistant_transport import (
    HomeAssistantWebhookError,
)
from home_cinema_control.notifications.models import UpdateNotification
from home_cinema_control.playback.startup.models import DeviceCommandStatus

logger = logging.getLogger(__name__)


class NotificationDeliveryStatus(StrEnum):
    DELIVERED = "delivered"
    UNSUPPORTED = "unsupported"
    FAILED = "failed"


@dataclass(frozen=True)
class NotificationDeliveryResult:
    status: NotificationDeliveryStatus
    detail: str = ""

    @classmethod
    def delivered(cls) -> "NotificationDeliveryResult":
        return cls(NotificationDeliveryStatus.DELIVERED)

    @classmethod
    def unsupported(cls, detail: str = "") -> "NotificationDeliveryResult":
        return cls(NotificationDeliveryStatus.UNSUPPORTED, detail)

    @classmethod
    def failed(cls, detail: str = "") -> "NotificationDeliveryResult":
        return cls(NotificationDeliveryStatus.FAILED, detail)


class NotificationChannel(Protocol):
    channel_id: str
    defer_until_playback: bool = False

    def deliver(self, notification: UpdateNotification) -> NotificationDeliveryResult:
        ...


class HomeAssistantUpdateChannel(NotificationChannel):
    channel_id = "home_assistant"

    def __init__(self, client) -> None:
        self._client = client

    def deliver(self, notification: UpdateNotification) -> NotificationDeliveryResult:
        try:
            self._client.send(
                {
                    "event": "hcc_update_available",
                    "current_version": notification.current_version,
                    "latest_version": notification.latest_version,
                    "release_url": notification.release_url,
                }
            )
        except HomeAssistantWebhookError as exc:
            logger.warning(
                "Home Assistant update notification failed | current=%s | latest=%s | "
                "status=%s",
                notification.current_version,
                notification.latest_version,
                exc.status_code or "transport_error",
            )
            return NotificationDeliveryResult.failed(type(exc).__name__)
        except Exception as exc:
            logger.warning(
                "Home Assistant update notification failed | current=%s | latest=%s | "
                "error=%s",
                notification.current_version,
                notification.latest_version,
                type(exc).__name__,
            )
            return NotificationDeliveryResult.failed(type(exc).__name__)
        return NotificationDeliveryResult.delivered()


class TelevisionUpdateChannel(NotificationChannel):
    defer_until_playback = True

    def __init__(
        self,
        *,
        channel_id: str,
        television_provider: Callable[[], object | None],
    ) -> None:
        self.channel_id = channel_id
        self._television_provider = television_provider

    def deliver(self, notification: UpdateNotification) -> NotificationDeliveryResult:
        try:
            television = self._television_provider()
            show_notification = getattr(television, "show_notification", None)
            if not callable(show_notification):
                return NotificationDeliveryResult.unsupported(
                    "TV adapter has no notification capability."
                )

            result = show_notification(notification.message)
            if result.status == DeviceCommandStatus.SKIPPED:
                return NotificationDeliveryResult.unsupported(result.detail)
            if result.status != DeviceCommandStatus.SUCCESS:
                return NotificationDeliveryResult.failed(result.detail)
        except Exception as exc:
            logger.exception(
                "TV update notification failed | current=%s | latest=%s",
                notification.current_version,
                notification.latest_version,
            )
            return NotificationDeliveryResult.failed(type(exc).__name__)
        return NotificationDeliveryResult.delivered()
