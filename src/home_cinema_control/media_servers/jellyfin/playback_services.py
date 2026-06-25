from __future__ import annotations

from home_cinema_control.media_servers.common.playback_event_publisher import (
    MediaServerPlaybackContext,
)
from home_cinema_control.media_servers.jellyfin.observed_track_mapper import (
    JellyfinObservedTrackMapper,
)
from home_cinema_control.media_servers.jellyfin.playback import (
    JellyfinPlaybackEventPublisher,
)
from home_cinema_control.media_servers.jellyfin.track_resolver import (
    JellyfinTrackResolver,
)


class JellyfinPlaybackServices:
    def playback_context_from_intent(self, intent):
        return MediaServerPlaybackContext.from_intent(intent)

    def create_playback_event_publisher(
        self,
        client,
        *,
        bridge_session_id: str,
        context,
    ):
        return JellyfinPlaybackEventPublisher(
            client,
            bridge_session_id=bridge_session_id,
            context=context,
        )

    def create_track_resolver(self, playback_session):
        return JellyfinTrackResolver(playback_session)

    def create_observed_track_mapper(self, playback_session, *, playback_state):
        return JellyfinObservedTrackMapper(
            playback_session,
            playback_state=playback_state,
        )
