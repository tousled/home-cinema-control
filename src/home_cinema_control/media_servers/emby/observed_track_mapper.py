from __future__ import annotations

from home_cinema_control.media_servers.common.observed_track_mapper import (
    MediaServerObservedTrackMapper,
)


class EmbyObservedTrackMapper(MediaServerObservedTrackMapper):
    """Maps OPPO menu indices observed during playback to Emby stream ids."""

    def __init__(self, emby_session, *, playback_state=None) -> None:
        super().__init__(emby_session, playback_state=playback_state)
