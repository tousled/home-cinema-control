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
        tv_app_result = self._return_tv_to_app(request)
        av_audio_result = self._restore_av_tv_audio(request)
        result = PlaybackErrorRecoveryResult(
            player_stop_result=player_stop_result,
            tv_app_result=tv_app_result,
            av_audio_result=av_audio_result,
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
            tv_app_result.status.value,
            av_audio_result.status.value,
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

        return self._cleanup_player_after_error_recovery(stop_result)

    def _cleanup_player_after_error_recovery(
        self,
        player_stop_result: DeviceCommandResult,
    ) -> DeviceCommandResult:
        if self._media_player is None:
            return player_stop_result

        cleanup = getattr(self._media_player, "cleanup_after_playback_finish", None)
        if cleanup is None:
            return player_stop_result

        try:
            cleanup_result = cleanup()
        except Exception as exc:
            logger.exception("Unable to run OPPO playback error cleanup")
            cleanup_result = DeviceCommandResult.failed(
                f"OPPO playback error cleanup failed: {type(exc).__name__}: {exc}"
            )

        logger.info(
            "OPPO playback error cleanup | status=%s | detail=%s",
            cleanup_result.status.value,
            cleanup_result.detail,
        )

        if player_stop_result.status == DeviceCommandStatus.FAILED:
            return player_stop_result
        if cleanup_result.status == DeviceCommandStatus.FAILED:
            return cleanup_result
        if cleanup_result.status == DeviceCommandStatus.SKIPPED:
            return player_stop_result

        return DeviceCommandResult.success(
            f"{player_stop_result.detail}; {cleanup_result.detail}"
        )

    def _return_tv_to_app(
        self,
        request: PlaybackErrorRecoveryRequest,
    ) -> DeviceCommandResult:
        if not request.tv_enabled:
            logger.info("Skipping TV app restore during error recovery: TV control is disabled.")
            return DeviceCommandResult.skipped("TV app restore is disabled.")

        if self._television is None:
            logger.info("Skipping TV app restore during error recovery: no TV adapter configured.")
            return DeviceCommandResult.skipped("TV adapter not configured.")

        logger.info(
            "Returning TV during playback error recovery | app_id=%s",
            request.previous_tv_app_id,
        )
        return self._television.launch_app(request.previous_tv_app_id)

    def _restore_av_tv_audio(
        self,
        request: PlaybackErrorRecoveryRequest,
    ) -> DeviceCommandResult:
        if not request.av_enabled:
            logger.info("Skipping AV audio restore during error recovery: AV control is disabled.")
            return DeviceCommandResult.skipped("AV TV audio restore is disabled.")

        if self._av_receiver is None:
            return DeviceCommandResult.skipped("No AV receiver adapter configured.")

        logger.info("Restoring AV receiver during playback error recovery.")
        return self._av_receiver.restore_tv_audio()


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
