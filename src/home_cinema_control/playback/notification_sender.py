from __future__ import annotations

import logging
from dataclasses import dataclass

from home_cinema_control.playback.intent import PlaybackOrigin

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PlaybackStartMessages:
    """User-visible failure/timeout messages sent back to the source client.

    Success-path startup narration (the six touchpoints) lives in
    `playback/startup/messaging.py` — this is only the error/timeout vocabulary,
    deliberately kept separate so real failures are never dressed in the
    success-path's cinematic tone.
    """

    timeout_play: str
    error_mount: str
    error_play: str
    error_no_oppo: str


def playback_start_messages(lang: dict) -> PlaybackStartMessages:
    return PlaybackStartMessages(
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
    """Send a user-visible playback message to the source client when present.

    Best-effort: any failure to deliver the message (e.g. a network error
    talking to the media server) is logged and swallowed here, never
    propagated, so notification delivery can never fail playback startup.
    """
    if not session_id:
        logger.info(
            "Skipping playback message; no active source session is available | "
            "origin=%s | text=%s",
            origin.value,
            message,
        )
        return

    try:
        if timeout_ms is None:
            playback_session.notify_session(session_id, message)
        else:
            playback_session.notify_session(session_id, message, timeout_ms)
    except Exception:
        logger.exception(
            "Failed to send playback message to source session | "
            "origin=%s | session_id=%s | text=%s",
            origin.value,
            session_id,
            message,
        )
