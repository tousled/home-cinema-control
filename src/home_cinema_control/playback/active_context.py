from __future__ import annotations


class ActivePlaybackRuntimeContext:
    """Runtime handles exposed while one playback orchestration is active."""

    def __init__(self) -> None:
        self._publisher = None
        self._media_player = None

    @property
    def publisher(self):
        return self._publisher

    @property
    def media_player(self):
        return self._media_player

    @property
    def oppo_playback(self):
        return self._media_player

    def activate(self, playback_wiring) -> None:
        self._publisher = playback_wiring.playback_event_publisher
        self._media_player = playback_wiring.startup_wiring.media_player

    def clear(self) -> None:
        self._publisher = None
        self._media_player = None
