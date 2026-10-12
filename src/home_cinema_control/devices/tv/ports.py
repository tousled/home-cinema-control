from typing import Protocol, runtime_checkable

from home_cinema_control.playback.startup.models import DeviceCommandResult


@runtime_checkable
class TelevisionNotificationPort(Protocol):
    supports_notifications: bool

    def show_notification(self, message: str) -> DeviceCommandResult:
        """Show a native notification without waking or changing the TV input."""
        ...
