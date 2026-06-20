from __future__ import annotations

from home_cinema_control.media_servers.common.playback_command_handler import (
    MediaServerPlaybackCommandHandler,
)
from home_cinema_control.media_servers.jellyfin.playback_request import (
    build_playback_intent_from_play_command,
)


class JellyfinPlaybackCommandHandler(MediaServerPlaybackCommandHandler):
    def __init__(self, *, jellyfin_session, **kwargs) -> None:
        super().__init__(
            provider_name="Jellyfin",
            media_server_session=jellyfin_session,
            play_command_parser=lambda data: build_playback_intent_from_play_command(
                data,
                load_item_info=jellyfin_session.get_item_info,
            ),
            **kwargs,
        )
