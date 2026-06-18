from __future__ import annotations

import logging
from dataclasses import dataclass

from home_cinema_control.playback.intent import PlaybackOrigin

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PlaybackStartMessages:
    """User-visible messages sent back to the source media-server client."""

    init_oppo: str
    wait_for_mount: str
    wait_for_play: str
    timeout_play: str
    error_mount: str
    error_play: str
    error_no_oppo: str


def playback_start_messages(lang: dict) -> PlaybackStartMessages:
    return PlaybackStartMessages(
        init_oppo=lang["msg-playback-starting"],
        wait_for_mount=lang["msg-playback-waiting-mount"],
        wait_for_play=lang["msg-playback-waiting-play"],
        timeout_play=lang["msg-playback-timeout"],
        error_mount=lang["msg-playback-error-mount"],
        error_play=lang["msg-playback-error-play"],
        error_no_oppo=lang["msg-playback-error-no-oppo"],
    )


def send_playback_message(
    playback_session,
    origin: PlaybackOrigin,
    session_id: str | None,
    message: str,
    timeout_ms: int | None = None,
) -> None:
    """Send a user-visible playback message to the source client when present."""
    if session_id:
        if timeout_ms is None:
            playback_session.notify_session(session_id, message)
        else:
            playback_session.notify_session(session_id, message, timeout_ms)
        return

    logger.info(
        "Skipping playback message; no active source session is available | "
        "origin=%s | text=%s",
        origin.value,
        message,
    )


class PlaybackStartupWaitNotifier:
    """Rate-limits source-client startup waiting messages to whole seconds."""

    def __init__(
        self,
        *,
        playback_session,
        origin: PlaybackOrigin,
        session_id: str | None,
        wait_for_play_message: str,
        poll_interval_seconds: float,
        notification_interval_seconds: int = 1,
    ) -> None:
        self._playback_session = playback_session
        self._origin = origin
        self._session_id = session_id
        self._wait_for_play_message = wait_for_play_message
        self._poll_interval_seconds = poll_interval_seconds
        self._notification_interval_seconds = notification_interval_seconds
        self._last_notified_second = -1

    def notify_waiting(self, attempt: int) -> None:
        elapsed_seconds = int(attempt * self._poll_interval_seconds)

        if elapsed_seconds <= 0:
            return

        if elapsed_seconds % self._notification_interval_seconds != 0:
            return

        if elapsed_seconds == self._last_notified_second:
            return

        self._last_notified_second = elapsed_seconds
        send_playback_message(
            self._playback_session,
            self._origin,
            self._session_id,
            self._wait_for_play_message + str(elapsed_seconds) + "s",
            timeout_ms=999,
        )
