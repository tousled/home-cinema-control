from typing import Protocol, Callable

from home_cinema_control.devices.tv.models import TvInputTarget
from home_cinema_control.playback.startup.models import (
    DeviceCommandResult,
    OppoPlaybackStartRequest,
    OppoPlaybackStartResult,
    OppoPlaybackPosition,
    OppoPlaybackState,
)


class MediaPlayerControl(Protocol):
    """Media-server-facing playback control interface.

    Abstracts over the hardware player so media server command handlers
    (e.g. Emby) do not depend on device-specific types.
    """

    def send_remote_key(self, key: str) -> DeviceCommandResult: ...

    def get_playback_state(self) -> OppoPlaybackState: ...

    def seek_to_position_ticks(self, position_ticks: int) -> DeviceCommandResult: ...

    def current_position_ticks(self) -> int: ...

    def select_audio_track(self, audio_index: int) -> DeviceCommandResult: ...

    def select_subtitle_track(self, subtitle_index: int) -> DeviceCommandResult: ...


class TelevisionOutputPort(Protocol):
    def get_current_app_id(self) -> str | None:
        """Return the current TV app id, if available."""
        ...

    def switch_to_input(self, target: TvInputTarget) -> DeviceCommandResult:
        """Switch the TV to the requested input."""
        ...

    def launch_app(self, app_id: str | None) -> DeviceCommandResult:
        """Launch the requested app on the TV, or skip if app_id is None."""
        ...


class AvReceiverOutputPort(Protocol):
    def power_on(self) -> DeviceCommandResult:
        """Ensure the AV receiver is powered on."""
        ...

    def switch_to_input(self, input_id: str) -> DeviceCommandResult:
        """Switch the AV receiver to the requested input id."""
        ...

    def restore_tv_audio(self) -> DeviceCommandResult:
        """Restore the AV receiver to TV audio."""
        ...


class OppoPlaybackPort(Protocol):
    def start_playback(
        self,
        request: OppoPlaybackStartRequest,
        *,
        on_waiting: Callable[[int], None] | None = None,
    ) -> OppoPlaybackStartResult: ...

    def get_playback_state(self) -> OppoPlaybackState: ...

    def get_playback_position(self) -> OppoPlaybackPosition: ...

    def seek_to(self, position_ticks: int) -> DeviceCommandResult: ...

    def select_audio_track(self, audio_index: int) -> DeviceCommandResult: ...

    def select_subtitle_track(self, subtitle_index: int) -> DeviceCommandResult: ...

    def stop_playback(self) -> DeviceCommandResult: ...
