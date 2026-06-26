import unittest

from home_cinema_control.playback.during.orchestrator import (
    DuringPlaybackOrchestrator,
)
from home_cinema_control.playback.during.models import (
    PlaybackMonitoringRequest,
    PlaybackMonitoringResult,
    PlaybackMonitoringStopReason,
)
from home_cinema_control.playback.player_state import (
    PlayerPlaybackLifecyclePhase,
    PlayerPlaybackState,
    PlayerPlaybackStatus,
)
from home_cinema_control.playback.startup.models import DeviceCommandResult


class DuringPlaybackOrchestratorTest(unittest.TestCase):
    def test_uses_svm3_when_runtime_starts_and_result_is_final(self):
        polling = RecordingPollingOrchestrator()
        svm3 = RecordingSVM3Orchestrator(
            _result(stop_reason=PlaybackMonitoringStopReason.PLAYER_IDLE)
        )
        runtime = RecordingSVM3Runtime(start_result=DeviceCommandResult.success("ok"))
        tcp = RecordingTcpClient(response="@OK 0")
        orchestrator = DuringPlaybackOrchestrator(
            config=_config(),
            polling_orchestrator=polling,
            oppo_svm3_observation_orchestrator=svm3,
            svm3_runtime=runtime,
            tcp_client=tcp,
        )

        result = orchestrator.monitor_until_stopped(PlaybackMonitoringRequest())

        self.assertEqual(12, result.position_seconds)
        self.assertEqual(0, polling.calls)
        self.assertEqual(1, svm3.calls)
        self.assertEqual(["start", "stop"], runtime.calls)
        self.assertEqual([b"#SVM 0\r"], tcp.payloads)

    def test_falls_back_to_polling_when_svm3_runtime_does_not_start(self):
        polling = RecordingPollingOrchestrator(
            _result(position_seconds=33, stop_reason=PlaybackMonitoringStopReason.PLAYER_IDLE)
        )
        svm3 = RecordingSVM3Orchestrator(_result())
        runtime = RecordingSVM3Runtime(start_result=DeviceCommandResult.failed("no svm3"))
        tcp = RecordingTcpClient(response="@OK 0")
        orchestrator = DuringPlaybackOrchestrator(
            config=_config(),
            polling_orchestrator=polling,
            oppo_svm3_observation_orchestrator=svm3,
            svm3_runtime=runtime,
            tcp_client=tcp,
        )

        result = orchestrator.monitor_until_stopped(PlaybackMonitoringRequest())

        self.assertEqual(33, result.position_seconds)
        self.assertEqual(1, polling.calls)
        self.assertEqual(0, svm3.calls)
        self.assertEqual(["start", "stop"], runtime.calls)
        self.assertEqual([b"#SVM 0\r"], tcp.payloads)

    def test_falls_back_to_polling_after_svm3_watchdog(self):
        polling = RecordingPollingOrchestrator(
            _result(position_seconds=44, stop_reason=PlaybackMonitoringStopReason.PLAYER_IDLE)
        )
        svm3 = RecordingSVM3Orchestrator(
            _result(
                position_seconds=22,
                stop_reason=PlaybackMonitoringStopReason.EVENT_WATCHDOG_EXPIRED,
            )
        )
        runtime = RecordingSVM3Runtime(start_result=DeviceCommandResult.success("ok"))
        tcp = RecordingTcpClient(response="@OK 0")
        orchestrator = DuringPlaybackOrchestrator(
            config=_config(),
            polling_orchestrator=polling,
            oppo_svm3_observation_orchestrator=svm3,
            svm3_runtime=runtime,
            tcp_client=tcp,
        )

        result = orchestrator.monitor_until_stopped(
            PlaybackMonitoringRequest(initial_position_seconds=5)
        )

        self.assertEqual(44, result.position_seconds)
        self.assertEqual(1, polling.calls)
        self.assertEqual(22, polling.requests[0].initial_position_seconds)
        self.assertEqual(30, polling.requests[0].monitoring_timeout_seconds)
        self.assertEqual(["start", "stop"], runtime.calls)
        self.assertEqual([b"#SVM 0\r"], tcp.payloads)

    def test_retries_svm3_after_bounded_polling_window_expires(self):
        polling = RecordingPollingOrchestrator(
            [
                _result(
                    position_seconds=33,
                    stop_reason=PlaybackMonitoringStopReason.OBSERVATION_WINDOW_EXPIRED,
                )
            ]
        )
        svm3 = RecordingSVM3Orchestrator(
            [
                _result(
                    position_seconds=22,
                    stop_reason=PlaybackMonitoringStopReason.EVENT_WATCHDOG_EXPIRED,
                ),
                _result(
                    position_seconds=55,
                    stop_reason=PlaybackMonitoringStopReason.PLAYER_IDLE,
                ),
            ]
        )
        runtime = RecordingSVM3Runtime(start_result=DeviceCommandResult.success("ok"))
        tcp = RecordingTcpClient(response="@OK 0")
        orchestrator = DuringPlaybackOrchestrator(
            config=_config(),
            polling_orchestrator=polling,
            oppo_svm3_observation_orchestrator=svm3,
            svm3_runtime=runtime,
            tcp_client=tcp,
        )

        result = orchestrator.monitor_until_stopped(
            PlaybackMonitoringRequest(initial_position_seconds=5)
        )

        self.assertEqual(55, result.position_seconds)
        self.assertEqual(2, svm3.calls)
        self.assertEqual(1, polling.calls)
        self.assertEqual(22, polling.requests[0].initial_position_seconds)
        self.assertEqual(30, polling.requests[0].monitoring_timeout_seconds)
        self.assertEqual(33, svm3.requests[1].initial_position_seconds)
        self.assertEqual(["start", "stop", "start", "stop"], runtime.calls)
        self.assertEqual([b"#SVM 0\r", b"#SVM 0\r"], tcp.payloads)

    def test_falls_back_to_polling_when_svm3_raises_exception(self):
        polling = RecordingPollingOrchestrator(
            _result(position_seconds=77, stop_reason=PlaybackMonitoringStopReason.PLAYER_IDLE)
        )
        svm3 = RaisingSVM3Orchestrator(RuntimeError("SVM3 stream died"))
        runtime = RecordingSVM3Runtime(start_result=DeviceCommandResult.success("ok"))
        tcp = RecordingTcpClient(response="@OK 0")
        orchestrator = DuringPlaybackOrchestrator(
            config=_config(),
            polling_orchestrator=polling,
            oppo_svm3_observation_orchestrator=svm3,
            svm3_runtime=runtime,
            tcp_client=tcp,
        )

        result = orchestrator.monitor_until_stopped(PlaybackMonitoringRequest())

        self.assertEqual(77, result.position_seconds)
        self.assertEqual(1, polling.calls)
        self.assertEqual(["start", "stop"], runtime.calls)
        self.assertEqual([b"#SVM 0\r"], tcp.payloads)  # SVM0 restored despite exception

    def test_carries_last_active_state_into_polling_retry_after_svm3_watchdog(self):
        paused_state = PlayerPlaybackState(
            status=PlayerPlaybackStatus.PAUSE,
            lifecycle_phase=PlayerPlaybackLifecyclePhase.ACTIVE,
            raw_response="@QPL OK PAUSE",
            ok=True,
        )
        polling = RecordingPollingOrchestrator(
            _result(position_seconds=44, stop_reason=PlaybackMonitoringStopReason.PLAYER_IDLE)
        )
        svm3 = RecordingSVM3Orchestrator(
            PlaybackMonitoringResult(
                position_seconds=22,
                duration_seconds=120,
                final_state=paused_state,
                stop_reason=PlaybackMonitoringStopReason.EVENT_WATCHDOG_EXPIRED,
            )
        )
        runtime = RecordingSVM3Runtime(start_result=DeviceCommandResult.success("ok"))
        tcp = RecordingTcpClient(response="@OK 0")
        orchestrator = DuringPlaybackOrchestrator(
            config=_config(),
            polling_orchestrator=polling,
            oppo_svm3_observation_orchestrator=svm3,
            svm3_runtime=runtime,
            tcp_client=tcp,
        )

        orchestrator.monitor_until_stopped(PlaybackMonitoringRequest())

        self.assertEqual(paused_state, polling.requests[0].last_active_state)

    def test_does_not_overwrite_last_active_state_when_result_is_not_active(self):
        paused_state = PlayerPlaybackState(
            status=PlayerPlaybackStatus.PAUSE,
            lifecycle_phase=PlayerPlaybackLifecyclePhase.ACTIVE,
            raw_response="@QPL OK PAUSE",
            ok=True,
        )
        polling = RecordingPollingOrchestrator(
            [
                _result(
                    position_seconds=33,
                    stop_reason=PlaybackMonitoringStopReason.OBSERVATION_WINDOW_EXPIRED,
                ),
                _result(
                    position_seconds=44, stop_reason=PlaybackMonitoringStopReason.PLAYER_IDLE
                ),
            ]
        )
        svm3 = RecordingSVM3Orchestrator(
            [
                PlaybackMonitoringResult(
                    position_seconds=22,
                    duration_seconds=120,
                    final_state=paused_state,
                    stop_reason=PlaybackMonitoringStopReason.EVENT_WATCHDOG_EXPIRED,
                ),
                _result(
                    position_seconds=55,
                    stop_reason=PlaybackMonitoringStopReason.EVENT_WATCHDOG_EXPIRED,
                ),
            ]
        )
        runtime = RecordingSVM3Runtime(start_result=DeviceCommandResult.success("ok"))
        tcp = RecordingTcpClient(response="@OK 0")
        orchestrator = DuringPlaybackOrchestrator(
            config=_config(),
            polling_orchestrator=polling,
            oppo_svm3_observation_orchestrator=svm3,
            svm3_runtime=runtime,
            tcp_client=tcp,
        )

        orchestrator.monitor_until_stopped(PlaybackMonitoringRequest())

        # _result()'s default final_state is STOP/IDLE, not ACTIVE — the paused
        # hint from the first SVM3 attempt must survive both the polling
        # window expiry and the second, signal-less SVM3 retry.
        self.assertEqual(paused_state, polling.requests[1].last_active_state)

    def test_retry_polling_window_uses_backoff_and_cap(self):
        polling = RecordingPollingOrchestrator(
            [
                _result(
                    position_seconds=10,
                    stop_reason=PlaybackMonitoringStopReason.OBSERVATION_WINDOW_EXPIRED,
                ),
                _result(
                    position_seconds=20,
                    stop_reason=PlaybackMonitoringStopReason.OBSERVATION_WINDOW_EXPIRED,
                ),
                _result(
                    position_seconds=30,
                    stop_reason=PlaybackMonitoringStopReason.PLAYER_IDLE,
                ),
            ]
        )
        svm3 = RecordingSVM3Orchestrator(
            [
                _result(
                    position_seconds=1,
                    stop_reason=PlaybackMonitoringStopReason.EVENT_WATCHDOG_EXPIRED,
                ),
                _result(
                    position_seconds=11,
                    stop_reason=PlaybackMonitoringStopReason.EVENT_WATCHDOG_EXPIRED,
                ),
                _result(
                    position_seconds=21,
                    stop_reason=PlaybackMonitoringStopReason.EVENT_WATCHDOG_EXPIRED,
                ),
            ]
        )
        runtime = RecordingSVM3Runtime(start_result=DeviceCommandResult.success("ok"))
        tcp = RecordingTcpClient(response="@OK 0")
        config = _config()
        config["oppo"]["svm3_retry_initial_delay_seconds"] = 30
        config["oppo"]["svm3_retry_max_delay_seconds"] = 60
        config["oppo"]["svm3_retry_backoff"] = 2
        orchestrator = DuringPlaybackOrchestrator(
            config=config,
            polling_orchestrator=polling,
            oppo_svm3_observation_orchestrator=svm3,
            svm3_runtime=runtime,
            tcp_client=tcp,
        )

        result = orchestrator.monitor_until_stopped(PlaybackMonitoringRequest())

        self.assertEqual(30, result.position_seconds)
        self.assertEqual(
            [30, 60, 60],
            [request.monitoring_timeout_seconds for request in polling.requests],
        )
        self.assertEqual(["start", "stop", "start", "stop", "start", "stop"], runtime.calls)
        self.assertEqual([b"#SVM 0\r", b"#SVM 0\r", b"#SVM 0\r"], tcp.payloads)


