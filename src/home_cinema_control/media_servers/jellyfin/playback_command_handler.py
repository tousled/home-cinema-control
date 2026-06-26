from home_cinema_control.media_servers.common.playback_command_handler import (
    MediaServerPlaybackCommandHandler,
)


class JellyfinPlaybackCommandHandler(MediaServerPlaybackCommandHandler):
    def __init__(self, *, jellyfin_session, **kwargs) -> None:
        super().__init__(
            provider_name="Jellyfin",
            media_server_session=jellyfin_session,
            **kwargs,
        )
