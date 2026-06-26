from __future__ import annotations

from typing import Protocol

from home_cinema_control.playback.state import BridgePlaybackState


class MediaServerPlaybackListener(Protocol):
    playback_state: BridgePlaybackState | None

    def run(self) -> None: ...

    def stop(self) -> None: ...

    def update_config(self, config: dict) -> None: ...

    def play_from_command(self, data: dict) -> None: ...
