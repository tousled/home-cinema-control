import unittest

from home_cinema_control.devices.oppo.svm3_runtime import OppoSVM3PlaybackRuntime
from home_cinema_control.devices.oppo.verbose_events import parse_verbose_event


class OppoSVM3PlaybackRuntimeTest(unittest.TestCase):
    def test_start_waits_for_svm3_acknowledgement(self):
        runtime = OppoSVM3PlaybackRuntime(
            listener=RecordingListener(["@SVM OK 3"]),
            thread_factory=ImmediateThread,
        )

        result = runtime.start()

        self.assertTrue(result.successful)

    def test_start_fails_without_svm3_acknowledgement(self):
        runtime = OppoSVM3PlaybackRuntime(
            listener=RecordingListener(["@UPL PLAY"]),
            thread_factory=ImmediateThread,
            start_timeout_seconds=0.01,
        )

        result = runtime.start()

        self.assertFalse(result.successful)
        self.assertIn("Timed out", result.detail)

    def test_listen_replays_last_observed_event_to_new_subscription(self):
        runtime = OppoSVM3PlaybackRuntime(
            listener=RecordingListener(
                ["@SVM OK 3", "@UPL PLAY", "@UTC 000 001 C 00:00:01"]
            ),
            thread_factory=ImmediateThread,
        )

        events = list(runtime.listen(duration_seconds=0.01))

        self.assertEqual(["UTC"], [event.code for event in events])

    def test_listen_accepts_verbose_observation_strategy_arguments(self):
        runtime = OppoSVM3PlaybackRuntime(
            listener=RecordingListener(["@SVM OK 3", "@UTC 000 001 C 00:00:01"]),
            thread_factory=ImmediateThread,
        )

        events = list(
            runtime.listen(
                verbose_mode=3,
                restore_verbose_mode=False,
                initial_commands=["#QPL"],
                keepalive_command="#QPL",
                keepalive_interval_seconds=5.0,
                utc_idle_timeout_seconds=1.0,
                duration_seconds=0.01,
            )
        )

        self.assertEqual(["UTC"], [event.code for event in events])


class RecordingListener:
    def __init__(self, raw_events):
        self.raw_events = raw_events
        self.listen_kwargs = None

    def listen(self, **kwargs):
        self.listen_kwargs = kwargs
        for raw_event in self.raw_events:
            yield parse_verbose_event(raw_event)


class ImmediateThread:
    def __init__(self, *, target, name=None, daemon=None):
        self._target = target
        self._alive = False

    def start(self):
        self._alive = True
        try:
            self._target()
        finally:
            self._alive = False

    def join(self, timeout=None):
        return None

    def is_alive(self):
        return self._alive


if __name__ == "__main__":
    unittest.main()
