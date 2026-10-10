from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from home_cinema_control.application_events import ApplicationEventBus
from home_cinema_control.devices.tv.factory import create_tv_controller_or_none
from home_cinema_control.home_automation.home_assistant_consumer import (
    HomeAssistantPlaybackConsumer,
    HomeAssistantWebhookClient,
)
from home_cinema_control.home_automation.delivery_status import (
    HomeAssistantDeliveryStatus,
    home_assistant_configuration_fingerprint,
)
from home_cinema_control.home_automation.delivery_status_store import (
    HomeAssistantDeliveryStatusStore,
)
from home_cinema_control.notifications.channels import (
    HomeAssistantUpdateChannel,
    TelevisionUpdateChannel,
)
from home_cinema_control.notifications.coordinator import UpdateNotificationCoordinator
from home_cinema_control.notifications.models import UpdateAvailableEvent
from home_cinema_control.notifications.monitor import UpdateMonitor
from home_cinema_control.notifications.state import NotificationStateStore
from home_cinema_control.playback.events import PlaybackEvent
from home_cinema_control.runtime import (
    HomeCinemaControlRuntime,
    RuntimePaths,
    build_runtime_paths,
)


@dataclass(frozen=True)
class ApplicationComposition:
    runtime: HomeCinemaControlRuntime
    paths: RuntimePaths
    event_bus: ApplicationEventBus
    update_monitor: UpdateMonitor
    update_notifications: UpdateNotificationCoordinator
    home_assistant_delivery_status: HomeAssistantDeliveryStatus | None


def build_application_composition(
    *,
    base_dir: str | Path,
    config_file: str | Path,
    version: str,
) -> ApplicationComposition:
    paths = build_runtime_paths(base_dir, config_file)
    event_bus = ApplicationEventBus()
    runtime = HomeCinemaControlRuntime(
        paths=paths,
        version=version,
        application_event_bus=event_bus,
    )
    config = runtime.load_config()
    notification_state_path = paths.config_file.with_name("hcc_notifications.sqlite")
    notification_state_store = NotificationStateStore(notification_state_path)
    home_assistant = config.get("home_assistant") or {}
    base_url = str(home_assistant.get("base_url") or "").strip()
    webhook_id = str(home_assistant.get("webhook_id") or "").strip()
    configuration_fingerprint = None
    if home_assistant.get("enabled") and base_url and webhook_id:
        configuration_fingerprint = home_assistant_configuration_fingerprint(
            base_url,
            webhook_id,
        )
    home_assistant_delivery_status = HomeAssistantDeliveryStatus(
        store=HomeAssistantDeliveryStatusStore(notification_state_path),
        configuration_fingerprint=configuration_fingerprint,
    )
    home_assistant_client = _build_home_assistant_client(
        config,
        delivery_status=home_assistant_delivery_status,
    )
    channels = _build_notification_channels(config, runtime, home_assistant_client)
    update_notifications = UpdateNotificationCoordinator(
        state_store=notification_state_store,
        channels=channels,
    )
    event_bus.subscribe(UpdateAvailableEvent, update_notifications)
    event_bus.subscribe(
        PlaybackEvent,
        update_notifications,
        ordering_key=lambda event: event.session_id,
    )

    if home_assistant_client is not None:
        event_bus.subscribe(
            PlaybackEvent,
            HomeAssistantPlaybackConsumer(home_assistant_client),
            ordering_key=lambda event: event.session_id,
        )

    update_monitor = UpdateMonitor(
        load_config=runtime.load_config,
        publish=event_bus.publish,
        current_version=version,
    )
    runtime.update_notification_service = update_notifications
    runtime.update_monitor = update_monitor
    return ApplicationComposition(
        runtime=runtime,
        paths=paths,
        event_bus=event_bus,
        update_monitor=update_monitor,
        update_notifications=update_notifications,
        home_assistant_delivery_status=(
            home_assistant_delivery_status if home_assistant_client is not None else None
        ),
    )


def _build_notification_channels(
    config: dict,
    runtime: HomeCinemaControlRuntime,
    home_assistant_client,
):
    channels = []
    if home_assistant_client is not None:
        channels.append(HomeAssistantUpdateChannel(home_assistant_client))

    tv = config.get("tv") or {}
    if tv.get("enabled"):
        model = str(tv.get("model") or "").strip().lower()
        channels.append(
            TelevisionUpdateChannel(
                channel_id=f"{model}_tv" if model else "television",
                television_provider=lambda: create_tv_controller_or_none(
                    runtime.load_config()
                ),
            )
        )
    return channels


def _build_home_assistant_client(
    config: dict,
    *,
    delivery_status: HomeAssistantDeliveryStatus | None = None,
):
    home_assistant = config.get("home_assistant") or {}
    if not home_assistant.get("enabled"):
        return None
    base_url = str(home_assistant.get("base_url") or "").strip()
    webhook_id = str(home_assistant.get("webhook_id") or "").strip()
    if not base_url or not webhook_id:
        return None
    return HomeAssistantWebhookClient(
        base_url=base_url,
        webhook_id=webhook_id,
        timeout_seconds=float(home_assistant.get("timeout_seconds", 3.0)),
        delivery_status=delivery_status,
    )