class RecordingPollingOrchestrator:
    def __init__(self, result=None):
        self.results = _as_result_list(result or _result(position_seconds=99))
        self.calls = 0
        self.requests = []

    def monitor_until_stopped(self, request):
        self.calls += 1
        self.requests.append(request)
        if not self.results:
            raise AssertionError("Unexpected extra polling call")
        return self.results.pop(0)


class RecordingSVM3Orchestrator:
    def __init__(self, result):
        self.results = _as_result_list(result)
        self.calls = 0
        self.reporter = None
        self.requests = []

    def set_observed_event_reporter(self, reporter):
        self.reporter = reporter

    def monitor_until_stopped(self, request):
        self.calls += 1
        self.requests.append(request)
        if not self.results:
            raise AssertionError("Unexpected extra SVM3 call")
        return self.results.pop(0)


class RecordingSVM3Runtime:
    def __init__(self, *, start_result):
        self.start_result = start_result
        self.calls = []

    def start(self):
        self.calls.append("start")
        return self.start_result

    def stop(self):
        self.calls.append("stop")


class RaisingSVM3Orchestrator:
    def __init__(self, exc):
        self._exc = exc

    def set_observed_event_reporter(self, reporter):
        pass

    def monitor_until_stopped(self, request):
        raise self._exc


class RecordingTcpClient:
    def __init__(self, *, response):
        self.response = response
        self.payloads = []

    def request(self, **kwargs):
        self.payloads.append(kwargs["payload"])
        return self.response


def _result(
    *,
    position_seconds=12,
    stop_reason=PlaybackMonitoringStopReason.PLAYER_IDLE,
):
    return PlaybackMonitoringResult(
        position_seconds=position_seconds,
        duration_seconds=120,
        final_state=PlayerPlaybackState(
            status=PlayerPlaybackStatus.STOP,
            lifecycle_phase=PlayerPlaybackLifecyclePhase.IDLE,
            raw_response="@QPL OK STOP",
            ok=True,
        ),
        stop_reason=stop_reason,
    )


def _as_result_list(value):
    if isinstance(value, list):
        return list(value)

    return [value]


def _config():
    return {
        "OPPO_Port": 23,
        "oppo": {
            "ip": "192.168.1.50",
            "connection_timeout_seconds": 3,
        },
    }


if __name__ == "__main__":
    unittest.main()
