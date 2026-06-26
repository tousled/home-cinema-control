from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Protocol

from home_cinema_control.devices.oppo.observed_events import (
    translate_oppo_verbose_event,
)
from home_cinema_control.devices.oppo.verbose_events import OppoVerboseEvent
from home_cinema_control.playback.player_state import (
    PlayerPlaybackLifecyclePhase,
    PlayerPlaybackState,
    PlayerPlaybackStatus,
)
from home_cinema_control.playback.during.models import (
    PlaybackMonitoringRequest,
    PlaybackMonitoringResult,
    PlaybackMonitoringStopReason,
)
from home_cinema_control.playback.during.natural_end import (
    is_oppo_end_of_content,
)
from home_cinema_control.playback.observed_events import (
    ObservedPlaybackEvent,
    ObservedPlaybackEventType,
    ObservedPlaybackState,
)
from home_cinema_control.playback.startup.models import (
    DeviceCommandResult,
)

logger = logging.getLogger(__name__)

# The OPPO reports the real title duration (``total_time``) over HTTP, not in
# the SVM3 event stream, so it is fetched once and cached. These bound how
# often the lookup is retried before a valid (>= floor) total is latched, so a
# disc that never reports one cannot drive an unbounded request loop.
_TOTAL_LOOKUP_INTERVAL_UPDATES = 5
_MAX_TOTAL_LOOKUP_ATTEMPTS = 60


class VerboseObservationEventSource(Protocol):
    def listen(
        self,
        *,
        verbose_mode: int = 2,
        duration_seconds: float | None = None,
        initial_commands: list[str] | None = None,
        keepalive_command: str | None = None,
        keepalive_interval_seconds: float = 10.0,
        restore_verbose_mode: bool = True,
        utc_idle_timeout_seconds: float | None = None,
        stop_requested=None,
    ): ...


class PlaybackProgressReporter(Protocol):
    def progress(
        self,
        *,
        position_seconds: int,
        duration_seconds: int,
        is_paused: bool = False,
        is_muted: bool = False,
    ): ...


class ObservedPlaybackEventReporter(Protocol):
    def report(self, event: ObservedPlaybackEvent): ...


