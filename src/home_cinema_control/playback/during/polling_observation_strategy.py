from __future__ import annotations

import logging
import time
from typing import Protocol

from home_cinema_control.devices.oppo.playback_state import (
    ACTIVE_PLAYBACK_STATUSES,
    OppoPlaybackCategory,
    OppoPlaybackStatus,
)
from home_cinema_control.playback.during.models import (
    PlaybackMonitoringRequest,
    PlaybackMonitoringResult,
    PlaybackMonitoringStopReason,
)
from home_cinema_control.playback.during.natural_end import (
    is_near_expected_end,
    is_polling_natural_end_reset,
)
from home_cinema_control.playback.ports import OppoPlaybackPort
from home_cinema_control.playback.startup.models import (
    OppoPlaybackPosition,
    OppoPlaybackState,
)

logger = logging.getLogger(__name__)


class PlaybackProgressReporter(Protocol):
    def progress(
        self,
        *,
        position_seconds: int,
        duration_seconds: int,
        is_paused: bool = False,
        is_muted: bool = False,
    ): ...


class PollingPlaybackObservationStrategy:
    """Monitor active OPPO playback and report media-server progress.

    QPL is the source of truth for player state and is polled frequently.
    getplayingtime is only used as a progress checkpoint and is intentionally
    polled less often because the OPPO HTTP API can become temporarily
    unavailable during title transitions.

    A paused OPPO can eventually report SCREEN_SAVER through QPL. That must not
    be treated as playback completion by itself: it is a long-pause state. We
    keep monitoring it until the player reports a real resume state or another
    idle state such as HOME_MENU / MEDIA_CENTER.
    """

    def __init__(
        self,
        *,
        oppo_playback: OppoPlaybackPort,
        progress_reporter: PlaybackProgressReporter | None = None,
        sleep=time.sleep,
    ) -> None:
        self._oppo_playback = oppo_playback
        self._progress_reporter = progress_reporter
        self._sleep = sleep

    def monitor_until_stopped(
        self,
        request: PlaybackMonitoringRequest,
    ) -> PlaybackMonitoringResult:
        last_position_seconds = request.initial_position_seconds
        last_duration_seconds = max(0, request.expected_duration_seconds)
        transition_polls = 0
        end_of_media_polls = 0
        position_read_failures = 0
        seconds_since_position_poll = 0.0
        elapsed_monitoring_seconds = 0.0
        paused_screensaver_logged = False

        final_state = self._oppo_playback.get_playback_state()
        last_active_state = _active_state_or_none(final_state) or request.last_active_state
        stop_reason = PlaybackMonitoringStopReason.PLAYER_IDLE

        while _should_continue_monitoring(
            final_state=final_state,
            last_active_state=last_active_state,
        ):
            self._sleep(request.poll_interval_seconds)
            elapsed_monitoring_seconds += request.poll_interval_seconds
            final_state = self._oppo_playback.get_playback_state()

            if _is_paused_screensaver_state(final_state, last_active_state):
                transition_polls = 0
                end_of_media_polls = 0
                seconds_since_position_poll += request.poll_interval_seconds

                if not paused_screensaver_logged:
                    logger.info(
                        "OPPO entered screen saver while paused; keeping playback "
                        "monitoring alive | last_position=%s | last_duration=%s",
                        last_position_seconds,
                        last_duration_seconds,
                    )
                    paused_screensaver_logged = True

                if _should_poll_position(
                    seconds_since_position_poll=seconds_since_position_poll,
                    progress_interval_seconds=request.progress_interval_seconds,
                ):
                    seconds_since_position_poll = 0.0
                    self._report_last_known_paused_progress(
                        request=request,
                        position_seconds=last_position_seconds,
                        duration_seconds=last_duration_seconds,
                    )

                if _monitoring_window_expired(
                    elapsed_seconds=elapsed_monitoring_seconds,
                    timeout_seconds=request.monitoring_timeout_seconds,
                ):
                    stop_reason = (
                        PlaybackMonitoringStopReason.OBSERVATION_WINDOW_EXPIRED
                    )
                    break

                continue

            paused_screensaver_logged = False
            last_active_state = _active_state_or_none(final_state) or last_active_state

            if final_state.category != OppoPlaybackCategory.ACTIVE:
                if is_near_expected_end(
                    position_seconds=last_position_seconds,
                    expected_duration_seconds=request.expected_duration_seconds,
                    tolerance_seconds=request.natural_end_reset_tolerance_seconds,
                ):
                    logger.info(
                        "OPPO polling detected transition after expected media end | "
                        "last_position=%s | expected_duration=%s | state=%s | "
                        "category=%s",
                        last_position_seconds,
                        request.expected_duration_seconds,
                        final_state.status.value,
                        final_state.category.value,
                    )
                    stop_reason = PlaybackMonitoringStopReason.NATURAL_END
                    break

                transition_polls += 1
                if transition_polls >= request.max_transition_polls:
                    logger.warning(
                        "OPPO playback monitoring stopped after transition grace | "
                        "polls=%s | state=%s | category=%s",
                        transition_polls,
                        final_state.status.value,
                        final_state.category.value,
                    )
                    stop_reason = (
                        PlaybackMonitoringStopReason.TRANSITION_GRACE_EXCEEDED
                    )
                    break

                if _monitoring_window_expired(
                    elapsed_seconds=elapsed_monitoring_seconds,
                    timeout_seconds=request.monitoring_timeout_seconds,
                ):
                    stop_reason = (
                        PlaybackMonitoringStopReason.OBSERVATION_WINDOW_EXPIRED
                    )
                    break

                continue

            transition_polls = 0
            seconds_since_position_poll += request.poll_interval_seconds

            if not _should_poll_position(
                seconds_since_position_poll=seconds_since_position_poll,
                progress_interval_seconds=request.progress_interval_seconds,
            ):
                if _monitoring_window_expired(
                    elapsed_seconds=elapsed_monitoring_seconds,
                    timeout_seconds=request.monitoring_timeout_seconds,
                ):
                    stop_reason = (
                        PlaybackMonitoringStopReason.OBSERVATION_WINDOW_EXPIRED
                    )
                    break
                continue

            seconds_since_position_poll = 0.0

            try:
                position = self._oppo_playback.get_playback_position()
            except Exception:
                position_read_failures += 1
                logger.warning(
                    "OPPO playback position read failed while QPL still reports "
                    "active playback | failures=%s | state=%s | category=%s | "
                    "last_position=%s | last_duration=%s",
                    position_read_failures,
                    final_state.status.value,
                    final_state.category.value,
                    last_position_seconds,
                    last_duration_seconds,
                    exc_info=True,
                )
                if _monitoring_window_expired(
                    elapsed_seconds=elapsed_monitoring_seconds,
                    timeout_seconds=request.monitoring_timeout_seconds,
                ):
                    stop_reason = (
                        PlaybackMonitoringStopReason.OBSERVATION_WINDOW_EXPIRED
                    )
                    break
                continue

            position_read_failures = 0
            normalized_position = _normalize_playback_position(position)

            logger.debug(
                "OPPO playback position | current=%s | total=%s | state=%s",
                position.current_seconds,
                position.total_seconds,
                final_state.status.value,
            )

            if not position.has_valid_position:
                if _monitoring_window_expired(
                    elapsed_seconds=elapsed_monitoring_seconds,
                    timeout_seconds=request.monitoring_timeout_seconds,
                ):
                    stop_reason = (
                        PlaybackMonitoringStopReason.OBSERVATION_WINDOW_EXPIRED
                    )
                    break
                continue

            if is_polling_natural_end_reset(
                last_position_seconds=last_position_seconds,
                current_position_seconds=normalized_position.current_seconds,
                current_duration_seconds=normalized_position.total_seconds,
                expected_duration_seconds=request.expected_duration_seconds,
                tolerance_seconds=request.natural_end_reset_tolerance_seconds,
            ):
                logger.info(
                    "OPPO polling detected playback reset after expected media end | "
                    "last_position=%s | expected_duration=%s | current=%s | total=%s",
                    last_position_seconds,
                    request.expected_duration_seconds,
                    normalized_position.current_seconds,
                    normalized_position.total_seconds,
                )
                stop_reason = PlaybackMonitoringStopReason.NATURAL_END
                break

            last_position_seconds = normalized_position.current_seconds
            last_duration_seconds = normalized_position.total_seconds

            if _is_expected_end_of_media_position(
                position,
                expected_duration_seconds=request.expected_duration_seconds,
                tolerance_seconds=request.natural_end_reset_tolerance_seconds,
            ):
                end_of_media_polls += 1
                if end_of_media_polls >= request.max_end_of_media_polls:
                    logger.info(
                        "OPPO playback monitoring stopped at natural media end | "
                        "polls=%s | position=%s | duration=%s | state=%s",
                        end_of_media_polls,
                        normalized_position.current_seconds,
                        normalized_position.total_seconds,
                        final_state.status.value,
                    )
                    stop_reason = PlaybackMonitoringStopReason.NATURAL_END
                    break
            else:
                end_of_media_polls = 0

            self._report_progress(
                request=request,
                position=normalized_position,
                playback_state=final_state,
            )

            if _monitoring_window_expired(
                elapsed_seconds=elapsed_monitoring_seconds,
                timeout_seconds=request.monitoring_timeout_seconds,
            ):
                stop_reason = PlaybackMonitoringStopReason.OBSERVATION_WINDOW_EXPIRED
                break

        return PlaybackMonitoringResult(
            position_seconds=last_position_seconds,
            duration_seconds=last_duration_seconds,
            final_state=final_state,
            stop_reason=stop_reason,
        )

    def _report_progress(
        self,
        *,
        request: PlaybackMonitoringRequest,
        position: OppoPlaybackPosition,
        playback_state: OppoPlaybackState,
    ) -> None:
        if not request.report_progress:
            return

        if self._progress_reporter is None:
            return

        self._progress_reporter.progress(
            position_seconds=position.current_seconds,
            duration_seconds=position.total_seconds,
            is_paused=_is_paused(playback_state),
            is_muted=request.is_muted,
        )

    def _report_last_known_paused_progress(
        self,
        *,
        request: PlaybackMonitoringRequest,
        position_seconds: int,
        duration_seconds: int,
    ) -> None:
        if duration_seconds <= 0:
            return

        self._report_progress(
            request=request,
            position=OppoPlaybackPosition(
                current_seconds=position_seconds,
                total_seconds=duration_seconds,
                raw_response="last-known-paused-position",
            ),
            playback_state=OppoPlaybackState(
                status=OppoPlaybackStatus.PAUSE,
                category=OppoPlaybackCategory.ACTIVE,
                raw_response="@OK PAUSE (screen saver)",
                ok=True,
            ),
        )


