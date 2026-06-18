from __future__ import annotations

import logging
import threading
from collections.abc import Callable

from home_cinema_control.playback.intent import PlaybackIntent, PlaybackOrigin

logger = logging.getLogger(__name__)


class PlaybackThreadLifecycle:
    """Coordinates background playback startup and active-playback replacement.

    The application service owns what playback does; this class only owns when
    the active thread starts, how replacement asks that thread to finish, and
    when the next playback may start.
    """

    def __init__(
        self,
        *,
        start_playback: Callable[..., object],
        reload_config: Callable[[], None],
        stop_active_playback: Callable[[], None],
        thread_factory=threading.Thread,
    ) -> None:
        self._start_playback = start_playback
        self._reload_config = reload_config
        self._stop_active_playback = stop_active_playback
        self._thread_factory = thread_factory
        self._active_thread: threading.Thread | None = None
        self._replacement_thread: threading.Thread | None = None
        self._thread_lock = threading.Lock()
        self._replacement_requested = threading.Event()
        self._last_playback_result = None

    @property
    def replacement_requested(self) -> bool:
        return self._replacement_requested.is_set()

    def start(self, intent: PlaybackIntent, *, origin: PlaybackOrigin) -> None:
        thread = self._thread_factory(
            target=self._run_start,
            args=(intent, origin),
        )
        with self._thread_lock:
            self._active_thread = thread
        thread.start()

    def replace(self, intent: PlaybackIntent, *, origin: PlaybackOrigin) -> bool:
        logger.info(
            "Replacing active playback through normal finish/start flow | "
            "origin=%s | media_item_id=%s",
            origin.value,
            intent.media_item_id,
        )
        with self._thread_lock:
            if (
                self._replacement_thread is not None
                and self._replacement_thread.is_alive()
            ):
                logger.info(
                    "Ignoring replacement request because another replacement "
                    "is already in progress | origin=%s | media_item_id=%s",
                    origin.value,
                    intent.media_item_id,
                )
                return False

            thread = self._thread_factory(
                target=self._run_replace,
                args=(intent, origin),
            )
            self._replacement_thread = thread

        thread.start()
        return True

    def _run_start(
        self,
        intent: PlaybackIntent,
        origin: PlaybackOrigin,
    ) -> None:
        try:
            logger.info("Thread Play: starting")
            self._last_playback_result = self._start_playback(
                intent,
                origin=origin,
            )
            self._reload_config()
            logger.info("Thread Play: finishing")
        finally:
            current_thread = threading.current_thread()
            with self._thread_lock:
                if self._active_thread is current_thread:
                    self._active_thread = None

    def _run_replace(self, intent: PlaybackIntent, origin: PlaybackOrigin) -> None:
        with self._thread_lock:
            active_thread = self._active_thread

        if active_thread is not None and active_thread.is_alive():
            logger.info("Stopping active playback before replacement.")
            self._replacement_requested.set()
            try:
                self._stop_active_playback()
                active_thread.join()
            finally:
                self._replacement_requested.clear()

            if (
                self._last_playback_result is not None
                and not self._last_playback_result.successful
            ):
                logger.warning(
                    "Skipping replacement startup because active playback did not "
                    "finish cleanly | successful=%s",
                    self._last_playback_result.successful,
                )
                return

        replacement_thread = self._thread_factory(
            target=self._run_start,
            args=(intent, origin),
        )
        with self._thread_lock:
            self._active_thread = replacement_thread
        replacement_thread.start()