class VerbosePlaybackObservationStrategy:
    """Monitor playback through one persistent OPPO SVM 3 event stream."""

    def __init__(
        self,
        *,
        event_source: VerboseObservationEventSource,
        progress_reporter: PlaybackProgressReporter | None = None,
        observed_event_reporter: ObservedPlaybackEventReporter | None = None,
            oppo_total_provider: Callable[[], int] | None = None,
    ) -> None:
        self._event_source = event_source
        self._progress_reporter = progress_reporter
        self._observed_event_reporter = observed_event_reporter
        self._deferred_audio_selector: Callable[[], DeviceCommandResult] | None = None
        self._oppo_total_provider = oppo_total_provider

    def set_observed_event_reporter(
        self,
        reporter: ObservedPlaybackEventReporter,
    ) -> None:
        self._observed_event_reporter = reporter

    def set_deferred_audio_selector(
        self,
        selector: Callable[[], DeviceCommandResult],
    ) -> None:
        self._deferred_audio_selector = selector

    def _maybe_latch_oppo_total(
            self,
            state: "_MonitoringState",
            request: PlaybackMonitoringRequest,
    ) -> None:
        """Latch the OPPO-reported title total once it is a feature-sized value.

        ``total_time`` is stable for the whole title and only available over
        HTTP, so it is fetched at most once and reused. Retries are throttled
        and capped so prerolls/seeks at startup (which report a tiny total) do
        not cause an unbounded lookup loop.
        """
        if state.latched_total_seconds is not None:
            return
        if self._oppo_total_provider is None:
            return
        if state.total_lookup_attempts >= _MAX_TOTAL_LOOKUP_ATTEMPTS:
            return

        state.updates_since_total_lookup += 1
        if (
                state.total_lookup_attempts > 0
                and state.updates_since_total_lookup < _TOTAL_LOOKUP_INTERVAL_UPDATES
        ):
            return

        state.updates_since_total_lookup = 0
        state.total_lookup_attempts += 1
        try:
            total_seconds = int(self._oppo_total_provider())
        except Exception:
            logger.warning("SVM3 OPPO total lookup failed.", exc_info=True)
            return

        if total_seconds >= request.natural_end_minimum_total_seconds:
            state.latched_total_seconds = total_seconds
            state.duration_seconds = total_seconds
            logger.info("SVM3 latched OPPO total | total=%s", total_seconds)

    def _reached_oppo_end_of_content(
            self,
            state: "_MonitoringState",
            request: PlaybackMonitoringRequest,
    ) -> bool:
        if state.latched_total_seconds is None:
            return False

        return is_oppo_end_of_content(
            current_seconds=state.last_position_seconds,
            total_seconds=state.latched_total_seconds,
            tolerance_seconds=request.natural_end_tolerance_seconds,
            minimum_total_seconds=request.natural_end_minimum_total_seconds,
        )

    def monitor_until_stopped(
        self,
        request: PlaybackMonitoringRequest,
    ) -> PlaybackMonitoringResult:
        state = _MonitoringState(
            last_position_seconds=request.initial_position_seconds,
            last_nonzero_position_seconds=max(0, request.initial_position_seconds),
            duration_seconds=max(0, request.expected_duration_seconds),
            is_paused=request.is_paused,
            seconds_since_progress=0.0,
        )
        final_player_state = _player_state(
            PlayerPlaybackStatus.UNKNOWN,
            PlayerPlaybackLifecyclePhase.UNKNOWN,
            raw_response="@SVM3 PLAYBACK MONITORING STARTED",
        )
        stop_reason = PlaybackMonitoringStopReason.EVENT_WATCHDOG_EXPIRED

        for event in self._event_source.listen(
            verbose_mode=3,
            restore_verbose_mode=False,
            utc_idle_timeout_seconds=request.event_watchdog_seconds,
        ):
            observed_event = translate_oppo_verbose_event(event)

            if _is_stop_event(observed_event):
                state.pending_stop_event = observed_event
                final_player_state = _player_state(
                    PlayerPlaybackStatus.STOP,
                    PlayerPlaybackLifecyclePhase.TRANSITION,
                    raw_response=event.raw,
                )
                continue

            if state.pending_stop_event is not None:
                if _is_play_event(observed_event):
                    logger.info(
                        "SVM3 pending stop cancelled by subsequent playback start | "
                        "stop_raw=%s | play_raw=%s",
                        state.pending_stop_event.raw,
                        event.raw,
                    )
                    state.pending_stop_event = None
                    state.is_paused = False
                    final_player_state = _player_state(
                        PlayerPlaybackStatus.PLAY,
                        PlayerPlaybackLifecyclePhase.ACTIVE,
                        raw_response=event.raw,
                    )
                    continue

                if _is_terminal_idle_event(event):
                    logger.info(
                        "SVM3 playback monitoring stopped after OPPO idle event | "
                        "stop_raw=%s | idle_raw=%s | position=%s",
                        state.pending_stop_event.raw,
                        event.raw,
                        state.final_position_seconds,
                    )
                    stop_reason = PlaybackMonitoringStopReason.PLAYER_IDLE
                    final_player_state = _terminal_idle_state(event)
                    state.pending_stop_event = None
                    break

                continue

            if _is_position_update(observed_event):
                observed_position_seconds = max(
                    0,
                    int(observed_event.position_seconds or 0),
                )
                state.last_position_seconds = observed_position_seconds
                if state.last_position_seconds > 0:
                    state.last_nonzero_position_seconds = state.last_position_seconds

                self._maybe_latch_oppo_total(state, request)
                if self._reached_oppo_end_of_content(state, request):
                    stop_reason = PlaybackMonitoringStopReason.NATURAL_END
                    final_player_state = _player_state(
                        PlayerPlaybackStatus.PLAY,
                        PlayerPlaybackLifecyclePhase.ACTIVE,
                        raw_response=event.raw,
                    )
                    logger.info(
                        "SVM3 detected end of content via OPPO total | "
                        "position=%s | total=%s | raw=%s",
                        state.last_position_seconds,
                        state.latched_total_seconds,
                        event.raw,
                    )
                    break

                state.seconds_since_progress += 1.0
                self._report_observed_event(observed_event)
                self._report_progress_if_due(request, state)
                continue

            if (
                observed_event is not None
                and observed_event.event_type
                == ObservedPlaybackEventType.AUDIO_TRACK_CHANGED
                and observed_event.player_audio_track_index
                == state.last_audio_track_index
            ):
                logger.debug(
                    "SVM3 skipping duplicate AudioTrackChanged | index=%s | raw=%s",
                    observed_event.player_audio_track_index,
                    observed_event.raw,
                )
                continue

            if observed_event is not None:
                if (
                    observed_event.event_type
                    == ObservedPlaybackEventType.AUDIO_TRACK_CHANGED
                ):
                    state.last_audio_track_index = (
                        observed_event.player_audio_track_index
                    )
                self._report_observed_event(observed_event)
                final_player_state = _state_from_observed_event(
                    observed_event,
                    fallback=final_player_state,
                )

            if _is_pause_event(observed_event):
                state.is_paused = True
                continue

            if _is_play_event(observed_event):
                state.is_paused = False
                if (
                    not state.deferred_audio_applied
                    and self._deferred_audio_selector is not None
                ):
                    state.deferred_audio_applied = True
                    self._apply_deferred_audio()
                continue

            if _is_terminal_idle_event(event):
                logger.info(
                    "SVM3 playback monitoring stopped at idle event | raw=%s | "
                    "position=%s",
                    event.raw,
                    state.final_position_seconds,
                )
                stop_reason = PlaybackMonitoringStopReason.PLAYER_IDLE
                final_player_state = _terminal_idle_state(event)
                break

        if state.pending_stop_event is not None:
            stop_reason = PlaybackMonitoringStopReason.PLAYER_IDLE
            final_player_state = _player_state(
                PlayerPlaybackStatus.STOP,
                PlayerPlaybackLifecyclePhase.TRANSITION,
                raw_response=state.pending_stop_event.raw,
            )

        return PlaybackMonitoringResult(
            position_seconds=state.final_position_seconds,
            duration_seconds=state.duration_seconds,
            final_state=final_player_state,
            stop_reason=stop_reason,
        )

    def _report_observed_event(self, event: ObservedPlaybackEvent) -> None:
        if self._observed_event_reporter is None:
            return

        result = self._observed_event_reporter.report(event)
        log = logger.debug if result.event_name == "PositionUpdate" else logger.info
        log(
            "Observed OPPO event report result | raw=%s | reported=%s | "
            "event=%s | detail=%s",
            event.raw,
            result.reported,
            result.event_name,
            result.detail,
        )

    def _apply_deferred_audio(self) -> None:
        logger.info(
            "SVM3 detected first PLAY event; attempting deferred audio track selection."
        )
        try:
            result = self._deferred_audio_selector()
            if result.successful:
                logger.info(
                    "Deferred audio track selection applied | detail=%s", result.detail
                )
            else:
                logger.warning(
                    "Deferred audio track selection failed | detail=%s", result.detail
                )
        except Exception:
            logger.exception("Deferred audio track selection raised unexpectedly.")

    def _report_progress_if_due(
        self,
        request: PlaybackMonitoringRequest,
        state: "_MonitoringState",
    ) -> None:
        if self._observed_event_reporter is not None:
            return

        if not request.report_progress:
            return

        if self._progress_reporter is None:
            return

        if request.progress_interval_seconds > 0:
            if state.seconds_since_progress < request.progress_interval_seconds:
                return

        state.seconds_since_progress = 0.0
        self._progress_reporter.progress(
            position_seconds=state.last_position_seconds,
            duration_seconds=state.duration_seconds,
            is_paused=state.is_paused,
            is_muted=request.is_muted,
        )


