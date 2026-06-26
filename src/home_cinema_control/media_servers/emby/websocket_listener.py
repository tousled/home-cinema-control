from websocket import WebSocketApp

from home_cinema_control.media_servers.common.websocket_listener import (
    MediaServerWebsocketListener,
    emby_websocket_uri,
)
from home_cinema_control.media_servers.emby.playback_command_handler import (
    EmbyPlaybackCommandHandler,
)
from home_cinema_control.media_servers.emby.session import EmbySession
from home_cinema_control.media_servers.emby.session_monitor import EmbySessionMonitor
from home_cinema_control.media_servers.emby.websocket_event_mapper import (
    EmbyWebsocketEventMapper,
    emby_sessions_start_message,
)


class EmbyWebsocket(MediaServerWebsocketListener):
    def __init__(
            self,
            *,
            config=None,
            config_file: str = "",
            language=None,
            playback_services=None,
    ):
        super().__init__(
            provider_name="Emby",
            session_attribute_name="emby_session",
            session_factory=EmbySession,
            command_handler_factory=lambda session, **kwargs: EmbyPlaybackCommandHandler(
                emby_session=session,
                **kwargs,
            ),
            session_monitor_factory=lambda session, **kwargs: EmbySessionMonitor(
                emby_session=session,
                **kwargs,
            ),
            websocket_event_mapper_factory=lambda session: EmbyWebsocketEventMapper(
                emby_session=session,
            ),
            session_subscription_message=emby_sessions_start_message(),
            websocket_app_factory=lambda *args, **kwargs: WebSocketApp(*args, **kwargs),
            websocket_uri_factory=emby_websocket_uri,
            config=config,
            config_file=config_file,
            language=language,
            playback_services=playback_services,
        )
