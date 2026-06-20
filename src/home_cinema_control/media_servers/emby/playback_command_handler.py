from __future__ import annotations

from home_cinema_control.media_servers.common.playback_command_handler import (
    MediaServerPlaybackCommandHandler,
)
from home_cinema_control.media_servers.emby.playback_request import (
    build_playback_intent_from_play_command,
)


class EmbyPlaybackCommandHandler(MediaServerPlaybackCommandHandler):
    def __init__(self, *, emby_session, **kwargs) -> None:
        super().__init__(
            provider_name="Emby",
            media_server_session=emby_session,
            play_command_parser=lambda data: build_playback_intent_from_play_command(
                data,
                load_item_info=emby_session.get_item_info,
            ),
            **kwargs,
        )
