from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class MediaTrackKind(str, Enum):
    VIDEO = "video"
    AUDIO = "audio"
    SUBTITLE = "subtitle"
    OTHER = "other"


@dataclass(frozen=True)
class MediaTrack:
    kind: MediaTrackKind
    source_index: int

