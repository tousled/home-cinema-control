from __future__ import annotations

import dataclasses

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
        self._emby_session = emby_session

    def handle_play(self, data: dict) -> None:
        intent = self._play_command_parser(data)
        if intent is None:
            return

        # Emby's "Play" websocket message never carries the id of the session
        # that issued the remote command — only `Id`, the bridge's own target
        # session echoed back. Resolve the real controlling client by looking
        # up the controlling user's other active sessions instead.
        if not intent.source_client_session_id:
            intent = dataclasses.replace(
                intent,
                source_client_session_id=self._emby_session.find_controlling_session_id(
                    intent.source_user_id
                ),
            )

        self._dispatch_play_intent(intent)
