import logging

from home_cinema_control.media_servers.emby.session_events import (
    build_playback_intent_from_session,
    describe_session_playback_source,
    find_monitored_session,
)
from home_cinema_control.playback.dispatch import bridge_playback_is_active
from home_cinema_control.playback.intent import PlaybackOrigin
from home_cinema_control.playback.state import BridgePlaybackState


class EmbySessionMonitor:
    """
    Observes Emby Sessions updates and hands off to the OPPO bridge when a
    monitored TV client starts playing an item that belongs to a watched library.
    """

    def __init__(
        self,
        *,
        emby_session,
        playback_state: BridgePlaybackState,
        config_provider,
        dispatcher,
    ):
        self._emby_session = emby_session
        self._state = playback_state
        self._config_provider = config_provider
        self._dispatcher = dispatcher
        self._monitored_state = ""

    def reset(self) -> None:
        if not bridge_playback_is_active(self._state.playstate):
            logging.info("ws::Session monitor reset on reconnect")
            self._monitored_state = ""

    def on_sessions_update(self, sessions: list) -> None:
        config = self._config_provider()
        device_id = config["playback"]["hcc_controlled_device"]
        if not device_id:
            return

        logging.debug(
            "Ws:Checking sessions for monitored device | sessions=%s", len(sessions)
        )

        item_data = find_monitored_session(sessions, device_id)
        item_data_list = None

        try:
            now_playing = item_data.get("NowPlayingItem") if item_data else None
            if now_playing:
                item_data_list = self._emby_session.get_item_info(
                    item_data["UserId"], now_playing["Id"]
                )
                logging.info(
                    "Ws:Monitored item detected | device=%s | title=%s | type=%s | container=%s",
                    item_data.get("DeviceName"),
                    now_playing.get("Name"),
                    now_playing.get("Type"),
                    now_playing.get("Container"),
                )
        except Exception as e:
            logging.warning("Ws:Could not load monitored item details: %s", e)

        try:
            if item_data["NowPlayingItem"]:
                if self._monitored_state == "":
                    self._monitored_state = item_data["NowPlayingItem"]["Name"]
                    self._handle_new_playback(item_data, item_data_list, config)
                elif item_data["NowPlayingItem"]["Name"] == self._monitored_state:
                    logging.info(
                        "Continue playing | device=%s | title=%s",
                        item_data["DeviceName"],
                        self._monitored_state,
                    )
                else:
                    logging.info(
                        "Changed to different item | device=%s | prev=%s | new=%s",
                        item_data["DeviceName"],
                        self._monitored_state,
                        item_data["NowPlayingItem"]["Name"],
                    )
        except Exception:
            self._handle_playback_ended(item_data)

    def _handle_new_playback(
        self,
        item_data: dict,
        item_data_list: dict | None,
        config: dict,
    ) -> None:
        item_name = item_data["NowPlayingItem"]["Name"]
        item_lib_id = item_data["NowPlayingItem"].get("Path", "")

        library_name, found = self._find_matching_library(item_lib_id, config)

        if not found:
            logging.info("item not in any active library: %s", item_name)
            return

        if not self._has_verified_path_mapping(item_lib_id, config):
            logging.info(
                "item is in an active library but has no verified path mapping: %s",
                item_name,
            )
            return

        logging.info("library match | item=%s | library=%s", item_name, library_name)

        userdata = (item_data_list or {}).get("UserData") or {}
        playback_source = describe_session_playback_source(
            item_data,
            item_info=item_data_list,
            item_user_data=userdata,
        )
        logging.info(
            "Emby monitored playback source | "
            "item_id=%s | name=%s | item_type=%s | "
            "item_container=%s | item_video_type=%s | "
            "media_source_id=%s | media_source_container=%s | "
            "media_source_video_type=%s | "
            "session_position_present=%s | "
            "session_position_ticks=%s | "
            "saved_position_ticks=%s | played=%s | "
            "play_count=%s | played_percentage=%s | "
            "audio_stream_index=%s | subtitle_stream_index=%s",
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

        playback_intent = build_playback_intent_from_session(
            item_data,
            monitored_device_id=config["playback"]["hcc_controlled_device"],
            item_user_data=userdata,
        )
        if playback_intent is None:
            logging.warning("Ws:Could not build playback intent from session")
            return

        logging.info(
            "Ws:Preparing playback handoff | item_id=%s | device=%s | "
            "start_seconds=%s | audio=%s | subtitle=%s",
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
        if config["playback"]["use_all_libraries"]:
            return "All Libraries Enabled", True

        for view in config["playback"]["libraries"]:
            if view["Active"]:
                if self._emby_session.is_item_path_in_library(view["Id"], item_path):
                    return view["Name"], True

        return "", False

    def _has_verified_path_mapping(self, item_path: str, config: dict) -> bool:
        for mapping in config["playback"].get("path_mappings", []):
            source_path = str(mapping.get("source_path", "") or "")
            if source_path and source_path in item_path and mapping.get("verified"):
                return True
        return False

    def _handle_playback_ended(self, item_data: dict | None) -> None:
        if self._monitored_state == "":
            return

        if bridge_playback_is_active(self._state.playstate):
            logging.info(
                "Keeping monitored state during bridge playback | "
                "monitored_state=%s | playstate=%s",
                self._monitored_state,
                self._state.playstate,
            )
            return

        logging.info(
            "Stopped playing | device=%s | title=%s",
            item_data.get("DeviceName") if item_data else None,
            self._monitored_state,
        )
        self._monitored_state = ""
