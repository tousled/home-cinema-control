from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
import logging
from typing import Protocol

from home_cinema_control.devices.oppo.constants import OPPO_TELNET_PORT
from home_cinema_control.devices.oppo.playback_command_control import (
    create_oppo_total_seconds_reader,
)
from home_cinema_control.devices.oppo.playback_state import OppoPlaybackCategory
from home_cinema_control.devices.oppo.svm_mode import OppoSVMModeClient
from home_cinema_control.devices.oppo.svm3_runtime import OppoSVM3PlaybackRuntime
from home_cinema_control.devices.oppo.verbose_events import OppoVerboseEventListener
from home_cinema_control.network.tcp import LoggingTcpClient
from home_cinema_control.playback.during.models import (
    PlaybackMonitoringRequest,
    PlaybackMonitoringResult,
    PlaybackMonitoringStopReason,
)
from home_cinema_control.playback.during.polling_observation_strategy import (
    PollingPlaybackObservationStrategy,
)
from home_cinema_control.playback.during.verbose_observation_strategy import (
    VerbosePlaybackObservationStrategy,
)

logger = logging.getLogger(__name__)


class ObservedPlaybackEventReporter(Protocol):
    def report(self, event): ...


class DuringPlaybackOrchestrator:
    """Use SVM3 observation when available, with polling as the safe fallback."""

    def __init__(
        self,
        *,
        config: dict,
        polling_orchestrator: PollingPlaybackObservationStrategy,
        progress_reporter=None,
        oppo_svm3_observation_orchestrator: VerbosePlaybackObservationStrategy
        | None = None,
        svm3_runtime: OppoSVM3PlaybackRuntime | None = None,
            oppo_total_provider: Callable[[], int] | None = None,
        tcp_client: LoggingTcpClient | None = None,
    ) -> None:
        self._config = config
        self._polling_orchestrator = polling_orchestrator
        self._svm3_runtime = svm3_runtime or _create_svm3_runtime(config)
        self._oppo_svm3_observation_orchestrator = (
            oppo_svm3_observation_orchestrator
            or VerbosePlaybackObservationStrategy(
                event_source=self._svm3_runtime,
                progress_reporter=progress_reporter,
            oppo_total_provider=(
                    oppo_total_provider or create_oppo_total_seconds_reader(config)
            ),
            )
        )
        self._svm_mode_client = OppoSVMModeClient(
            config,
            tcp_client=tcp_client,
            name="oppo-svm3-observation",
        )
        retry_initial_delay_seconds = _positive_float(
            config["oppo"].get("svm3_retry_initial_delay_seconds", 30),
            default=30,
        )
        self._retry_max_delay_seconds = _positive_float(
            config["oppo"].get("svm3_retry_max_delay_seconds", 120),
            default=120,
        )
        self._retry_initial_delay_seconds = min(
            retry_initial_delay_seconds,
            self._retry_max_delay_seconds,
        )
        self._retry_backoff = _float_greater_than(
            config["oppo"].get("svm3_retry_backoff", 2),
            default=2,
            minimum=1,
        )

    def set_observed_event_reporter(
        self,
        reporter: ObservedPlaybackEventReporter,
    ) -> None:
        self._oppo_svm3_observation_orchestrator.set_observed_event_reporter(reporter)

    def set_deferred_audio_selector(self, selector) -> None:
        self._oppo_svm3_observation_orchestrator.set_deferred_audio_selector(selector)

    def monitor_until_stopped(
        self,
        request: PlaybackMonitoringRequest,
    ) -> PlaybackMonitoringResult:
        current_request = request
        retry_delay_seconds = self._retry_initial_delay_seconds

        while True:
            result = self._monitor_with_svm3(current_request)
            if result is not None:
                current_request = _request_from_result(current_request, result)
                if result.stop_reason != PlaybackMonitoringStopReason.EVENT_WATCHDOG_EXPIRED:
                    return result

                logger.warning(
                    "OPPO SVM3 observation watchdog expired; continuing with "
                    "bounded polling before retry | position=%s | duration=%s | "
                    "retry_delay=%s",
                    result.position_seconds,
                    result.duration_seconds,
                    retry_delay_seconds,
                )

            polling_result = self._polling_orchestrator.monitor_until_stopped(
                replace(
                    current_request,
                    monitoring_timeout_seconds=retry_delay_seconds,
                )
            )
            current_request = _request_from_result(current_request, polling_result)

            if (
                polling_result.stop_reason
                != PlaybackMonitoringStopReason.OBSERVATION_WINDOW_EXPIRED
            ):
                return polling_result

            logger.info(
                "OPPO polling observation window expired; retrying SVM3 "
                "observation | position=%s | duration=%s | retry_delay=%s",
                polling_result.position_seconds,
                polling_result.duration_seconds,
                retry_delay_seconds,
            )
            retry_delay_seconds = min(
                self._retry_max_delay_seconds,
                retry_delay_seconds * self._retry_backoff,
            )

    def _monitor_with_svm3(
        self,
        request: PlaybackMonitoringRequest,
    ) -> PlaybackMonitoringResult | None:
        start_result = self._svm3_runtime.start()
        if not start_result.successful:
            logger.warning(
                "OPPO SVM3 observation unavailable; using bounded polling | "
                "detail=%s",
                start_result.detail,
            )
            self._svm3_runtime.stop()
            self._restore_svm0_safely()
            return None

        try:
            return self._oppo_svm3_observation_orchestrator.monitor_until_stopped(
                request
            )
        except Exception:
            logger.exception(
                "OPPO SVM3 observation failed; using bounded polling before retry."
            )
            return None
        finally:
            self._svm3_runtime.stop()
            self._restore_svm0_safely()

    def _restore_svm0(self):
        return self._svm_mode_client.set_mode(0)

    def _restore_svm0_safely(self) -> None:
        try:
            self._restore_svm0()
        except Exception:
            logger.exception("Failed to restore OPPO SVM 0 after SVM3 observation.")


def _create_svm3_runtime(config: dict) -> OppoSVM3PlaybackRuntime:
    oppo = config["oppo"]
    return OppoSVM3PlaybackRuntime(
        listener=OppoVerboseEventListener(
            host=oppo["ip"],
            port=int(config.get("OPPO_Port", OPPO_TELNET_PORT)),
            connect_timeout_seconds=float(oppo.get("connection_timeout_seconds", 3)),
            read_timeout_seconds=float(oppo.get("read_timeout_seconds", 0.5)),
        )
    )


def _request_from_result(
    request: PlaybackMonitoringRequest,
    result: PlaybackMonitoringResult,
) -> PlaybackMonitoringRequest:
    last_active_state = (
        result.final_state
        if result.final_state.category == OppoPlaybackCategory.ACTIVE
        else request.last_active_state
    )
    return replace(
        request,
        initial_position_seconds=result.position_seconds,
        monitoring_timeout_seconds=None,
        last_active_state=last_active_state,
    )


def _positive_float(value, *, default: float) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return default

    if parsed <= 0:
        return default

    return parsed


def _float_greater_than(value, *, default: float, minimum: float) -> float:
    parsed = _positive_float(value, default=default)
    if parsed <= minimum:
        return default

    return parsed
