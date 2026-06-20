from websocket import WebSocketApp

from home_cinema_control.media_servers.common.websocket_listener import (
    MediaServerWebsocketListener,
    jellyfin_websocket_uri,
)
from home_cinema_control.media_servers.jellyfin.playback_command_handler import (
    JellyfinPlaybackCommandHandler,
)
from home_cinema_control.media_servers.jellyfin.session import JellyfinSession
from home_cinema_control.media_servers.jellyfin.session_monitor import (
    JellyfinSessionMonitor,
)


class JellyfinWebsocket(MediaServerWebsocketListener):
    def __init__(
        self,
        *,
        config=None,
        config_file: str = "",
        language=None,
        playback_services=None,
    ):
        super().__init__(
            provider_name="Jellyfin",
            session_attribute_name="jellyfin_session",
            session_factory=JellyfinSession,
            command_handler_factory=lambda session, **kwargs: JellyfinPlaybackCommandHandler(
                jellyfin_session=session,
                **kwargs,
            ),
            session_monitor_factory=lambda session, **kwargs: JellyfinSessionMonitor(
                jellyfin_session=session,
                **kwargs,
            ),
            websocket_app_factory=lambda *args, **kwargs: WebSocketApp(*args, **kwargs),
            websocket_uri_factory=jellyfin_websocket_uri,
            config=config,
            config_file=config_file,
            language=language,
            playback_services=playback_services,
        )
