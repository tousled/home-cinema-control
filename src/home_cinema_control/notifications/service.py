"""Compatibility facade for the update notification coordinator."""

from collections.abc import Callable

from home_cinema_control.notifications.channels import (
    HomeAssistantUpdateChannel,
    TelevisionUpdateChannel,
)
from home_cinema_control.notifications.coordinator import UpdateNotificationCoordinator
from home_cinema_control.notifications.models import UpdateNotification
from home_cinema_control.notifications.service_helpers import build_update_notification


class UpdateNotificationService(UpdateNotificationCoordinator):
    """Compatibility constructor while callers migrate to channel injection."""

    def __init__(
        self,
        *,
        state_store,
        home_assistant_consumer=None,
        television_factory: Callable[[dict], object] | None = None,
        config_provider: Callable[[], dict] | None = None,
        channels=None,
    ) -> None:
        if channels is None:
            channels = []
            if home_assistant_consumer is not None:
                channels.append(HomeAssistantUpdateChannel(home_assistant_consumer))
            if television_factory is not None:
                config_provider = config_provider or (lambda: {})
                config = config_provider()
                tv = config.get("tv") or {}
                model = str(tv.get("model") or "").strip().lower()
                channels.append(
                    TelevisionUpdateChannel(
                        channel_id=f"{model}_tv" if model else "television",
                        television_provider=lambda: television_factory(config_provider()),
                    )
                )
        super().__init__(state_store=state_store, channels=channels)

__all__ = [
    "UpdateNotificationCoordinator",
    "UpdateNotificationService",
    "UpdateNotification",
    "build_update_notification",
]
