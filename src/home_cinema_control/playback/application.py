from __future__ import annotations

import logging
import time

from home_cinema_control.playback.dispatch import bridge_playback_is_active
from home_cinema_control.playback.handoff import (
    PlaybackHandoffService,
    _should_stop_source_client_before_handoff as _handoff_should_stop_source_client,
)
from home_cinema_control.playback.intent import PlaybackIntent, PlaybackOrigin
from home_cinema_control.playback.oppo_lifecycle import (
    MediaPlayerLifecycleService,
    OppoPlaybackLifecycleService,
)
from home_cinema_control.playback.state import BridgePlaybackState
from home_cinema_control.playback.state_detector import PlaybackStateDetector
from home_cinema_control.playback.thread_lifecycle import PlaybackThreadLifecycle


logger = logging.getLogger(__name__)
_should_stop_source_client_before_handoff = _handoff_should_stop_source_client


class PlaybackApplicationService:
    """Application facade for playback requests and replacement admission.

    The handoff service owns the synchronous playback lifecycle. This facade
    decides whether an incoming intent is new, duplicate, or a replacement and
    delegates thread/replacement coordination to PlaybackThreadLifecycle.
    """

    def __init__(
        self,
        *,
        playback_session,
        playback_state: BridgePlaybackState,
        reload_config,
        media_server_playback_services=None,
        media_player_lifecycle: MediaPlayerLifecycleService | None = None,
        oppo_lifecycle: OppoPlaybackLifecycleService | None = None,
        playback_event_dispatcher=None,
        playback_event_publisher=None,
        playback_state_detector: PlaybackStateDetector | None = None,
        stop_active_playback=None,
        sleep=time.sleep,
    ) -> None:
        self._playback_session = playback_session
        self._state = playback_state
        self._reload_config = reload_config
        self._media_player_lifecycle = (
            media_player_lifecycle
            or oppo_lifecycle
            or MediaPlayerLifecycleService()
        )
        self._playback_event_publisher = playback_event_publisher or playback_event_dispatcher
        self._sleep = sleep
        self._thread_lifecycle = None
        self._handoff = PlaybackHandoffService(
            playback_session=playback_session,
            playback_state=playback_state,
            media_server_playback_services=media_server_playback_services,
            media_player_lifecycle=self._media_player_lifecycle,
            playback_event_publisher=self._playback_event_publisher,
            playback_state_detector=playback_state_detector,
            replacement_requested=lambda: self._thread_lifecycle.replacement_requested,
        )
        self._stop_active_playback = stop_active_playback or (
            self._handoff.stop_active_playback_before_replacement
        )
        self._thread_lifecycle = PlaybackThreadLifecycle(
            start_playback=self._start_from_intent,
            reload_config=self._reload_config,
            stop_active_playback=self._stop_active_playback,
        )

    @property
    def active_publisher(self):
        return self._handoff.active_publisher

    @property
    def active_media_player(self):
        return self._handoff.active_media_player

    def request_playback_from_intent(
        self,
        intent: PlaybackIntent,
        *,
        origin: PlaybackOrigin,
    ) -> bool:
        if self._is_duplicate_intent(intent):
            logger.info(
                "Ignoring duplicate playback request | item_id=%s | playstate=%s",
                intent.media_item_id,
                self._state.playstate,
            )
            return False

        self._wait_for_loading_to_finish()
        if self._state.playstate in ("Playing", "Replay"):
            logger.info("already playing, replacing")
            return self.replace_from_intent(intent, origin=origin)

        self.start_from_intent(intent, origin=origin)
        return True

    def start_from_intent(self, intent: PlaybackIntent, *, origin: PlaybackOrigin) -> None:
        self._thread_lifecycle.start(intent, origin=origin)

    def replace_from_intent(self, intent: PlaybackIntent, *, origin: PlaybackOrigin) -> bool:
        return self._thread_lifecycle.replace(intent, origin=origin)

    def stop_active_playback_and_wait(self) -> bool:
        """Stop active playback and wait for its synchronous cleanup flow."""
        return self._thread_lifecycle.stop_active_and_wait()

    def observe_playback_state(self, state) -> None:
        """Accept a player observation from media-server command handling."""
        self._handoff.observe_playback_state(state)

    def _is_duplicate_intent(self, intent: PlaybackIntent) -> bool:
        if not bridge_playback_is_active(self._state.playstate):
            return False
        active_session = self._state.active_session
        return active_session is not None and str(
            active_session.media_item_id
        ) == str(intent.media_item_id)

    def _wait_for_loading_to_finish(self) -> None:
        if self._state.playstate not in ("Loading", "Replay"):
            return

        logger.info("waiting for loading state to finish")
        timeout = 60
        elapsed = 0
        while self._state.playstate == "Loading" and elapsed < timeout:
            self._sleep(3)
            elapsed = elapsed + 3

    def _start_from_intent(
        self,
        intent: PlaybackIntent,
        *,
        origin: PlaybackOrigin,
    ):
        """Compatibility callback retained for the thread lifecycle seam."""
        return self._handoff.run(intent, origin=origin)