def _should_continue_monitoring(
    *,
    final_state: OppoPlaybackState,
    last_active_state: OppoPlaybackState | None,
) -> bool:
    return final_state.category in {
        OppoPlaybackCategory.ACTIVE,
        OppoPlaybackCategory.TRANSITION,
    } or (
        final_state.category == OppoPlaybackCategory.UNKNOWN
        and last_active_state is not None
    ) or _is_paused_screensaver_state(final_state, last_active_state)


def _active_state_or_none(
    playback_state: OppoPlaybackState,
) -> OppoPlaybackState | None:
    if playback_state.category == OppoPlaybackCategory.ACTIVE:
        return playback_state

    return None


def _is_paused_screensaver_state(
    playback_state: OppoPlaybackState,
    last_active_state: OppoPlaybackState | None,
) -> bool:
    return (
        playback_state.status == OppoPlaybackStatus.SCREEN_SAVER
        and last_active_state is not None
        # The bridge may miss the PAUSE state between poll intervals before
        # screen saver activates. STOP → SCREEN_SAVER cannot occur within
        # a monitoring session: OPPO always shows HOME_MENU for minutes
        # between them, and the loop exits at HOME_MENU (IDLE, not SCREEN_SAVER).
        and last_active_state.status in ACTIVE_PLAYBACK_STATUSES
    )


