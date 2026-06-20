from abc import ABC, abstractmethod

from home_cinema_control.devices.tv.models import TvInputTarget
from home_cinema_control.playback.startup.models import DeviceCommandResult


class BaseTvController(ABC):
    def __init__(self, config: dict):
        self.config = config

    @abstractmethod
    def test_connection(self) -> DeviceCommandResult:
        pass

    @abstractmethod
    def retrieve_hdmi_inputs(self) -> DeviceCommandResult:
        pass

    @abstractmethod
    def switch_to_input(self, target: TvInputTarget) -> DeviceCommandResult:
        pass

    @abstractmethod
    def launch_app(self, app_id: str | None) -> DeviceCommandResult:
        pass

    @abstractmethod
    def get_current_app_id(self) -> str | None:
        pass

    @abstractmethod
    def media_server_app_id(self, provider_type: str) -> str | None:
        """Return this TV brand's app id for the given media-server provider.

        Each TV adapter owns its own provider-to-app-id mapping, the same way
        each media-server provider owns its own wire format. Adding a TV brand
        means adding its mapping here, not touching shared code.
        """