class _MonitoringState:
    def __init__(
        self,
        *,
        last_position_seconds: int,
        last_nonzero_position_seconds: int,
        duration_seconds: int,
        is_paused: bool,
        seconds_since_progress: float,
    ) -> None:
        self.last_position_seconds = last_position_seconds
        self.last_nonzero_position_seconds = last_nonzero_position_seconds
        self.duration_seconds = duration_seconds
        self.is_paused = is_paused
        self.seconds_since_progress = seconds_since_progress
        self.pending_stop_event: ObservedPlaybackEvent | None = None
        self.last_audio_track_index: int | None = None
        self.deferred_audio_applied: bool = False
        self.latched_total_seconds: int | None = None
        self.total_lookup_attempts: int = 0
        self.updates_since_total_lookup: int = 0

    @property
    def final_position_seconds(self) -> int:
        if self.last_position_seconds > 0:
            return self.last_position_seconds

        return self.last_nonzero_position_seconds


def _state_from_observed_event(
    event: ObservedPlaybackEvent,
    *,
    fallback: PlayerPlaybackState,
) -> PlayerPlaybackState:
    if event.event_type != ObservedPlaybackEventType.PLAYBACK_STATE_CHANGED:
        return fallback

    if event.playback_state == ObservedPlaybackState.PLAYING:
        return _player_state(
            PlayerPlaybackStatus.PLAY,
            PlayerPlaybackLifecyclePhase.ACTIVE,
            raw_response=event.raw,
        )

    if event.playback_state == ObservedPlaybackState.PAUSED:
        return _player_state(
            PlayerPlaybackStatus.PAUSE,
            PlayerPlaybackLifecyclePhase.ACTIVE,
            raw_response=event.raw,
        )

    if event.playback_state == ObservedPlaybackState.STOPPED:
        return _player_state(
            PlayerPlaybackStatus.STOP,
            PlayerPlaybackLifecyclePhase.TRANSITION,
            raw_response=event.raw,
        )

    return fallback


