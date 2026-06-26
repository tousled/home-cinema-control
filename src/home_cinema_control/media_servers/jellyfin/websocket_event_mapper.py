from __future__ import annotations

import dataclasses
import json
from typing import Any

from home_cinema_control.media_servers.common.models import (
    MediaServerCommand,
    MediaServerCommandKind,
)
from home_cinema_control.media_servers.common.websocket_events import (
    MediaServerWebsocketEvent,
    MediaServerWebsocketEventKind,
)
from home_cinema_control.media_servers.jellyfin.playback_request import (
    build_playback_intent_from_play_command,
)
from home_cinema_control.playback.time_units import TICKS_PER_SECOND

DEFAULT_REMOTE_SKIP_SECONDS = 10

_Kind = MediaServerCommandKind
_EventKind = MediaServerWebsocketEventKind


def jellyfin_sessions_start_message() -> str:
    return '{"MessageType":"SessionsStart", "Data": "0,1500"}'


class JellyfinWebsocketEventMapper:
    def __init__(self, *, jellyfin_session) -> None:
        self._session = jellyfin_session

    def map(self, raw_message: str) -> MediaServerWebsocketEvent:
        message = json.loads(raw_message)
        message_type = message.get("MessageType")
        data = message.get("Data")

        if message_type == "Play":
            return self.map_play_payload(data or {}, raw_type=message_type)

        if message_type == "Playstate":
            return MediaServerWebsocketEvent(
                kind=_EventKind.PLAYBACK_COMMAND,
                raw_type=message_type,
                command=command_from_jellyfin_playstate_message(data or {}),
            )

        if message_type == "GeneralCommand":
            return MediaServerWebsocketEvent(
                kind=_EventKind.PLAYBACK_COMMAND,
                raw_type=message_type,
                command=command_from_jellyfin_general_command_message(data or {}),
            )

        if message_type == "Sessions" and isinstance(data, list):
            return MediaServerWebsocketEvent(
                kind=_EventKind.SESSIONS_UPDATE,
                raw_type=message_type,
                sessions=data,
            )

        return MediaServerWebsocketEvent(
            kind=_EventKind.UNSUPPORTED,
            raw_type=str(message_type or ""),
        )

    def map_play_payload(
        self,
        data: dict[str, Any],
        *,
        raw_type: str = "Play",
    ) -> MediaServerWebsocketEvent:
        intent = build_playback_intent_from_play_command(
            data,
            load_item_info=self._session.get_item_info,
        )
        if intent is None:
            return MediaServerWebsocketEvent(
                kind=_EventKind.UNSUPPORTED,
                raw_type=raw_type,
            )

        if not intent.source_client_session_id:
            intent = dataclasses.replace(
                intent,
                source_client_session_id=(
                    self._session.find_controlling_session_id(intent.source_user_id)
                ),
            )

        return MediaServerWebsocketEvent(
            kind=_EventKind.PLAYBACK_INTENT,
            raw_type=raw_type,
            playback_intent=intent,
        )


def command_from_jellyfin_playstate_message(
    data: dict[str, Any],
) -> MediaServerCommand:
    command = data.get("Command")

    if command == "Seek":
        return MediaServerCommand(
            kind=_Kind.SEEK,
            position_ticks=int(data["SeekPositionTicks"]),
            raw_name=command,
        )

    if command == "SeekRelative":
        return MediaServerCommand(
            kind=_Kind.SEEK_RELATIVE,
            offset_ticks=int(data.get("SeekPositionTicks", 0)),
            raw_name=command,
        )

    if command == "FastForward":
        return MediaServerCommand(
            kind=_Kind.SEEK_RELATIVE,
            offset_ticks=int(
                data.get(
                    "SeekPositionTicks",
                    DEFAULT_REMOTE_SKIP_SECONDS * TICKS_PER_SECOND,
                )
            ),
            raw_name=command,
        )

    if command == "Rewind":
        return MediaServerCommand(
            kind=_Kind.SEEK_RELATIVE,
            offset_ticks=int(
                data.get(
                    "SeekPositionTicks",
                    -DEFAULT_REMOTE_SKIP_SECONDS * TICKS_PER_SECOND,
                )
            ),
            raw_name=command,
        )

    kind = {
        "Pause": _Kind.PAUSE,
        "Unpause": _Kind.UNPAUSE,
        "PlayPause": _Kind.PLAY_PAUSE,
        "Stop": _Kind.STOP,
        "NextTrack": _Kind.NEXT_TRACK,
        "PreviousTrack": _Kind.PREVIOUS_TRACK,
    }.get(command)

    if kind is None:
        return MediaServerCommand(kind=_Kind.UNSUPPORTED, raw_name=str(command or ""))

    return MediaServerCommand(kind=kind, raw_name=command)


def command_from_jellyfin_general_command_message(
    data: dict[str, Any],
) -> MediaServerCommand:
    name = data.get("Name")
    args = data.get("Arguments") or {}

    if name == "SetAudioStreamIndex":
        return MediaServerCommand(
            kind=_Kind.SET_AUDIO_TRACK,
            track_index=int(args["Index"]),
            raw_name=name,
        )

    if name == "SetSubtitleStreamIndex":
        return MediaServerCommand(
            kind=_Kind.SET_SUBTITLE_TRACK,
            track_index=int(args["Index"]),
            raw_name=name,
        )

    return MediaServerCommand(kind=_Kind.UNSUPPORTED, raw_name=str(name or ""))
