from __future__ import annotations

from typing import Protocol

from home_cinema_control.playback.intent import PlaybackIntent
from home_cinema_control.playback.observed_event_reporter import ObservedPlaybackTrackMapper
from home_cinema_control.playback.startup.completion import PlaybackTrackResolver
from home_cinema_control.playback.state import BridgePlaybackState


class MediaServerPlaybackServices(Protocol):
    def playback_context_from_intent(self, intent: PlaybackIntent): ...

    def create_playback_event_publisher(
        self,
        client,
        *,
        bridge_session_id: str,
        context,
    ): ...

    def create_track_resolver(self, playback_session) -> PlaybackTrackResolver: ...

    def create_observed_track_mapper(
        self,
        playback_session,
        *,
        playback_state: BridgePlaybackState,
    ) -> ObservedPlaybackTrackMapper: ...
