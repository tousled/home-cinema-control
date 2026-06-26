from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from home_cinema_control.media_servers.common.models import MediaServerCommand
from home_cinema_control.playback.intent import PlaybackIntent


class MediaServerWebsocketEventKind(str, Enum):
    PLAYBACK_INTENT = "playback_intent"
    PLAYBACK_COMMAND = "playback_command"
    SESSIONS_UPDATE = "sessions_update"
    UNSUPPORTED = "unsupported"


@dataclass(frozen=True)
class MediaServerWebsocketEvent:
    kind: MediaServerWebsocketEventKind
    raw_type: str = ""
    playback_intent: PlaybackIntent | None = None
    command: MediaServerCommand | None = None
    sessions: list[dict[str, Any]] | None = None
