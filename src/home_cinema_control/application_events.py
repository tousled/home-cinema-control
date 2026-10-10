from __future__ import annotations

import logging
import queue
import threading
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
from time import monotonic
from typing import Any, Protocol

logger = logging.getLogger(__name__)
_STOP = object()


class EventPublisher(Protocol):
    def publish(self, event: Any) -> None: ...


class ApplicationEventConsumer(Protocol):
    name: str

    def consume(self, event: Any) -> None: ...


@dataclass
class _Subscription:
    event_type: type
    consumer: ApplicationEventConsumer
    events: queue.Queue | None
    threads: tuple[threading.Thread, ...]
    ordering_key: Callable[[Any], object] | None = None
    ordered_dispatcher: "_OrderedEventDispatcher | None" = None

    def enqueue(self, event: Any) -> None:
        if self.ordered_dispatcher is not None:
            key = self.ordering_key(event)
            self.ordered_dispatcher.enqueue(key, event)
            return
        self.events.put_nowait(event)


class _OrderedEventDispatcher:
    """Runs one FIFO lane per correlation key with a bounded worker pool.

    The dispatcher keeps ordering local to the subscription and correlation
    key. A busy playback session therefore cannot reorder its own events, but
    it also cannot permanently occupy one thread per session over the runtime's
    lifetime.
    """

    def __init__(
        self,
        consumer: ApplicationEventConsumer,
        *,
        worker_count: int,
    ) -> None:
        self._consumer = consumer
        self._ready_keys: queue.Queue[object] = queue.Queue()
        self._pending: dict[object, deque[Any]] = {}
        self._active_keys: set[object] = set()
        self._lock = threading.RLock()
        self._idle = threading.Condition(self._lock)
        self._stopping = False
        self._threads = tuple(
            threading.Thread(
                target=self._run,
                name=f"hcc-event-consumer-{consumer.name}-{index}",
                daemon=True,
            )
            for index in range(worker_count)
        )

    def start(self) -> None:
        for thread in self._threads:
            thread.start()

    @property
    def threads(self) -> tuple[threading.Thread, ...]:
        return self._threads

    def enqueue(self, key: object, event: Any) -> None:
        with self._lock:
            if self._stopping:
                return
            lane = self._pending.setdefault(key, deque())
            lane.append(event)
            if key not in self._active_keys:
                self._active_keys.add(key)
                self._ready_keys.put(key)

    def shutdown(self, *, drain: bool, timeout_seconds: float) -> None:
        deadline = monotonic() + timeout_seconds
        with self._lock:
            self._stopping = True
            if not drain:
                self._pending.clear()
                self._idle.notify_all()
            else:
                while self._pending or self._active_keys:
                    remaining = deadline - monotonic()
                    if remaining <= 0:
                        logger.error(
                            "Ordered application event consumer did not drain before timeout | consumer=%s",
                            self._consumer.name,
                        )
                        break
                    self._idle.wait(timeout=remaining)

            for _ in self._threads:
                self._ready_keys.put(_STOP)

        for thread in self._threads:
            thread.join(timeout=max(0.0, deadline - monotonic()))

    def _run(self) -> None:
        while True:
            key = self._ready_keys.get()
            try:
                if key is _STOP:
                    return

                with self._lock:
                    lane = self._pending.get(key)
                    if not lane:
                        self._active_keys.discard(key)
                        self._idle.notify_all()
                        continue
                    event = lane.popleft()

                _consume_one(self._consumer, event)

                with self._lock:
                    lane = self._pending.get(key)
                    if lane:
                        self._ready_keys.put(key)
                    else:
                        self._pending.pop(key, None)
                        self._active_keys.discard(key)
                        self._idle.notify_all()
            finally:
                self._ready_keys.task_done()


