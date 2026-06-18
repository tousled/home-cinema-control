from __future__ import annotations


class ActivePlaybackRuntimeContext:
    """Runtime handles exposed while one playback orchestration is active."""

    def __init__(self) -> None:
        self._publisher = None
        self._oppo_playback = None

    @property
    def publisher(self):
        return self._publisher

    @property
    def oppo_playback(self):
        return self._oppo_playback

    def activate(self, playback_wiring) -> None:
        self._publisher = playback_wiring.playback_event_publisher
        self._oppo_playback = playback_wiring.startup_wiring.oppo_playback

    def clear(self) -> None:
        self._publisher = None
        self._oppo_playback = None
