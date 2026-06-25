from __future__ import annotations

from home_cinema_control.media_servers.common.observed_track_mapper import (
    MediaServerObservedTrackMapper,
)


class JellyfinObservedTrackMapper(MediaServerObservedTrackMapper):
    """Maps OPPO menu indices observed during playback to Jellyfin stream ids."""

    def __init__(self, jellyfin_session, *, playback_state=None) -> None:
        super().__init__(jellyfin_session, playback_state=playback_state)