def _should_poll_position(
    *,
    seconds_since_position_poll: float,
    progress_interval_seconds: float,
) -> bool:
    if progress_interval_seconds <= 0:
        return True

    return seconds_since_position_poll >= progress_interval_seconds


def _monitoring_window_expired(
    *,
    elapsed_seconds: float,
    timeout_seconds: float | None,
) -> bool:
    return timeout_seconds is not None and elapsed_seconds >= timeout_seconds


def _is_paused(playback_state: OppoPlaybackState) -> bool:
    return playback_state.status == OppoPlaybackStatus.PAUSE


def _is_expected_end_of_media_position(
    position: OppoPlaybackPosition,
    *,
    expected_duration_seconds: int,
    tolerance_seconds: int,
) -> bool:
    if not is_near_expected_end(
        position_seconds=position.current_seconds,
        expected_duration_seconds=expected_duration_seconds,
        tolerance_seconds=tolerance_seconds,
    ):
        return False

    return (
        position.total_seconds > 0
        and position.current_seconds >= position.total_seconds
    )


def _normalize_playback_position(
    position: OppoPlaybackPosition,
) -> OppoPlaybackPosition:
    if not (
        position.total_seconds > 0
        and position.current_seconds >= position.total_seconds
    ):
        return position

    return OppoPlaybackPosition(
        current_seconds=position.total_seconds,
        total_seconds=position.total_seconds,
        raw_response=position.raw_response,
    )
