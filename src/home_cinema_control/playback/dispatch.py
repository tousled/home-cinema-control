from __future__ import annotations

from home_cinema_control.playback.intent import PlaybackIntent, PlaybackOrigin


def bridge_playback_is_active(playstate: str) -> bool:
    return playstate in ("Loading", "Playing", "Replay", "Paused")


class PlaybackIntentDispatcher:
    """Application boundary for playback requests from a media server."""

    def __init__(
        self,
        *,
        playback_application_service,
    ) -> None:
        self._playback_application_service = playback_application_service

    def dispatch(self, intent: PlaybackIntent, *, origin: PlaybackOrigin) -> bool:
        return self._playback_application_service.request_playback_from_intent(
            intent,
            origin=origin,
        )
