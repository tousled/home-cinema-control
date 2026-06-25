from __future__ import annotations

import dataclasses

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
        self._jellyfin_session = jellyfin_session

    def handle_play(self, data: dict) -> None:
        intent = self._play_command_parser(data)
        if intent is None:
            return

        # Jellyfin's "Play" websocket message never carries the id of the
        # session that issued the remote command — only `Id`, the bridge's
        # own target session echoed back. Resolve the real controlling
        # client the same way EmbyPlaybackCommandHandler does.
        if not intent.source_client_session_id:
            intent = dataclasses.replace(
                intent,
                source_client_session_id=self._jellyfin_session.find_controlling_session_id(
                    intent.source_user_id
                ),
            )

        self._dispatch_play_intent(intent)
