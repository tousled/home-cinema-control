import logging
from collections.abc import Callable
from typing import Any

from home_cinema_control.config.manager import active_media_server_config
from home_cinema_control.media_servers.common.models import (
    MediaServerItemPlaybackInfo,
    MediaServerSession,
)
from home_cinema_control.playback.dispatch import bridge_playback_is_active
from home_cinema_control.playback.intent import PlaybackIntent, PlaybackOrigin
from home_cinema_control.playback.state import BridgePlaybackState
from home_cinema_control.playback.time_units import TICKS_PER_SECOND


class MediaServerSessionMonitor:
    """
    Observes media-server Sessions updates and hands off to the OPPO bridge when
    a monitored TV client starts playing an item from an active mapped library.

    The monitor reasons over :class:`MediaServerSession` domain objects only.
    Each provider supplies ``find_monitored_session`` as its inbound mapper
    (wire payload -> ``MediaServerSession``); the handoff policy below never
    touches provider wire shape.
    """

    def __init__(
        self,
        *,
        provider_name: str,
        media_server_session,
        playback_state: BridgePlaybackState,
        config_provider,
        dispatcher,
        find_monitored_session: Callable[
            [list[dict[str, Any]], str], MediaServerSession | None
        ],
    ):
        self._provider_name = provider_name
        self._session = media_server_session
        self._state = playback_state
        self._config_provider = config_provider
        self._dispatcher = dispatcher
        self._find_monitored_session = find_monitored_session
        self._monitored_state = ""

    def reset(self) -> None:
        if not bridge_playback_is_active(self._state.playstate):
            logging.info("%s session monitor reset on reconnect", self._provider_name)
            self._monitored_state = ""

    def on_sessions_update(self, sessions: list) -> None:
        config = self._config_provider()
        device_id = active_media_server_config(config).playback.hcc_controlled_device
        if not device_id:
            return

        logging.debug(
            "%s ws: checking sessions for monitored device | sessions=%s",
            self._provider_name,
            len(sessions),
        )

        session = self._find_monitored_session(sessions, device_id)
        item_playback_info = None

        if session is not None and session.now_playing is not None:
            try:
                item_playback_info = self._session.get_item_playback_info(
                    session.user_id,
                    session.now_playing.item_id,
                    session.media_source_id,
                )
                logging.info(
                    "%s monitored item detected | device=%s | title=%s | "
                    "type=%s | container=%s",
                    self._provider_name,
                    session.device_name,
                    session.now_playing.name,
                    session.now_playing.item_type,
                    session.now_playing.container,
                )
            except Exception as e:
                logging.exception(
                    "%s ws: could not load monitored item details: %s",
                    self._provider_name,
                    e,
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
        item_path = session.now_playing.path

        library_name, found = self._find_matching_library(item_path, config)

        if not found:
            logging.info("%s item not in any active library: %s", self._provider_name, item_name)
            return

        if not self._has_verified_path_mapping(item_path, config):
            logging.info(
                "%s item is in an active library but has no verified path mapping: %s",
                self._provider_name,
                item_name,
            )
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
                if self._session.is_item_path_in_library(view.id, item_path):
                    return view.name, True

        return "", False

    def _has_verified_path_mapping(self, item_path: str, config: dict) -> bool:
        for mapping in active_media_server_config(config).playback.path_mappings:
            if mapping.source_path and mapping.source_path in item_path and mapping.verified:
                return True
        return False

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
