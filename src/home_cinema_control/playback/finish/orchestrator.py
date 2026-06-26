from __future__ import annotations

import logging
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Protocol

from home_cinema_control.playback.player_state import (
    PlayerPlaybackLifecyclePhase,
)
from home_cinema_control.playback.finish.models import (
    PlaybackFinishRequest,
    PlaybackFinishResult,
)
from home_cinema_control.playback.ports import (
    AvReceiverOutputPort,
    MediaPlayerPort,
    TelevisionOutputPort,
)
from home_cinema_control.playback.player_state import PlayerPlaybackState
from home_cinema_control.playback.restoration import (
    PlaybackOutputRestorationRequest,
    PlaybackRestorationService,
)
from home_cinema_control.playback.startup.models import (
    DeviceCommandResult,
    DeviceCommandStatus,
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
        media_player: MediaPlayerPort | None = None,
        sleep=time.sleep,
    ) -> None:
        self._stopped_reporter = stopped_reporter
        self._television = television
        self._av_receiver = av_receiver
        self._media_player = media_player
        self._restoration = PlaybackRestorationService(
            television=television,
            av_receiver=av_receiver,
            media_player=media_player,
        )
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
                self._restoration.cleanup_after_confirmed_player_state,
                player_idle_result,
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

        output_restoration_result = self._restoration.restore_outputs(
            PlaybackOutputRestorationRequest(
                previous_tv_app_id=request.previous_tv_app_id,
                tv_enabled=request.tv_enabled,
                av_enabled=request.av_enabled,
                final_player_state=final_player_state,
                log_context="playback finish",
            )
        )

        return PlaybackFinishResult(
            media_server_stop_result=media_server_stop_result,
            player_idle_result=player_idle_result,
            tv_app_result=output_restoration_result.tv_app_result,
            av_audio_result=output_restoration_result.av_audio_result,
            final_player_state=final_player_state,
        )

    def _close_and_confirm_player_state(
        self,
        request: PlaybackFinishRequest,
    ) -> tuple[PlayerPlaybackState, DeviceCommandResult]:
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

        if request.final_player_state.lifecycle_phase == PlayerPlaybackLifecyclePhase.IDLE:
            return DeviceCommandResult.skipped("Player is already idle after media end.")

        if self._media_player is None:
            return DeviceCommandResult.skipped(
                "No OPPO playback adapter configured for media-end close."
            )

        logger.info(
            "Closing OPPO playback after natural media end | state=%s | lifecycle_phase=%s",
            request.final_player_state.status.value,
            request.final_player_state.lifecycle_phase.value,
        )
        return self._media_player.stop()

    def _confirm_idle_state(
        self,
        request: PlaybackFinishRequest,
    ) -> tuple[PlayerPlaybackState, DeviceCommandResult]:
        state = request.final_player_state
        if state.lifecycle_phase == PlayerPlaybackLifecyclePhase.IDLE:
            return state, DeviceCommandResult.success("OPPO already idle.")

        if self._media_player is None:
            logger.info(
                "Skipping OPPO idle confirmation; no player port is available | "
                "state=%s | lifecycle_phase=%s",
                state.status.value,
                state.lifecycle_phase.value,
            )
            return state, DeviceCommandResult.skipped(
                "No OPPO playback adapter configured for idle confirmation."
            )

        for poll_number in range(1, request.max_idle_confirmation_polls + 1):
            self._sleep(request.idle_confirmation_poll_interval_seconds)
            try:
                state = self._media_player.get_playback_state()
            except Exception as exc:
                logger.exception(
                    "Unable to confirm OPPO idle state during playback finish; "
                    "continuing with last known state | state=%s | lifecycle_phase=%s",
                    state.status.value,
                    state.lifecycle_phase.value,
                )
                return state, DeviceCommandResult.failed(
                    f"OPPO idle confirmation failed: {type(exc).__name__}: {exc}"
                )

            logger.info(
                "OPPO finish idle confirmation | poll=%s | state=%s | lifecycle_phase=%s",
                poll_number,
                state.status.value,
                state.lifecycle_phase.value,
            )

            if state.lifecycle_phase == PlayerPlaybackLifecyclePhase.IDLE:
                return state, DeviceCommandResult.success(
                    "OPPO idle state confirmed."
                )

        logger.warning(
            "OPPO did not report idle before finish continuation | state=%s | "
            "lifecycle_phase=%s",
            state.status.value,
            state.lifecycle_phase.value,
        )
        return state, DeviceCommandResult.failed(
            "OPPO did not report idle before finish continuation."
        )
