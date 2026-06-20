from __future__ import annotations

from home_cinema_control.media_servers.emby import web_config
from home_cinema_control.media_servers.emby.playback_services import EmbyPlaybackServices
from home_cinema_control.media_servers.emby.websocket_listener import EmbyWebsocket
from home_cinema_control.media_servers.common.setup import ModuleMediaServerSetupService


class EmbyProvider:
    def playback_services(self) -> EmbyPlaybackServices:
        return EmbyPlaybackServices()

    def create_playback_listener(
        self,
        *,
        config: dict,
        config_file: str,
        language: dict,
    ) -> EmbyWebsocket:
        return EmbyWebsocket(
            config=config,
            config_file=config_file,
            language=language,
            playback_services=self.playback_services(),
        )

    def setup_service(self):
        return ModuleMediaServerSetupService(web_config)
