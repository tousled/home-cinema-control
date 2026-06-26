from __future__ import annotations

from dataclasses import dataclass

from home_cinema_control.playback.content_kind import MediaContentKind


@dataclass(frozen=True)
class MediaServerPlaybackSource:
    """The resolved file + metadata for what's actually being played.

    The counterpart to `MediaServerPlaybackContext`: context is the request,
    source is what got resolved. Each provider maps its own raw `Item`/
    `MediaSource` wire dict into this at the adapter edge — policy code reads
    these typed fields and never a provider's own field names.
    """

    path: str
    container: str
    duration_seconds: int
    production_year: int | None
    title: str
    content_kind: MediaContentKind