class ApplicationEventBus:
    """Small in-process event bus with opt-in correlation-key ordering.

    An ordered subscription routes each correlation key through its own FIFO
    lane and processes lanes with a bounded worker pool. The event type and
    subscription define the event family; the ordering key identifies the
    lifecycle correlation that requires ordering, without adding sequence
    metadata to the event. The bus deliberately does not impose a global order
    between unrelated event families or consumers.
    """

    def __init__(self, *, queue_size: int = 64, ordered_worker_count: int = 2) -> None:
        self._queue_size = queue_size
        self._ordered_worker_count = max(1, ordered_worker_count)
        self._subscriptions: list[_Subscription] = []
        self._lock = threading.RLock()
        self._stopping = False

    def subscribe(
        self,
        event_type: type,
        consumer: ApplicationEventConsumer,
        *,
        ordering_key: Callable[[Any], object] | None = None,
    ) -> None:
        with self._lock:
            if self._stopping:
                raise RuntimeError("Cannot subscribe while stopping")

            # Ordered lifecycle events are low-volume and must not be dropped.
            ordered_dispatcher = (
                _OrderedEventDispatcher(
                    consumer,
                    worker_count=self._ordered_worker_count,
                )
                if ordering_key is not None
                else None
            )
            events = (
                None
                if ordered_dispatcher is not None
                else queue.Queue(maxsize=self._queue_size)
            )
            threads = (
                ordered_dispatcher.threads
                if ordered_dispatcher is not None
                else (
                    threading.Thread(
                        target=self._run_consumer,
                        args=(consumer, events),
                        name=f"hcc-event-consumer-{consumer.name}",
                        daemon=True,
                    ),
                )
            )
            subscription = _Subscription(
                event_type=event_type,
                consumer=consumer,
                events=events,
                threads=threads,
                ordering_key=ordering_key,
                ordered_dispatcher=ordered_dispatcher,
            )
            self._subscriptions.append(subscription)
            if ordered_dispatcher is not None:
                ordered_dispatcher.start()
            else:
                for thread in subscription.threads:
                    thread.start()

    def register(self, consumer: ApplicationEventConsumer) -> None:
        """Compatibility helper for legacy callers receiving every event."""
        self.subscribe(object, consumer)

    def publish(self, event: Any) -> None:
        with self._lock:
            if self._stopping:
                logger.warning(
                    "Dropping application event during bus shutdown | event_id=%s | event=%s",
                    getattr(event, "event_id", "unknown"),
                    getattr(event, "event_type", type(event).__name__),
                )
                return

            subscriptions = tuple(
                subscription
                for subscription in self._subscriptions
                if subscription.event_type is object
                or isinstance(event, subscription.event_type)
            )
            for subscription in subscriptions:
                try:
                    subscription.enqueue(event)
                except queue.Full:
                    logger.error(
                        "Application event queue full | consumer=%s | event_id=%s | "
                        "event=%s",
                        subscription.consumer.name,
                        getattr(event, "event_id", "unknown"),
                        getattr(event, "event_type", type(event).__name__),
                    )

    def shutdown(self, *, drain: bool = True, timeout_seconds: float = 5.0) -> None:
        with self._lock:
            self._stopping = True
            subscriptions = tuple(self._subscriptions)

        for subscription in subscriptions:
            if subscription.ordered_dispatcher is not None:
                subscription.ordered_dispatcher.shutdown(
                    drain=drain,
                    timeout_seconds=timeout_seconds,
                )
                continue
            if not drain:
                _drain_queue(subscription.events)
            subscription.events.put(_STOP)

        for subscription in subscriptions:
            for thread in subscription.threads:
                thread.join(timeout=timeout_seconds)
            if any(thread.is_alive() for thread in subscription.threads):
                logger.error(
                    "Application event consumer did not stop before timeout | consumer=%s",
                    subscription.consumer.name,
                )

    @staticmethod
    def _run_consumer(consumer: ApplicationEventConsumer, events: queue.Queue | None) -> None:
        while True:
            event = events.get()
            try:
                if event is _STOP:
                    return
                _consume_one(consumer, event)
            finally:
                events.task_done()


def _consume_one(consumer: ApplicationEventConsumer, event: Any) -> None:
    try:
        consumer.consume(event)
    except Exception:
        logger.exception(
            "Application event consumer failed | consumer=%s | event_id=%s | "
            "event=%s",
            consumer.name,
            getattr(event, "event_id", "unknown"),
            getattr(event, "event_type", type(event).__name__),
        )


def _drain_queue(events: queue.Queue | None) -> None:
    if events is None:
        return
    while True:
        try:
            events.get_nowait()
        except queue.Empty:
            return
        else:
            events.task_done()
