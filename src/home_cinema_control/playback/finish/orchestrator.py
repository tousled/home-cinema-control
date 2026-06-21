from __future__ import annotations

import logging
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Protocol

from home_cinema_control.devices.oppo.playback_state import (
    OppoPlaybackCategory,
    OppoPlaybackStatus,
)
from home_cinema_control.playback.finish.models import (
    PlaybackFinishRequest,
    PlaybackFinishResult,
)
from home_cinema_control.playback.ports import (
    AvReceiverOutputPort,
    OppoPlaybackPort,
    TelevisionOutputPort,
)
from home_cinema_control.playback.startup.models import (
    DeviceCommandResult,
    DeviceCommandStatus,
    OppoPlaybackState,
)

logger = logging.getLogger(__name__)


class PlaybackStoppedReporter(Protocol):
    def stopped(
        self,
        *,
        position_seconds: int,
        duration_seconds: int,
        is_paused: bool = False,
        is_muted: bool = False,
        played: bool = True,
    ): ...


class FinishPlaybackOrchestrator:
    """Completes normal playback and restores user-facing outputs."""

    def __init__(
        self,
        *,
        stopped_reporter: PlaybackStoppedReporter,
            television: TelevisionOutputPort | None,
        av_receiver: AvReceiverOutputPort | None,
        oppo_playback: OppoPlaybackPort | None = None,
        sleep=time.sleep,
    ) -> None:
        self._stopped_reporter = stopped_reporter
        self._television = television
        self._av_receiver = av_receiver
        self._oppo_playback = oppo_playback
        self._sleep = sleep

    def finish(self, request: PlaybackFinishRequest) -> PlaybackFinishResult:
        final_player_state, player_idle_result = self._close_and_confirm_player_state(
            request
        )

        # Player cleanup (OPPO autoscript unmount) and the Emby "stopped"
        # report are independent — run them concurrently so a slow/unverified
        # unmount attempt never delays the user-facing stop notification.
        with ThreadPoolExecutor(max_workers=1) as executor:
            cleanup_future = executor.submit(
                self._cleanup_player_after_finish, player_idle_result
            )

            media_server_stop_result = self._stopped_reporter.stopped(
                position_seconds=request.position_seconds,
                duration_seconds=request.duration_seconds,
                is_paused=request.is_paused,
                is_muted=request.is_muted,
                played=request.played,
            )

            player_idle_result = cleanup_future.result()

        logger.info(
            "Media server playback stopped | position_seconds=%s | "
            "duration_seconds=%s | media_ended=%s | played=%s",
            request.position_seconds,
            request.duration_seconds,
            request.media_ended,
            request.played,
        )

        tv_app_result = self._return_tv_to_app(request)
        av_audio_result = self._restore_av_tv_audio(request)

        return PlaybackFinishResult(
            media_server_stop_result=media_server_stop_result,
            player_idle_result=player_idle_result,
            tv_app_result=tv_app_result,
            av_audio_result=av_audio_result,
            final_player_state=final_player_state,
        )

    def _close_and_confirm_player_state(
        self,
        request: PlaybackFinishRequest,
    ) -> tuple[OppoPlaybackState, DeviceCommandResult]:
        close_result = self._close_player_after_natural_end(request)
        if close_result.status == DeviceCommandStatus.FAILED:
            return request.final_player_state, close_result

        final_player_state, idle_result = self._confirm_idle_state(request)
        if close_result.successful and idle_result.successful:
            return final_player_state, DeviceCommandResult.success(
                f"{close_result.detail}; {idle_result.detail}"
            )

        return final_player_state, idle_result

    def _close_player_after_natural_end(
        self,
        request: PlaybackFinishRequest,
    ) -> DeviceCommandResult:
        if not request.media_ended:
            return DeviceCommandResult.skipped("Playback did not end by media position.")

        if request.final_player_state.category == OppoPlaybackCategory.IDLE:
            return DeviceCommandResult.skipped("Player is already idle after media end.")

        if self._oppo_playback is None:
            return DeviceCommandResult.skipped(
                "No OPPO playback adapter configured for media-end close."
            )

        logger.info(
            "Closing OPPO playback after natural media end | state=%s | category=%s",
            request.final_player_state.status.value,
            request.final_player_state.category.value,
        )
        return self._oppo_playback.stop_playback()

    def _confirm_idle_state(
        self,
        request: PlaybackFinishRequest,
    ) -> tuple[OppoPlaybackState, DeviceCommandResult]:
        state = request.final_player_state
        if state.category == OppoPlaybackCategory.IDLE:
            return state, DeviceCommandResult.success("OPPO already idle.")

        if self._oppo_playback is None:
            logger.info(
                "Skipping OPPO idle confirmation; no player port is available | "
                "state=%s | category=%s",
                state.status.value,
                state.category.value,
            )
            return state, DeviceCommandResult.skipped(
                "No OPPO playback adapter configured for idle confirmation."
            )

        for poll_number in range(1, request.max_idle_confirmation_polls + 1):
            self._sleep(request.idle_confirmation_poll_interval_seconds)
            try:
                state = self._oppo_playback.get_playback_state()
            except Exception as exc:
                logger.exception(
                    "Unable to confirm OPPO idle state during playback finish; "
                    "continuing with last known state | state=%s | category=%s",
                    state.status.value,
                    state.category.value,
                )
                return state, DeviceCommandResult.failed(
                    f"OPPO idle confirmation failed: {type(exc).__name__}: {exc}"
                )

            logger.info(
                "OPPO finish idle confirmation | poll=%s | state=%s | category=%s",
                poll_number,
                state.status.value,
                state.category.value,
            )

            if state.category == OppoPlaybackCategory.IDLE:
                return state, DeviceCommandResult.success(
                    "OPPO idle state confirmed."
                )

        logger.warning(
            "OPPO did not report idle before finish continuation | state=%s | "
            "category=%s",
            state.status.value,
            state.category.value,
        )
        return state, DeviceCommandResult.failed(
            "OPPO did not report idle before finish continuation."
        )

    def _cleanup_player_after_finish(
        self,
        player_idle_result: DeviceCommandResult,
    ) -> DeviceCommandResult:
        if self._oppo_playback is None:
            return player_idle_result

        cleanup = getattr(self._oppo_playback, "cleanup_after_playback_finish", None)
        if cleanup is None:
            return player_idle_result

        try:
            cleanup_result = cleanup()
        except Exception as exc:
            logger.exception("Unable to run OPPO playback finish cleanup")
            cleanup_result = DeviceCommandResult.failed(
                f"OPPO playback finish cleanup failed: {type(exc).__name__}: {exc}"
            )

        logger.info(
            "OPPO playback finish cleanup | status=%s | detail=%s",
            cleanup_result.status.value,
            cleanup_result.detail,
        )

        if player_idle_result.status == DeviceCommandStatus.FAILED:
            return player_idle_result
        if cleanup_result.status == DeviceCommandStatus.FAILED:
            return cleanup_result
        if cleanup_result.status == DeviceCommandStatus.SKIPPED:
            return player_idle_result

        return DeviceCommandResult.success(
            f"{player_idle_result.detail}; {cleanup_result.detail}"
        )

    def _return_tv_to_app(
        self,
        request: PlaybackFinishRequest,
    ) -> DeviceCommandResult:
        if not request.tv_enabled:
            logger.info("Skipping TV app restore after playback finish: TV control is disabled.")
            return DeviceCommandResult.skipped("TV app restore is disabled.")

        if _player_is_in_screen_saver(request):
            logger.info(
                "Skipping TV app restore after playback finish: OPPO is in screen "
                "saver, the player is likely still paused rather than finished."
            )
            return DeviceCommandResult.skipped(
                "OPPO is in screen saver; treating as still paused."
            )

        if self._television is None:
            logger.info("Skipping TV app restore after playback finish: no TV adapter configured.")
            return DeviceCommandResult.skipped("TV adapter not configured.")

        logger.info(
            "Returning TV after playback finish | app_id=%s",
            request.previous_tv_app_id,
        )
        try:
            return self._television.launch_app(request.previous_tv_app_id)
        except Exception as exc:
            logger.exception("Unable to return TV after playback finish")
            return DeviceCommandResult.failed(
                f"TV app restore failed: {type(exc).__name__}: {exc}"
            )

    def _restore_av_tv_audio(
        self,
        request: PlaybackFinishRequest,
    ) -> DeviceCommandResult:
        if not request.av_enabled:
            logger.info("Skipping AV audio restore after playback finish: AV control is disabled.")
            return DeviceCommandResult.skipped("AV TV audio restore is disabled.")

        if _player_is_in_screen_saver(request):
            logger.info(
                "Skipping AV audio restore after playback finish: OPPO is in "
                "screen saver, the player is likely still paused rather than finished."
            )
            return DeviceCommandResult.skipped(
                "OPPO is in screen saver; treating as still paused."
            )

        if self._av_receiver is None:
            return DeviceCommandResult.skipped("No AV receiver adapter configured.")

        logger.info("Restoring AV receiver after playback finish.")
        try:
            return self._av_receiver.restore_tv_audio()
        except Exception as exc:
            logger.exception("Unable to restore AV receiver after playback finish")
            return DeviceCommandResult.failed(
                f"AV TV audio restore failed: {type(exc).__name__}: {exc}"
            )


def _player_is_in_screen_saver(request: PlaybackFinishRequest) -> bool:
    # Defense in depth: a SCREEN_SAVER final state means the OPPO went idle
    # while monitoring gave up, not that the user actually stopped. Restoring
    # the room here would interrupt a session that is, in practice, still
    # paused. See the screen-saver carve-out in polling_observation_strategy.py.
    return request.final_player_state.status == OppoPlaybackStatus.SCREEN_SAVER
