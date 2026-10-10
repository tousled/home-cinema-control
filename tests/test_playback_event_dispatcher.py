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

    def test_ordered_subscription_preserves_fifo_per_correlation_key(self):
        consumer = KeyedRecordingConsumer()
        bus = ApplicationEventBus(ordered_worker_count=2)
        bus.subscribe(
            PlaybackEvent,
            consumer,
            ordering_key=lambda event: event.session_id,
        )

        bus.publish(_event("a-1", session_id="session-a"))
        bus.publish(_event("b-1", session_id="session-b"))
        bus.publish(_event("a-2", session_id="session-a"))
        bus.publish(_event("b-2", session_id="session-b"))
        bus.shutdown(drain=True)

        self.assertEqual(["a-1", "a-2"], consumer.events["session-a"])
        self.assertEqual(["b-1", "b-2"], consumer.events["session-b"])

    def test_ordered_subscription_processes_different_keys_in_parallel(self):
        consumer = BlockingConsumer()
        bus = ApplicationEventBus(ordered_worker_count=2)
        bus.subscribe(
            PlaybackEvent,
            consumer,
            ordering_key=lambda event: event.session_id,
        )

        bus.publish(_event("a-1", session_id="session-a"))
        self.assertTrue(consumer.first_started.wait(timeout=1))

        bus.publish(_event("b-1", session_id="session-b"))
        self.assertTrue(consumer.second_key_seen.wait(timeout=1))

        consumer.release_first.set()
        bus.shutdown(drain=True)

        self.assertCountEqual(["a-1", "b-1"], consumer.events)

    def test_different_event_families_are_not_serialized_together(self):
        playback = BlockingConsumer()
        updates = RecordingConsumer("updates")
        bus = ApplicationEventBus(ordered_worker_count=2)
        bus.subscribe(
            PlaybackEvent,
            playback,
            ordering_key=lambda event: event.session_id,
        )
        bus.subscribe(UpdateAvailableEvent, updates)

        bus.publish(_event("playback-1", session_id="session-a"))
        self.assertTrue(playback.first_started.wait(timeout=1))
        bus.publish(_update_event())
        self.assertTrue(updates.ready.wait(timeout=1))

        playback.release_first.set()
        bus.shutdown(drain=True)

        self.assertEqual(["playback-1"], playback.events)
        self.assertEqual(1, len(updates.events))

    def test_consumer_failure_does_not_stop_other_consumers(self):
        failing = FailingConsumer()
        healthy = RecordingConsumer("healthy")
        dispatcher = PlaybackEventDispatcher()
        dispatcher.register(failing)
        dispatcher.register(healthy)

        dispatcher.publish(_event("event-1"))
        dispatcher.shutdown(drain=True)

        self.assertEqual(["event-1"], healthy.events)


def _event(event_id, event_type=PlaybackEventType.PAUSED, *, session_id="session-1"):
    return PlaybackEvent(
        event_id=event_id,
        session_id=session_id,
        event_type=event_type,
    )


def _update_event():
    return UpdateAvailableEvent(
        notification=UpdateNotification(
            current_version="1.4.0",
            latest_version="1.4.1",
            release_url="https://example.test/1.4.1",
            title="Update",
            message="Update",
        )
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


class KeyedRecordingConsumer:
    name = "keyed-recording"

    def __init__(self):
        self.events = {"session-a": [], "session-b": []}

    def consume(self, event):
        self.events[event.session_id].append(event.event_id)


class BlockingConsumer:
    name = "blocking"

    def __init__(self):
        self.events = []
        self.first_started = threading.Event()
        self.second_key_seen = threading.Event()
        self.release_first = threading.Event()

    def consume(self, event):
        if event.session_id == "session-a":
            self.first_started.set()
            self.release_first.wait(timeout=1)
        if event.session_id == "session-b":
            self.second_key_seen.set()
        self.events.append(event.event_id)


if __name__ == "__main__":
    unittest.main()
