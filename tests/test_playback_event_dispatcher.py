import threading
import time
import unittest

from home_cinema_control.application_events import ApplicationEventBus
from home_cinema_control.notifications.models import (
    UpdateAvailableEvent,
    UpdateNotification,
)
from home_cinema_control.playback.event_dispatcher import PlaybackEventDispatcher
from home_cinema_control.playback.events import PlaybackEvent, PlaybackEventType


class PlaybackEventDispatcherTest(unittest.TestCase):
    def test_typed_subscriptions_route_without_global_event_coupling(self):
        playback = RecordingConsumer("playback")
        updates = RecordingConsumer("updates")
        bus = ApplicationEventBus()
        bus.subscribe(
            PlaybackEvent,
            playback,
            ordering_key=lambda event: event.session_id,
        )
        bus.subscribe(UpdateAvailableEvent, updates)

        bus.publish(_event("event-1", PlaybackEventType.STARTED))
        bus.publish(
            UpdateAvailableEvent(
                notification=UpdateNotification(
                    current_version="1.4.0",
                    latest_version="1.4.1",
                    release_url="https://example.test/1.4.1",
                    title="Update",
                    message="Update",
                )
            )
        )
        bus.publish(_event("event-2", PlaybackEventType.PAUSED))
        bus.shutdown(drain=True)

        self.assertEqual(["event-1", "event-2"], playback.events)
        self.assertEqual(1, len(updates.events))

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


def _event(event_id, event_type=PlaybackEventType.PAUSED):
    return PlaybackEvent(
        event_id=event_id,
        session_id="session-1",
        event_type=event_type,
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
