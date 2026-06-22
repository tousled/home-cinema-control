from __future__ import annotations

import time

from home_cinema_control.media_servers.emby.playback import MediaContentKind
from home_cinema_control.playback.intent import PlaybackOrigin
from home_cinema_control.playback.notification_sender import send_playback_message

STILL_WITH_YOU_THRESHOLD_SECONDS = 20.0
COLLISION_GUARD_MIN_INTERVAL_SECONDS = 2.5

_ACTION_LANG_KEYS = {
    MediaContentKind.MOVIE: "msg-startup-action-movie",
    MediaContentKind.EPISODE: "msg-startup-action-episode",
    MediaContentKind.CONCERT: "msg-startup-action-concert",
    MediaContentKind.LIVE_TV: "msg-startup-action-live-tv",
}


class _StartupMessageGate:
    """Skips a send if too little real time passed since the last one.

    Prevents a fast/warm startup from sending toasts faster than a user could
    read them; never delays or queues a send, only decides whether to skip it.
    """

    def __init__(self, *, min_interval_seconds: float = COLLISION_GUARD_MIN_INTERVAL_SECONDS) -> None:
        self._min_interval_seconds = min_interval_seconds
        self._last_sent_at: float | None = None

    def should_send(self) -> bool:
        now = time.monotonic()
        if (
            self._last_sent_at is not None
            and (now - self._last_sent_at) < self._min_interval_seconds
        ):
            return False
        self._last_sent_at = now
        return True


class PlaybackStartupMessagingService:
    """Narrates real playback-startup milestones to the source media-server client.

    Owns the six touchpoints from `.agents/specs/2026-06-22-playback-startup-messages.md`:
    received, locating, starting, fine-tuning, a still-with-you safety net, and the
    closing action message. Callers only see this interface — the collision guard,
    the wait timing, and the message catalog are private. Every send is best-effort
    via `send_playback_message`; a delivery failure never raises here.
    """

    def __init__(
        self,
        *,
        playback_session,
        origin: PlaybackOrigin,
        session_id: str | None,
        lang: dict,
        still_with_you_threshold_seconds: float = STILL_WITH_YOU_THRESHOLD_SECONDS,
    ) -> None:
        self._playback_session = playback_session
        self._origin = origin
        self._session_id = session_id
        self._lang = lang
        self._still_with_you_threshold_seconds = still_with_you_threshold_seconds
        self._gate = _StartupMessageGate()
        self._waiting_started_at: float | None = None
        self._still_with_you_sent = False

    def received(self) -> None:
        """Touchpoint 1: t=0, unconditional, closes the open loop immediately."""
        self._send_gated(self._lang["msg-startup-received"])

    def locating(self) -> None:
        """Touchpoint 2: sent once, before media path resolution begins."""
        self._send_gated(self._lang["msg-startup-locating"])

    def notify_waiting(self, _attempt: int) -> None:
        """Touchpoints 3 & 5: first call sends 'starting'; later calls send the
        'still with you' safety net once real elapsed time crosses the threshold.

        `_attempt` is accepted for compatibility with the orchestrator's
        `on_startup_waiting` callback shape but unused — timing is measured
        against the wall clock, not derived from poll-loop cadence.
        """
        if self._waiting_started_at is None:
            self._waiting_started_at = time.monotonic()
            self._send(self._lang["msg-startup-starting"])
            return

        if self._still_with_you_sent:
            return

        elapsed_seconds = time.monotonic() - self._waiting_started_at
        if elapsed_seconds >= self._still_with_you_threshold_seconds:
            self._still_with_you_sent = True
            self._send(self._lang["msg-startup-still-with-you"])

    def tracks_applying(self) -> None:
        """Touchpoint 4: sent once, when resume/audio/subtitle application begins."""
        self._send_gated(self._lang["msg-startup-fine-tuning"])

    def action(self, content_kind: MediaContentKind) -> None:
        """Touchpoint 6: sent once playback is confirmed active, for every origin."""
        lang_key = _ACTION_LANG_KEYS.get(content_kind, "msg-startup-action-generic")
        self._send(self._lang[lang_key])

    def _send_gated(self, message: str) -> None:
        if self._gate.should_send():
            self._send(message)

    def _send(self, message: str) -> None:
        send_playback_message(self._playback_session, self._origin, self._session_id, message)
