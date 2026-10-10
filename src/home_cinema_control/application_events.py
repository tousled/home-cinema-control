from __future__ import annotations

import logging
import queue
import threading
from collections.abc import Callable
from dataclasses import dataclass
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
    events: queue.Queue
    thread: threading.Thread
    ordering_key: Callable[[Any], object] | None = None


class ApplicationEventBus:
    """Small in-process event bus with opt-in FIFO routing.

    An ordered subscription uses one FIFO worker. Its ordering key identifies
    the lifecycle correlation that requires ordering, without adding sequence
    metadata to the event. The bus deliberately does not impose a global order
    between unrelated event families or consumers.
    """

    def __init__(self, *, queue_size: int = 64) -> None:
        self._queue_size = queue_size
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
        # Ordered lifecycle events are low-volume and must not be dropped.
        events = queue.Queue(maxsize=0 if ordering_key is not None else self._queue_size)
        subscription = _Subscription(
            event_type=event_type,
            consumer=consumer,
            events=events,
            thread=threading.Thread(
                target=self._run_consumer,
                args=(consumer, events),
                name=f"hcc-event-consumer-{consumer.name}",
                daemon=True,
            ),
            ordering_key=ordering_key,
        )
        with self._lock:
            if self._stopping:
                raise RuntimeError("Cannot subscribe while stopping")
            self._subscriptions.append(subscription)
            subscription.thread.start()

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
                    subscription.events.put_nowait(event)
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
            if not drain:
                _drain_queue(subscription.events)
            subscription.events.put(_STOP)

        for subscription in subscriptions:
            subscription.thread.join(timeout=timeout_seconds)
            if subscription.thread.is_alive():
                logger.error(
                    "Application event consumer did not stop before timeout | consumer=%s",
                    subscription.consumer.name,
                )

    @staticmethod
    def _run_consumer(consumer: ApplicationEventConsumer, events: queue.Queue) -> None:
        while True:
            event = events.get()
            try:
                if event is _STOP:
                    return
                consumer.consume(event)
            except Exception:
                logger.exception(
                    "Application event consumer failed | consumer=%s | event_id=%s | "
                    "event=%s",
                    consumer.name,
                    getattr(event, "event_id", "unknown"),
                    getattr(event, "event_type", type(event).__name__),
                )
            finally:
                events.task_done()


def _drain_queue(events: queue.Queue) -> None:
    while True:
        try:
            events.get_nowait()
        except queue.Empty:
            return
        else:
            events.task_done()
