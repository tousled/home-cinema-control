from home_cinema_control.media_servers.common.playback_command_handler import (
    MediaServerPlaybackCommandHandler,
)


class EmbyPlaybackCommandHandler(MediaServerPlaybackCommandHandler):
    def __init__(self, *, emby_session, **kwargs) -> None:
        super().__init__(
            provider_name="Emby",
            media_server_session=emby_session,
            **kwargs,
        )
