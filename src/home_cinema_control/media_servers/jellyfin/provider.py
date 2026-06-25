from __future__ import annotations

from home_cinema_control.media_servers.common.setup import ModuleMediaServerSetupService
from home_cinema_control.media_servers.jellyfin import web_config
from home_cinema_control.media_servers.jellyfin.playback_services import (
    JellyfinPlaybackServices,
)
from home_cinema_control.media_servers.jellyfin.websocket_listener import (
    JellyfinWebsocket,
)


class JellyfinProvider:
    def playback_services(self):
        return JellyfinPlaybackServices()

    def create_playback_listener(self, *, config: dict, config_file: str, language: dict):
        return JellyfinWebsocket(
            config=config,
            config_file=config_file,
            language=language,
            playback_services=self.playback_services(),
        )

    def setup_service(self):
        return ModuleMediaServerSetupService(web_config)
