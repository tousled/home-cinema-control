from __future__ import annotations

import logging
from dataclasses import dataclass

from home_cinema_control.playback.player_state import (
    PlayerPlaybackState,
    PlayerPlaybackStatus,
)
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
class PlaybackOutputRestorationRequest:
    previous_tv_app_id: str | None
    tv_enabled: bool = True
    av_enabled: bool = True
    final_player_state: PlayerPlaybackState | None = None
    log_context: str = "playback restoration"


@dataclass(frozen=True)
class PlaybackOutputRestorationResult:
    tv_app_result: DeviceCommandResult
    av_audio_result: DeviceCommandResult

    @property
    def successful(self) -> bool:
        return (
            self.tv_app_result.status != DeviceCommandStatus.FAILED
            and self.av_audio_result.status != DeviceCommandStatus.FAILED
        )


class PlaybackRestorationService:
    """Restores playback-side device state after finish or error recovery."""

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

    def cleanup_after_confirmed_player_state(
        self,
        idle_confirmation_result: DeviceCommandResult,
    ) -> DeviceCommandResult:
        return self._cleanup_media_player_after_playback(
            idle_confirmation_result,
            log_context="OPPO playback finish cleanup",
            failure_context="OPPO playback finish cleanup",
        )

    def cleanup_after_player_stop(
        self,
        stop_result: DeviceCommandResult,
    ) -> DeviceCommandResult:
        return self._cleanup_media_player_after_playback(
            stop_result,
            log_context="OPPO playback error cleanup",
            failure_context="OPPO playback error cleanup",
        )

    def restore_outputs(
        self,
        request: PlaybackOutputRestorationRequest,
    ) -> PlaybackOutputRestorationResult:
        return PlaybackOutputRestorationResult(
            tv_app_result=self._return_tv_to_app(request),
            av_audio_result=self._restore_av_tv_audio(request),
        )

    def _cleanup_media_player_after_playback(
        self,
        player_result: DeviceCommandResult,
        *,
        log_context: str,
        failure_context: str,
    ) -> DeviceCommandResult:
        if self._media_player is None:
            return player_result

        cleanup = getattr(self._media_player, "cleanup_after_playback_finish", None)
        if cleanup is None:
            return player_result

        try:
            cleanup_result = cleanup()
        except Exception as exc:
            logger.exception("Unable to run %s", failure_context)
            cleanup_result = DeviceCommandResult.failed(
                f"{failure_context} failed: {type(exc).__name__}: {exc}"
            )

        logger.info(
            "%s | status=%s | detail=%s",
            log_context,
            cleanup_result.status.value,
            cleanup_result.detail,
        )

        if player_result.status == DeviceCommandStatus.FAILED:
            return player_result
        if cleanup_result.status == DeviceCommandStatus.FAILED:
            return cleanup_result
        if cleanup_result.status == DeviceCommandStatus.SKIPPED:
            return player_result

        return DeviceCommandResult.success(
            f"{player_result.detail}; {cleanup_result.detail}"
        )

    def _return_tv_to_app(
        self,
        request: PlaybackOutputRestorationRequest,
    ) -> DeviceCommandResult:
        if not request.tv_enabled:
            logger.info(
                "Skipping TV app restore during %s: TV control is disabled.",
                request.log_context,
            )
            return DeviceCommandResult.skipped("TV app restore is disabled.")

        if _player_is_in_screen_saver(request):
            logger.info(
                "Skipping TV app restore during %s: OPPO is in screen saver, "
                "the player is likely still paused rather than finished.",
                request.log_context,
            )
            return DeviceCommandResult.skipped(
                "OPPO is in screen saver; treating as still paused."
            )

        if self._television is None:
            logger.info(
                "Skipping TV app restore during %s: no TV adapter configured.",
                request.log_context,
            )
            return DeviceCommandResult.skipped("TV adapter not configured.")

        logger.info(
            "Returning TV during %s | app_id=%s",
            request.log_context,
            request.previous_tv_app_id,
        )
        try:
            return self._television.launch_app(request.previous_tv_app_id)
        except Exception as exc:
            logger.exception("Unable to return TV during %s", request.log_context)
            return DeviceCommandResult.failed(
                f"TV app restore failed: {type(exc).__name__}: {exc}"
            )

    def _restore_av_tv_audio(
        self,
        request: PlaybackOutputRestorationRequest,
    ) -> DeviceCommandResult:
        if not request.av_enabled:
            logger.info(
                "Skipping AV audio restore during %s: AV control is disabled.",
                request.log_context,
            )
            return DeviceCommandResult.skipped("AV TV audio restore is disabled.")

        if _player_is_in_screen_saver(request):
            logger.info(
                "Skipping AV audio restore during %s: OPPO is in screen saver, "
                "the player is likely still paused rather than finished.",
                request.log_context,
            )
            return DeviceCommandResult.skipped(
                "OPPO is in screen saver; treating as still paused."
            )

        if self._av_receiver is None:
            return DeviceCommandResult.skipped("No AV receiver adapter configured.")

        logger.info("Restoring AV receiver during %s.", request.log_context)
        try:
            return self._av_receiver.restore_tv_audio()
        except Exception as exc:
            logger.exception("Unable to restore AV receiver during %s", request.log_context)
            return DeviceCommandResult.failed(
                f"AV TV audio restore failed: {type(exc).__name__}: {exc}"
            )


def _player_is_in_screen_saver(request: PlaybackOutputRestorationRequest) -> bool:
    # Defense in depth: a SCREEN_SAVER final state means the OPPO went idle
    # while monitoring gave up, not that the user actually stopped. Restoring
    # the room here would interrupt a session that is, in practice, still
    # paused. See the screen-saver carve-out in polling_observation_strategy.py.
    return (
        request.final_player_state is not None
        and request.final_player_state.status == PlayerPlaybackStatus.SCREEN_SAVER
    )
