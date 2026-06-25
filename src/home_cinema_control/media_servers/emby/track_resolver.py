from __future__ import annotations

from home_cinema_control.media_servers.common.track_resolver import (
    MediaServerTrackResolver,
)


class EmbyTrackResolver(MediaServerTrackResolver):
    """Adapts EmbySession track resolution to the PlaybackTrackResolver protocol."""

    def __init__(self, emby_session) -> None:
        super().__init__(emby_session)
