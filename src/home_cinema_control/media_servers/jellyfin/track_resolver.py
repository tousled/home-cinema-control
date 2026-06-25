from __future__ import annotations

from home_cinema_control.media_servers.common.track_resolver import (
    MediaServerTrackResolver,
)


class JellyfinTrackResolver(MediaServerTrackResolver):
    """Adapts JellyfinSession track resolution to the PlaybackTrackResolver protocol."""

    def __init__(self, jellyfin_session) -> None:
        super().__init__(jellyfin_session)
