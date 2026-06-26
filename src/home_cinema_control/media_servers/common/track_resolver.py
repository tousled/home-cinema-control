class MediaServerTrackResolver:
    """Adapts a media-server session's track resolution to the PlaybackTrackResolver protocol."""

    def __init__(self, media_server_session) -> None:
        self._session = media_server_session

    def resolve_audio_track(
        self,
        *,
        source_user_id: str,
        media_item_id: str,
        selected_source_track_id: int,
    ) -> int:
        return self._session.resolve_audio_track_index(
            source_user_id,
            media_item_id,
            selected_source_track_id,
        )

    def resolve_subtitle_track(
        self,
        *,
        source_user_id: str,
        media_item_id: str,
        selected_source_track_id: int,
    ) -> int:
        return self._session.resolve_subtitle_track_index(
            source_user_id,
            media_item_id,
            selected_source_track_id,
        )
