import logging

from home_cinema_control.media_servers.common.constants import DEVICE_ID
from home_cinema_control.media_servers.common.models import (
    find_controlling_session_id as resolve_controlling_session_id,
)
from home_cinema_control.media_servers.common.playback_source import (
    MediaServerPlaybackSource,
    media_server_playback_source_from_item,
)
from home_cinema_control.media_servers.common.track_mapping import (
    source_audio_to_player_index,
    source_subtitle_to_player_index,
)
from home_cinema_control.media_servers.jellyfin.client import JellyfinClient
from home_cinema_control.media_servers.jellyfin.session_events import session_from_payload
from home_cinema_control.playback.state import BridgePlaybackState


class JellyfinSession:
    def __init__(self, config, playback_state: BridgePlaybackState):
        self.config = config
        self._state = playback_state
        self.client = JellyfinClient.from_config(config)
        self.user_info = self.client.authenticate()
        self.lang = None
        logging.info("JellyfinSession started")

    def stop_session_playback(self, session_id):
        response = self.client.stop_session_playback(session_id, {"Command": "Stop"})
        logging.debug("stop_session_playback response: %s", response.text)
        return response

    def notify_session(self, session_id, text, timeout=3500):
        response = self.client.send_session_message(session_id, text, timeout)
        logging.debug("notify_session response: %s", response.text)
        return response

    def find_controlling_session_id(self, controlling_user_id):
        """Find the real client session that issued a remote Play command.

        Jellyfin's "Play" websocket message shares Emby's protocol design and
        the same gap: it never identifies the controller's own session — only
        echoes back the target (this bridge's) session id. Maps the raw
        Sessions payload to MediaServerSession at this edge, then delegates
        the actual resolution policy to the shared, provider-neutral
        implementation (see common/models.py's find_controlling_session_id).
        get_sessions_by_user narrows server-side (confirmed param, see its
        docstring) but the client-side filtering below is what actually
        guarantees correctness regardless.
        """
        if not controlling_user_id:
            return None

        sessions = self.client.get_sessions_by_user(controlling_user_id)
        if not isinstance(sessions, list):
            return None

        mapped_sessions = [session_from_payload(session) for session in sessions]
        return resolve_controlling_session_id(
            mapped_sessions,
            controlling_user_id=controlling_user_id,
            own_device_id=DEVICE_ID,
        )

    def set_capabilities(self):
        response = self.client.set_capabilities(
            {
                "SupportsMediaControl": True,
                "PlayableMediaTypes": ["Video", "Audio"],
                "SupportedCommands": [
                    "Play",
                    "Playstate",
                    "SetAudioStreamIndex",
                    "SetSubtitleStreamIndex",
                    "DisplayMessage",
                    "PlayMediaSource",
                ],
                "DeviceProfile": {},
            }
        )
        logging.debug("set_capabilities response: %s", response.text)
        self._refresh_session_info()
        return response

    def get_item_info(self, user_id, item_id):
        return self.client.get_item_info(user_id, item_id)

    def get_media_source_info(self, user_id, item_id, mediasource_id) -> MediaServerPlaybackSource:
        item_data = self.client.get_item_info(user_id, item_id)
        return media_server_playback_source_from_item(item_data, mediasource_id)

    def is_item_path_in_library(self, view_id, item_path):
        for folder in self.client.get_virtual_folders():
            if str(folder.get("ItemId", "") or folder.get("Id", "")) != str(view_id):
                if folder.get("Name") != view_id:
                    continue
            for location in folder.get("Locations", []):
                if item_path.startswith(location):
                    return True
        return False

    def resolve_audio_track_index(self, user_id, item_id, index):
        response = self.get_item_info(user_id, item_id)
        return source_audio_to_player_index(response.get("MediaStreams", []), index)

    def resolve_subtitle_track_index(self, user_id, item_id, index):
        response = self.get_item_info(user_id, item_id)
        return source_subtitle_to_player_index(response.get("MediaStreams", []), index)

    def _session_info(self):
        session_info = (self.user_info or {}).get("SessionInfo")
        if session_info and session_info.get("Id"):
            return session_info
        self._refresh_session_info()
        session_info = (self.user_info or {}).get("SessionInfo")
        if session_info and session_info.get("Id"):
            return session_info
        raise RuntimeError(
            "Jellyfin session is not available for Home Cinema Control client."
        )

    def _refresh_session_info(self):
        session = self._find_own_session()
        if not session:
            logging.warning(
                "Could not resolve Jellyfin session for bridge client | device_id=%s",
                DEVICE_ID,
            )
            return None
        self.user_info = dict(self.user_info or {})
        self.user_info["SessionInfo"] = session
        return session

    def _find_own_session(self):
        sessions = self.client.get_sessions_by_device(DEVICE_ID)
        if not isinstance(sessions, list):
            return None
        user_id = ((self.user_info or {}).get("User") or {}).get("Id")
        for session in sessions:
            if user_id and session.get("UserId") != user_id:
                continue
            return session
        return sessions[0] if sessions else None
