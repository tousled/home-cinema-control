from __future__ import annotations

import logging
from dataclasses import dataclass

from home_cinema_control.devices.av.factory import create_av_receiver_or_none
from home_cinema_control.devices.tv.factory import create_tv_controller_or_none
from home_cinema_control.playback.ports import (
    AvReceiverOutputPort,
    MediaPlayerPort,
    TelevisionOutputPort,
)
from home_cinema_control.playback.restoration import (
    PlaybackOutputRestorationRequest,
    PlaybackRestorationService,
)
from home_cinema_control.playback.startup.models import (
    DeviceCommandResult,
    DeviceCommandStatus,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PlaybackErrorRecoveryRequest:
    reason: str
    previous_tv_app_id: str | None
    tv_enabled: bool = True
    av_enabled: bool = True


@dataclass(frozen=True)
class PlaybackErrorRecoveryResult:
    player_stop_result: DeviceCommandResult
    tv_app_result: DeviceCommandResult
    av_audio_result: DeviceCommandResult

    @property
    def successful(self) -> bool:
        return (
            self.player_stop_result.status != DeviceCommandStatus.FAILED
            and
            self.tv_app_result.status != DeviceCommandStatus.FAILED
            and self.av_audio_result.status != DeviceCommandStatus.FAILED
        )


class PlaybackErrorHandler:
    """Central recovery point for playback errors across orchestration phases."""

    def __init__(
        self,
        *,
            television: TelevisionOutputPort | None,
        av_receiver: AvReceiverOutputPort | None,
        media_player: MediaPlayerPort | None = None,
    ) -> None:
        self._television = television
        self._av_receiver = av_receiver
        self._media_player = media_player
        self._restoration = PlaybackRestorationService(
            television=television,
            av_receiver=av_receiver,
            media_player=media_player,
        )

    def recover(self, request: PlaybackErrorRecoveryRequest) -> PlaybackErrorRecoveryResult:
        logger.warning(
            "Recovering playback error | reason=%s | previous_tv_app_id=%s | "
            "tv_enabled=%s | av_enabled=%s",
            request.reason,
            request.previous_tv_app_id,
            request.tv_enabled,
            request.av_enabled,
        )

        player_stop_result = self._stop_player_playback()
        output_restoration_result = self._restoration.restore_outputs(
            PlaybackOutputRestorationRequest(
                previous_tv_app_id=request.previous_tv_app_id,
                tv_enabled=request.tv_enabled,
                av_enabled=request.av_enabled,
                log_context="playback error recovery",
            )
        )
        result = PlaybackErrorRecoveryResult(
            player_stop_result=player_stop_result,
            tv_app_result=output_restoration_result.tv_app_result,
            av_audio_result=output_restoration_result.av_audio_result,
        )

        # OPPO_ERROR_RECOVERY_FAILED / TV_ERROR_RECOVERY_FAILED / AV_ERROR_RECOVERY_FAILED
        # are real diagnostics — recovery failing on top of the original failure is
        # not routine narration.
        log = logger.info if result.successful else logger.error
        log(
            "Playback error recovery result | successful=%s | player_stop=%s | "
            "tv=%s | av_audio=%s",
            result.successful,
            player_stop_result.status.value,
            output_restoration_result.tv_app_result.status.value,
            output_restoration_result.av_audio_result.status.value,
        )
        return result

    def _stop_player_playback(self) -> DeviceCommandResult:
        if self._media_player is None:
            return DeviceCommandResult.skipped("No OPPO playback adapter configured.")

        logger.info("Stopping OPPO playback during error recovery.")
        try:
            stop_result = self._media_player.stop()
        except Exception as exc:
            logger.exception("Unable to stop OPPO playback during error recovery.")
            stop_result = DeviceCommandResult.failed(
                f"OPPO playback stop failed: {type(exc).__name__}: {exc}"
            )

        return self._restoration.cleanup_after_player_stop(stop_result)


def create_playback_error_handler(
    config: dict,
    *,
    media_player: MediaPlayerPort | None = None,
) -> PlaybackErrorHandler:
    return PlaybackErrorHandler(
        television=create_tv_controller_or_none(config),
        av_receiver=create_av_receiver_or_none(config),
        media_player=media_player,
    )
