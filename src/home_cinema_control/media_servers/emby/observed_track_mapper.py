from __future__ import annotations

import logging
from typing import Any

from home_cinema_control.media_servers.emby.track_mapping import (
    player_audio_to_source_track_id,
    player_subtitle_to_source_track_id,
)

logger = logging.getLogger(__name__)


class EmbyObservedTrackMapper:
    """Maps OPPO menu indices observed during playback to Emby stream ids."""

    def __init__(self, emby_session, *, playback_state=None) -> None:
        self._emby_session = emby_session
        self._playback_state = playback_state
        self._media_streams: list[dict[str, Any]] | None = None

    def player_audio_to_source_track_id(self, player_track_index: int) -> int | None:
        return player_audio_to_source_track_id(
            self._active_media_streams(),
            player_track_index,
        )

    def player_subtitle_to_source_track_id(
        self,
        player_track_index: int,
    ) -> int | None:
        return player_subtitle_to_source_track_id(
            self._active_media_streams(),
            player_track_index,
        )

    def _active_media_streams(self) -> list[dict[str, Any]]:
        if self._media_streams is not None:
            return self._media_streams

        active_session = self._active_session()
        if active_session is None:
            logger.warning("Cannot map observed OPPO track; no active playback session.")
            return []

        item_info = self._emby_session.get_item_info(
            active_session.source_user_id,
            active_session.media_item_id,
        )
        self._media_streams = item_info.get("MediaStreams", [])
        return self._media_streams

    def _active_session(self):
        if self._playback_state is not None:
            active_session = getattr(self._playback_state, "active_session", None)
            if active_session is not None:
                return active_session

        return None
