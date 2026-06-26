from __future__ import annotations

import logging

from home_cinema_control.media_servers.common.media_tracks import MediaTrack
from home_cinema_control.media_servers.common.track_mapping import (
    player_audio_to_source_track_id,
    player_subtitle_to_source_track_id,
)

logger = logging.getLogger(__name__)


class MediaServerObservedTrackMapper:
    """Maps OPPO menu indices observed during playback to media-server stream ids."""

    def __init__(self, media_server_session, *, playback_state=None) -> None:
        self._session = media_server_session
        self._playback_state = playback_state
        self._tracks: list[MediaTrack] | None = None

    def player_audio_to_source_track_id(self, player_track_index: int) -> int | None:
        return player_audio_to_source_track_id(
            self._active_tracks(),
            player_track_index,
        )

    def player_subtitle_to_source_track_id(
        self,
        player_track_index: int,
    ) -> int | None:
        return player_subtitle_to_source_track_id(
            self._active_tracks(),
            player_track_index,
        )

    def _active_tracks(self) -> list[MediaTrack]:
        if self._tracks is not None:
            return self._tracks

        active_session = self._active_session()
        if active_session is None:
            logger.warning("Cannot map observed OPPO track; no active playback session.")
            return []

        self._tracks = self._session.get_item_tracks(
            active_session.source_user_id,
            active_session.media_item_id,
        )
        return self._tracks

    def _active_session(self):
        if self._playback_state is not None:
            active_session = getattr(self._playback_state, "active_session", None)
            if active_session is not None:
                return active_session

        return None