def _player_state(
    status: PlayerPlaybackStatus,
    lifecycle_phase: PlayerPlaybackLifecyclePhase,
    *,
    raw_response: str,
) -> PlayerPlaybackState:
    return PlayerPlaybackState(
        status=status,
        lifecycle_phase=lifecycle_phase,
        raw_response=raw_response,
        ok=True,
    )


def _is_position_update(event: ObservedPlaybackEvent | None) -> bool:
    return (
        event is not None
        and event.event_type == ObservedPlaybackEventType.POSITION_UPDATED
    )


def _is_pause_event(event: ObservedPlaybackEvent | None) -> bool:
    return (
        event is not None
        and event.event_type == ObservedPlaybackEventType.PLAYBACK_STATE_CHANGED
        and event.playback_state == ObservedPlaybackState.PAUSED
    )


def _is_play_event(event: ObservedPlaybackEvent | None) -> bool:
    return (
        event is not None
        and event.event_type == ObservedPlaybackEventType.PLAYBACK_STATE_CHANGED
        and event.playback_state == ObservedPlaybackState.PLAYING
    )


def _is_stop_event(event: ObservedPlaybackEvent | None) -> bool:
    return (
        event is not None
        and event.event_type == ObservedPlaybackEventType.PLAYBACK_STATE_CHANGED
        and event.playback_state == ObservedPlaybackState.STOPPED
    )


def _is_terminal_idle_event(event: OppoVerboseEvent) -> bool:
    return event.code == "UPL" and event.payload.strip().upper() in {
        "MCTR",
        "HOME",
        "DLNA",
    }


def _terminal_idle_state(event: OppoVerboseEvent) -> PlayerPlaybackState:
    status = (
        PlayerPlaybackStatus.MEDIA_CENTER
        if event.payload.strip().upper() == "MCTR"
        else PlayerPlaybackStatus.HOME_MENU
    )
    return _player_state(
        status,
        PlayerPlaybackLifecyclePhase.IDLE,
        raw_response=event.raw,
    )
