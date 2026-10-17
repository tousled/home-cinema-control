import logging
from collections.abc import Callable
from typing import Any

from home_cinema_control.config.manager import active_media_server_config
from home_cinema_control.media_servers.common.models import (
    MediaServerItemPlaybackInfo,
    MediaServerSession,
)
from home_cinema_control.media_servers.common.path_matching import (
    longest_matching_mapping,
)
from home_cinema_control.playback.dispatch import bridge_playback_is_active
from home_cinema_control.playback.diagnostics import (
    diagnose_media_server_item_unavailable,
    diagnose_media_server_library_not_matched,
    diagnose_media_server_monitored_device_not_found,
    diagnose_path_mapping_not_found,
    diagnose_path_mapping_not_verified,
)
from home_cinema_control.playback.events import PlaybackRejectedEvent, new_playback_event_id
from home_cinema_control.playback.intent import PlaybackIntent, PlaybackOrigin
from home_cinema_control.playback.state import BridgePlaybackState
from home_cinema_control.playback.time_units import TICKS_PER_SECOND


class MediaServerSessionMonitor:
    """
    Observes media-server Sessions updates and hands off to the OPPO bridge when
    a monitored TV client starts playing an item from an active mapped library.

    The monitor reasons over :class:`MediaServerSession` domain objects only.
    Each provider maps its wire payload, loads provider-specific item details,
    and calls :meth:`on_monitored_session`; the policy below never touches
    provider wire shape or a provider session object.
    """

    def __init__(
        self,
        *,
        provider_name: str,
        playback_state: BridgePlaybackState,
        config_provider,
        dispatcher,
        is_item_path_in_library: Callable[[str, str], bool],
        playback_event_publisher=None,
    ):
        self._provider_name = provider_name
        self._state = playback_state
        self._config_provider = config_provider
        self._dispatcher = dispatcher
        self._playback_event_publisher = playback_event_publisher
        self._is_item_path_in_library = is_item_path_in_library
        self._monitored_state = ""
        self._last_device_snapshot_fingerprint = None
        self._last_item_lookup_failure_fingerprint = None

    def reset(self) -> None:
        if not bridge_playback_is_active(self._state.playstate):
            logging.info("%s session monitor reset on reconnect", self._provider_name)
            self._monitored_state = ""
            self._last_device_snapshot_fingerprint = None
            self._last_item_lookup_failure_fingerprint = None

    def select_monitored_session(
        self,
        sessions: list[MediaServerSession],
        configured_device_id: str,
    ) -> MediaServerSession | None:
        """Select a configured device and explain a no-match snapshot once."""
        session = next(
            (candidate for candidate in sessions if candidate.device_id == configured_device_id),
            None,
        )
        if session is not None:
            self._last_device_snapshot_fingerprint = None
            return session

        candidates = [
            {
                "device_id": candidate.device_id,
                "device_name": candidate.device_name,
                "client_name": candidate.client_name,
                "has_now_playing": candidate.now_playing is not None,
            }
            for candidate in sessions
        ]
        candidates.sort(
            key=lambda candidate: (
                candidate["device_id"],
                candidate["device_name"],
                candidate["client_name"],
            )
        )
        fingerprint = (
            configured_device_id,
            tuple(
                (
                    candidate["device_id"],
                    candidate["device_name"],
                    candidate["client_name"],
                    candidate["has_now_playing"],
                )
                for candidate in candidates
            ),
        )
        if fingerprint != self._last_device_snapshot_fingerprint:
            logging.warning(
                "%s monitored device not found | code=MEDIA_SERVER_MONITORED_DEVICE_NOT_FOUND "
                "| configured_device_id=%s | candidates=%s",
                self._provider_name,
                configured_device_id,
                candidates,
            )
            self._state.record_diagnostic(
                diagnose_media_server_monitored_device_not_found(
                    provider=self._provider_name,
                    configured_device_id=configured_device_id,
                    candidates=candidates,
                )
            )
            self._last_device_snapshot_fingerprint = fingerprint
        return None

    def record_item_lookup_failure(
        self, session: MediaServerSession, error: Exception
    ) -> None:
        """Record one provider item lookup failure per unchanged failure state."""
        now_playing = session.now_playing
        fingerprint = (
            session.device_id,
            now_playing.item_id if now_playing else "",
            session.media_source_id,
            type(error).__name__,
            str(error),
        )
        if fingerprint == self._last_item_lookup_failure_fingerprint:
            return
        self._last_item_lookup_failure_fingerprint = fingerprint
        diagnostic = diagnose_media_server_item_unavailable(
            str(error),
            provider=self._provider_name,
            session=session,
            error_type=type(error).__name__,
        )
        self._record_playback_rejection(diagnostic)

    def clear_item_lookup_failure(self) -> None:
        self._last_item_lookup_failure_fingerprint = None

    def on_monitored_session(
        self,
        session: MediaServerSession | None,
        item_playback_info: MediaServerItemPlaybackInfo | None,
        *,
        config: dict,
    ) -> None:
        """Apply shared admission policy to provider-mapped domain data."""
        if session is not None and is_ambient_theme_audio(session.now_playing):
            logging.debug(
                "%s ignoring ambient theme audio | device=%s | title=%s | path=%s",
                self._provider_name,
                session.device_name,
                session.now_playing.name,
                session.now_playing.path,
            )
            return

        if session is not None and session.now_playing is not None:
            logging.info(
                "%s monitored item detected | device=%s | title=%s | "
                "type=%s | container=%s",
                self._provider_name,
                session.device_name,
                session.now_playing.name,
                session.now_playing.item_type,
                session.now_playing.container,
            )

        if session is None or session.now_playing is None:
            self._handle_playback_ended(session)
            return

        item_name = session.now_playing.name
        if self._monitored_state == "":
            self._monitored_state = item_name
            self._handle_new_playback(session, item_playback_info, config)
        elif item_name == self._monitored_state:
            logging.info(
                "Continue playing | device=%s | title=%s",
                session.device_name,
                self._monitored_state,
            )
        else:
            logging.info(
                "Changed to different item | device=%s | prev=%s | new=%s",
                session.device_name,
                self._monitored_state,
                item_name,
            )

    def _handle_new_playback(
        self,
        session: MediaServerSession,
        item_playback_info: MediaServerItemPlaybackInfo | None,
        config: dict,
    ) -> None:
        item_name = session.now_playing.name
        item_path = (
            item_playback_info.media_source_path
            if item_playback_info and item_playback_info.media_source_path
            else session.now_playing.path
        )

        library_name, found = self._find_matching_library(item_path, config)

        if not found:
            logging.info("%s item not in any active library: %s", self._provider_name, item_name)
            diagnostic = diagnose_media_server_library_not_matched(
                provider=self._provider_name,
                item_name=item_name,
                item_path=item_path,
            )
            self._record_playback_rejection(diagnostic)
            return

        mapping = self._matching_path_mapping(item_path, config)
        if mapping is None:
            logging.info(
                "%s item is in an active library but has no matching path mapping: %s",
                self._provider_name,
                item_name,
            )
            diagnostic = diagnose_path_mapping_not_found(
                provider=self._provider_name,
                item_name=item_name,
                item_path=item_path,
            )
            self._record_playback_rejection(diagnostic)
            return

        if mapping.get("verified") is not True:
            source_path = str(mapping.get("source_path") or "")
            logging.info(
                "%s item matches an unverified path mapping | item=%s | source_path=%s",
                self._provider_name,
                item_name,
                source_path,
            )
            diagnostic = diagnose_path_mapping_not_verified(
                provider=self._provider_name,
                item_name=item_name,
                item_path=item_path,
                source_path=source_path,
            )
            self._record_playback_rejection(diagnostic)
            return

        logging.info(
            "%s library match | item=%s | library=%s",
            self._provider_name,
            item_name,
            library_name,
        )

        item_playback_info = item_playback_info or MediaServerItemPlaybackInfo()
        playback_source = describe_session_playback_source(
            session,
            item_playback_info=item_playback_info,
        )
        logging.info(
            "%s monitored playback source | "
            "item_id=%s | name=%s | item_type=%s | "
            "item_container=%s | item_video_type=%s | "
            "media_source_id=%s | media_source_container=%s | "
            "media_source_path=%s | "
            "media_source_video_type=%s | "
            "session_position_present=%s | "
            "session_position_ticks=%s | "
            "saved_position_ticks=%s | played=%s | "
            "play_count=%s | played_percentage=%s | "
            "audio_stream_index=%s | subtitle_stream_index=%s",
            self._provider_name,
            playback_source["item_id"],
            playback_source["item_name"],
            playback_source["item_type"],
            playback_source["item_container"],
            playback_source["item_video_type"],
            playback_source["media_source_id"],
            playback_source["media_source_container"],
            playback_source["media_source_path"],
            playback_source["media_source_video_type"],
            playback_source["session_position_ticks_present"],
            playback_source["session_position_ticks"],
            playback_source["saved_position_ticks"],
            playback_source["played"],
            playback_source["play_count"],
            playback_source["playback_percentage"],
            playback_source["audio_stream_index"],
            playback_source["subtitle_stream_index"],
        )

        playback_intent = playback_intent_from_session(
            session,
            saved_position_ticks=item_playback_info.saved_position_ticks,
        )
        if playback_intent is None:
            logging.error(
                "%s ws: could not build playback intent from session",
                self._provider_name,
            )
            return

        logging.info(
            "%s ws: preparing playback handoff | item_id=%s | device=%s | "
            "start_seconds=%s | audio=%s | subtitle=%s",
            self._provider_name,
            playback_intent.media_item_id,
            playback_intent.source_device_name,
            playback_intent.start_position_seconds,
            playback_intent.selected_audio_track_id,
            playback_intent.selected_subtitle_track_id,
        )

        self._dispatcher.dispatch(
            playback_intent,
            origin=PlaybackOrigin.OBSERVED_TV_CLIENT,
        )

    def _find_matching_library(
        self, item_path: str, config: dict
    ) -> tuple[str, bool]:
        playback = active_media_server_config(config).playback
        if playback.use_all_libraries:
            return "All Libraries Enabled", True

        for view in playback.libraries:
            if view.active:
                if self._is_item_path_in_library(view.id, item_path):
                    return view.name, True

        return "", False

    def _matching_path_mapping(self, item_path: str, config: dict):
        mappings = [
            mapping.model_dump()
            for mapping in active_media_server_config(config).playback.path_mappings
        ]
        return longest_matching_mapping(item_path, mappings)

    def _record_playback_rejection(self, diagnostic) -> None:
        self._state.record_diagnostic(diagnostic)
        self._publish_playback_rejected(diagnostic)

    def _publish_playback_rejected(self, diagnostic) -> None:
        if self._playback_event_publisher is None:
            return
        try:
            self._playback_event_publisher.publish(
                PlaybackRejectedEvent(
                    event_id=new_playback_event_id(),
                    component=diagnostic.component,
                    diagnostic_code=diagnostic.code,
                    provider=self._provider_name.lower(),
                )
            )
        except Exception:
            logging.exception(
                "%s playback rejection event dispatch failed | code=%s",
                self._provider_name,
                diagnostic.code,
            )

    def _handle_playback_ended(self, session: MediaServerSession | None) -> None:
        if self._monitored_state == "":
            return

        if bridge_playback_is_active(self._state.playstate):
            logging.info(
                "Keeping %s monitored state during bridge playback | "
                "monitored_state=%s | playstate=%s",
                self._provider_name,
                self._monitored_state,
                self._state.playstate,
            )
            return

        logging.info(
            "Stopped playing | device=%s | title=%s",
            session.device_name if session else None,
            self._monitored_state,
        )
        self._monitored_state = ""


