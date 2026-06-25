from __future__ import annotations

from home_cinema_control.media_servers.common.playback_event_publisher import (
    MediaServerPlaybackContext,
)
from home_cinema_control.media_servers.emby.observed_track_mapper import (
    EmbyObservedTrackMapper,
)
from home_cinema_control.media_servers.emby.playback import EmbyPlaybackEventPublisher
from home_cinema_control.media_servers.emby.track_resolver import EmbyTrackResolver


class EmbyPlaybackServices:
    def playback_context_from_intent(self, intent):
        return MediaServerPlaybackContext.from_intent(intent)

    def create_playback_event_publisher(
        self,
        client,
        *,
        bridge_session_id: str,
        context,
    ):
        return EmbyPlaybackEventPublisher(
            client,
            bridge_session_id=bridge_session_id,
            context=context,
        )

    def create_track_resolver(self, playback_session):
        return EmbyTrackResolver(playback_session)

    def create_observed_track_mapper(self, playback_session, *, playback_state):
        return EmbyObservedTrackMapper(playback_session, playback_state=playback_state)
