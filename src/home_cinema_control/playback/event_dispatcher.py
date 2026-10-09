from __future__ import annotations

import logging
import queue
import threading
from dataclasses import dataclass
from typing import Protocol

from home_cinema_control.playback.events import PlaybackEvent

logger = logging.getLogger(__name__)
_STOP = object()


class PlaybackEventConsumer(Protocol):
    name: str

    def consume(self, event: PlaybackEvent) -> None: ...


@dataclass
class _ConsumerWorker:
    consumer: PlaybackEventConsumer
    events: queue.Queue
    thread: threading.Thread


class PlaybackEventDispatcher:
    """Fan out lifecycle events through one bounded worker per consumer."""

    def __init__(self, *, queue_size: int = 64) -> None:
        self._queue_size = queue_size
        self._workers: list[_ConsumerWorker] = []
        self._lock = threading.RLock()
        self._stopping = False

    def register(self, consumer: PlaybackEventConsumer) -> None:
        events = queue.Queue(maxsize=self._queue_size)
        worker = _ConsumerWorker(
            consumer=consumer,
            events=events,
            thread=threading.Thread(
                target=self._run_consumer,
                args=(consumer, events),
                name=f"hcc-playback-consumer-{consumer.name}",
                daemon=True,
            ),
        )
        with self._lock:
            if self._stopping:
                raise RuntimeError("Cannot register a consumer while stopping")
            self._workers.append(worker)
            worker.thread.start()

    def publish(self, event: PlaybackEvent) -> None:
        with self._lock:
            workers = tuple(self._workers)
            if self._stopping:
                logger.warning(
                    "Dropping playback event during dispatcher shutdown | "
                    "event_id=%s | event=%s",
                    event.event_id,
                    event.event_type,
                )
                return

        for worker in workers:
            try:
                worker.events.put_nowait(event)
            except queue.Full:
                logger.error(
                    "Playback consumer queue full | consumer=%s | event_id=%s | "
                    "session_id=%s | event=%s",
                    worker.consumer.name,
                    event.event_id,
                    event.session_id,
                    event.event_type,
                )

    def shutdown(self, *, drain: bool = True, timeout_seconds: float = 5.0) -> None:
        with self._lock:
            self._stopping = True
            workers = tuple(self._workers)

        for worker in workers:
            if not drain:
                _drain_queue(worker.events)
            worker.events.put(_STOP)

        for worker in workers:
            worker.thread.join(timeout=timeout_seconds)
            if worker.thread.is_alive():
                logger.error(
                    "Playback consumer did not stop before timeout | consumer=%s",
                    worker.consumer.name,
                )

    @staticmethod
    def _run_consumer(consumer: PlaybackEventConsumer, events: queue.Queue) -> None:
        while True:
            event = events.get()
            try:
                if event is _STOP:
                    return
                consumer.consume(event)
            except Exception:
                logger.exception(
                    "Playback consumer failed | consumer=%s | event_id=%s | "
                    "session_id=%s | event=%s",
                    consumer.name,
                    event.event_id,
                    event.session_id,
                    event.event_type,
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
