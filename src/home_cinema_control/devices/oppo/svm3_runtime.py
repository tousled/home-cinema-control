from __future__ import annotations

import logging
import queue
import threading
import time
from collections.abc import Callable, Iterator

from home_cinema_control.devices.oppo.verbose_events import (
    OppoVerboseEvent,
    OppoVerboseEventListener,
)
from home_cinema_control.playback.startup.models import DeviceCommandResult

logger = logging.getLogger(__name__)


class OppoSVM3PlaybackRuntime:
    """Owns one persistent OPPO SVM 3 stream during playback observation."""

    def __init__(
        self,
        *,
        listener: OppoVerboseEventListener,
        thread_factory: Callable[..., threading.Thread] = threading.Thread,
        now: Callable[[], float] = time.monotonic,
        start_timeout_seconds: float = 3.0,
    ) -> None:
        self._listener = listener
        self._thread_factory = thread_factory
        self._now = now
        self._start_timeout_seconds = start_timeout_seconds
        self._stop_requested = threading.Event()
        self._ready = threading.Event()
        self._subscriptions: list[queue.Queue[OppoVerboseEvent]] = []
        self._subscriptions_lock = threading.Lock()
        self._thread: threading.Thread | None = None
        self._last_event: OppoVerboseEvent | None = None
        self._last_error: BaseException | None = None

    def start(self) -> DeviceCommandResult:
        if self.is_running:
            return DeviceCommandResult.success("OPPO SVM 3 runtime is already running.")

        self._stop_requested.clear()
        self._ready.clear()
        self._last_error = None
        self._thread = self._thread_factory(
            target=self._run,
            name="oppo-svm3-playback-runtime",
            daemon=True,
        )
        self._thread.start()
        if not self._ready.wait(timeout=self._start_timeout_seconds):
            if self._last_error is not None:
                return DeviceCommandResult.failed(
                    "OPPO SVM 3 runtime failed while starting: "
                    f"{type(self._last_error).__name__}: {self._last_error}"
                )

            return DeviceCommandResult.failed(
                "Timed out waiting for OPPO SVM 3 acknowledgement."
            )

        logger.info("OPPO SVM 3 playback runtime started")
        return DeviceCommandResult.success("OPPO SVM 3 playback runtime started.")

    def stop(self, *, timeout_seconds: float = 3.0) -> None:
        self._stop_requested.set()
        if self._thread is not None:
            self._thread.join(timeout=timeout_seconds)
        logger.info("OPPO SVM 3 playback runtime stopped")

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def listen(
        self,
        *,
        verbose_mode: int = 3,
        duration_seconds: float | None = None,
        initial_commands: list[str] | None = None,
        keepalive_command: str | None = None,
        keepalive_interval_seconds: float = 10.0,
        restore_verbose_mode: bool = False,
        utc_idle_timeout_seconds: float | None = None,
        stop_requested=None,
    ) -> Iterator[OppoVerboseEvent]:
        """Yield events from the playback-owned SVM3 runtime.

        The generic verbose observation strategy can also receive a raw
        ``OppoVerboseEventListener``, whose ``listen`` method owns SVM mode
        selection parameters such as ``verbose_mode`` and
        ``restore_verbose_mode``. This runtime already starts one persistent
        SVM3 stream in ``start()``, so those compatibility arguments are
        intentionally accepted but not used here.
        """
        _ = (
            verbose_mode,
            initial_commands,
            keepalive_command,
            keepalive_interval_seconds,
            restore_verbose_mode,
        )

        if not self.is_running:
            start_result = self.start()
            if not start_result.successful:
                raise RuntimeError(start_result.detail)

        subscription = self._subscribe()
        deadline = (
            None
            if duration_seconds is None
            else self._now() + max(0.0, duration_seconds)
        )
        utc_idle_timeout_seconds = (
            None
            if utc_idle_timeout_seconds is None
            else max(0.1, utc_idle_timeout_seconds)
        )
        last_utc_at = self._now()

        try:
            while not (stop_requested and stop_requested()):
                if deadline is not None and self._now() >= deadline:
                    break

                if (
                    utc_idle_timeout_seconds is not None
                    and self._now() - last_utc_at >= utc_idle_timeout_seconds
                ):
                    logger.warning(
                        "OPPO SVM 3 event stream idle timeout | seconds=%s",
                        utc_idle_timeout_seconds,
                    )
                    break

                try:
                    event = subscription.get(timeout=0.2)
                except queue.Empty:
                    if self._last_error is not None:
                        raise RuntimeError(
                            "OPPO SVM 3 playback runtime failed"
                        ) from self._last_error
                    if not self.is_running:
                        break
                    continue

                if event.code == "UTC":
                    last_utc_at = self._now()

                yield event
        finally:
            self._unsubscribe(subscription)

    def _run(self) -> None:
        try:
            for event in self._listener.listen(
                verbose_mode=3,
                restore_verbose_mode=False,
                stop_requested=self._stop_requested.is_set,
            ):
                self._publish(event)
        except Exception as exc:
            self._last_error = exc
            logger.exception("OPPO SVM 3 playback runtime failed")

    def _subscribe(self) -> queue.Queue[OppoVerboseEvent]:
        subscription: queue.Queue[OppoVerboseEvent] = queue.Queue()
        if self._last_event is not None:
            subscription.put(self._last_event)
        with self._subscriptions_lock:
            self._subscriptions.append(subscription)
        return subscription

    def _unsubscribe(self, subscription: queue.Queue[OppoVerboseEvent]) -> None:
        with self._subscriptions_lock:
            if subscription in self._subscriptions:
                self._subscriptions.remove(subscription)

    def _publish(self, event: OppoVerboseEvent) -> None:
        self._last_event = event
        if event.code == "SVM" and event.payload.strip().upper() == "OK 3":
            self._ready.set()

        with self._subscriptions_lock:
            subscriptions = list(self._subscriptions)

        for subscription in subscriptions:
            subscription.put(event)
