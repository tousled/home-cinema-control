from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from home_cinema_control.playback.player_state import PlayerPlaybackStartResult
from home_cinema_control.devices.tv.models import TvInputTarget


class DeviceCommandStatus(Enum):
    SUCCESS = "success"
    SKIPPED = "skipped"
    FAILED = "failed"


class PlaybackOutputRoute(Enum):
    HDMI = "hdmi"
    TV_APP = "tv_app"
    NONE = "none"


@dataclass(frozen=True)
class DeviceCommandResult:
    status: DeviceCommandStatus
    detail: str | None = None

    @property
    def successful(self) -> bool:
        return self.status == DeviceCommandStatus.SUCCESS

    @classmethod
    def success(cls, detail: str | None = None) -> "DeviceCommandResult":
        return cls(status=DeviceCommandStatus.SUCCESS, detail=detail)

    @classmethod
    def skipped(cls, detail: str | None = None) -> "DeviceCommandResult":
        return cls(status=DeviceCommandStatus.SKIPPED, detail=detail)

    @classmethod
    def failed(cls, detail: str | None = None) -> "DeviceCommandResult":
        return cls(status=DeviceCommandStatus.FAILED, detail=detail)


@dataclass(frozen=True)
class PlaybackOutputSwitchRequest:
    tv_input: TvInputTarget
    av_input_id: str | None
    route: PlaybackOutputRoute = PlaybackOutputRoute.HDMI
    player_app_id: str | None = None
    tv_enabled: bool = True
    av_enabled: bool = True
    previous_tv_app_id_override: str | None = None
    active_media_server_provider_type: str | None = None


@dataclass(frozen=True)
class PlaybackOutputSwitchResult:
    previous_tv_app_id: str | None
    tv_input_result: DeviceCommandResult
    av_power_result: DeviceCommandResult
    av_input_result: DeviceCommandResult

    @property
    def successful(self) -> bool:
        return (
                self.tv_input_result.status != DeviceCommandStatus.FAILED
            and self.av_power_result.status != DeviceCommandStatus.FAILED
            and self.av_input_result.status != DeviceCommandStatus.FAILED
        )

    @property
    def output_result(self) -> DeviceCommandResult:
        """Result of the selected media-player output route."""
        return self.tv_input_result


@dataclass(frozen=True)
class PlayerMediaFileLocation:
    content_server: str
    content_directory: str
    playback_file_name: str
    playback_file_format: str
    network_protocol: str | None = None
    player_uri: str | None = None


@dataclass(frozen=True)
class MediaPlayerStartRequest:
    media_location: PlayerMediaFileLocation
    network_protocol: str | None = None
    assume_player_already_on: bool = True
    startup_timeout_seconds: int | float = 30
    poll_interval_seconds: float = 0.5
    requested_start_position_seconds: int = 0


@dataclass(frozen=True)
class PlaybackStartupRequest:
    output_switch_request: PlaybackOutputSwitchRequest
    media_player_start_request: MediaPlayerStartRequest


@dataclass(frozen=True)
class PlaybackStartupResult:
    output_switch_result: PlaybackOutputSwitchResult
    media_player_start_result: PlayerPlaybackStartResult

    @property
    def successful(self) -> bool:
        return (
            self.output_switch_result.successful
            and self.media_player_start_result.successful
        )