def playback_intent_from_session(
    session: MediaServerSession,
    *,
    saved_position_ticks: int | None = None,
) -> PlaybackIntent | None:
    """Map an observed :class:`MediaServerSession` to a handoff intent.

    Provider-neutral: it reads only HCC domain fields. The 100ns tick value
    carried by the session is converted to seconds here, at the domain level.
    """
    now_playing = session.now_playing
    if now_playing is None:
        return None

    start_position_ticks = session.position_ticks
    if start_position_ticks is None:
        start_position_ticks = saved_position_ticks or 0

    return PlaybackIntent(
        media_item_id=now_playing.item_id,
        media_source_id=session.media_source_id,
        source_user_id=session.user_id,
        source_client_session_id=session.client_session_id,
        source_device_id=session.device_id,
        source_device_name=session.device_name,
        start_position_seconds=int(start_position_ticks or 0) // TICKS_PER_SECOND,
        selected_audio_track_id=session.audio_stream_index,
        selected_subtitle_track_id=session.subtitle_stream_index,
    )


def describe_session_playback_source(
    session: MediaServerSession,
    *,
    item_playback_info: MediaServerItemPlaybackInfo,
) -> dict[str, Any]:
    """Build the diagnostics snapshot logged at handoff. Logging only.

    Operates on domain objects only: the session and the item's mapped
    playback info. Neither carries provider wire shape.
    """
    now_playing = session.now_playing

    return {
        "item_id": now_playing.item_id if now_playing else None,
        "item_name": now_playing.name if now_playing else None,
        "item_type": now_playing.item_type if now_playing else None,
        "item_container": now_playing.container if now_playing else None,
        "item_video_type": now_playing.video_type if now_playing else None,
        "media_source_id": session.media_source_id or None,
        "media_source_path": item_playback_info.media_source_path,
        "media_source_container": item_playback_info.media_source_container,
        "media_source_video_type": item_playback_info.media_source_video_type,
        "session_position_ticks_present": session.position_ticks is not None,
        "session_position_ticks": session.position_ticks,
        "saved_position_ticks": item_playback_info.saved_position_ticks,
        "played": item_playback_info.played,
        "play_count": item_playback_info.play_count,
        "playback_percentage": item_playback_info.playback_percentage,
        "audio_stream_index": session.audio_stream_index,
        "subtitle_stream_index": session.subtitle_stream_index,
    }


def is_ambient_theme_audio(now_playing) -> bool:
    if now_playing is None:
        return False

    normalized_path = (now_playing.path or "").replace("\\", "/").lower()
    return normalized_path.rsplit("/", 1)[-1] == "theme.mp3"
