from __future__ import annotations

import logging

from home_cinema_control.config.manager import active_media_server_config
from home_cinema_control.media_servers.common.session_monitor import (
    MediaServerSessionMonitor,
    is_ambient_theme_audio,
)
from home_cinema_control.media_servers.emby.session_events import (
    sessions_from_payload,
)


class EmbySessionMonitor(MediaServerSessionMonitor):
    def __init__(self, *, emby_session, **kwargs):
        super().__init__(
            provider_name="Emby",
            is_item_path_in_library=emby_session.is_item_path_in_library,
            **kwargs,
        )
        self._emby_session = emby_session

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
        session = self.select_monitored_session(sessions_from_payload(sessions), device_id)
        if session is not None and is_ambient_theme_audio(session.now_playing):
            self.on_monitored_session(session, None, config=config)
            return
        item_playback_info = self._load_item_playback_info(session)
        if session is not None and session.now_playing is not None and item_playback_info is None:
            return
        self.on_monitored_session(session, item_playback_info, config=config)

    def _load_item_playback_info(self, session):
        if session is None or session.now_playing is None:
            return None
        try:
            item_playback_info = self._emby_session.get_item_playback_info(
                session.user_id,
                session.now_playing.item_id,
                session.media_source_id,
            )
            self.clear_item_lookup_failure()
            return item_playback_info
        except Exception as exc:
            logging.exception("%s ws: could not load monitored item details", self._provider_name)
            self.record_item_lookup_failure(session, exc)
            return None
