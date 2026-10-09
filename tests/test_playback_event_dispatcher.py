import threading
import time
import unittest

from home_cinema_control.playback.event_dispatcher import PlaybackEventDispatcher
from home_cinema_control.playback.events import PlaybackEvent, PlaybackEventType


class PlaybackEventDispatcherTest(unittest.TestCase):
    def test_consumers_receive_events_independently_in_order(self):
        fast = RecordingConsumer("fast")
        slow = RecordingConsumer("slow", wait=True)
        dispatcher = PlaybackEventDispatcher(queue_size=4)
        dispatcher.register(fast)
        dispatcher.register(slow)

        dispatcher.publish(_event("event-1"))
        dispatcher.publish(_event("event-2"))
        self.assertTrue(fast.ready.wait(timeout=1))

        dispatcher.shutdown(drain=True)

        self.assertEqual(["event-1", "event-2"], fast.events)
        self.assertEqual(["event-1", "event-2"], slow.events)

    def test_consumer_failure_does_not_stop_other_consumers(self):
        failing = FailingConsumer()
        healthy = RecordingConsumer("healthy")
        dispatcher = PlaybackEventDispatcher()
        dispatcher.register(failing)
        dispatcher.register(healthy)

        dispatcher.publish(_event("event-1"))
        dispatcher.shutdown(drain=True)

        self.assertEqual(["event-1"], healthy.events)


def _event(event_id):
    return PlaybackEvent(
        event_id=event_id,
        session_id="session-1",
        event_type=PlaybackEventType.PAUSED,
    )


class RecordingConsumer:
    def __init__(self, name, *, wait=False):
        self.name = name
        self.wait = wait
        self.events = []
        self.ready = threading.Event()

    def consume(self, event):
        if self.wait:
            time.sleep(0.01)
        self.events.append(event.event_id)
        self.ready.set()


class FailingConsumer:
    name = "failing"

    def consume(self, event):
        raise RuntimeError("test failure")


if __name__ == "__main__":
    unittest.main()
