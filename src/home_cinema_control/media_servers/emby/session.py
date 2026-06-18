import logging

from home_cinema_control.media_servers.emby.track_mapping import (
    source_audio_to_player_index,
    source_subtitle_to_player_index,
)

from home_cinema_control.media_servers.emby.client import EmbyClient
from home_cinema_control.media_servers.emby.constants import DEVICE_ID
from home_cinema_control.playback.state import BridgePlaybackState


class EmbySession:
    def __init__(self, config, playback_state: BridgePlaybackState):
        self.config = config
        self._state = playback_state
        self.client = EmbyClient.from_config(config)
        self.user_info = self.client.authenticate()
        self.lang = None
        logging.info("EmbySession started")

    def stop_session_playback(self, session_id):
        response = self.client.stop_session_playback(session_id, {"Command": "Stop"})
        logging.debug("stop_session_playback response: %s", response.text)
        return response

    def notify_session(self, session_id, text, timeout=3500):
        response = self.client.send_session_message(session_id, text, timeout)
        logging.debug("notify_session response: %s", response.text)
        return response

    def set_capabilities(self):
        message_data = {
            "IconUrl": "https://img.alicdn.com/imgextra/i1/1840220527/O1CN018lXYlv1FlPES6Bgcw_!!1840220527.png",
            "SupportsMediaControl": True,
            "PlayableMediaTypes": ["Video", "Audio"],
            "SupportedCommands": [
                "Play",
                "Playstate",
                "MoveUp",
                "MoveDown",
                "MoveLeft",
                "MoveRight",
                "Select",
                "Back",
                "ToggleContextMenu",
                "ToggleFullscreen",
                "ToggleOsdMenu",
                "GoHome",
                "PageUp",
                "NextLetter",
                "GoToSearch",
                "GoToSettings",
                "PageDown",
                "PreviousLetter",
                "TakeScreenshot",
                "VolumeUp",
                "VolumeDown",
                "ToggleMute",
                "SendString",
                "DisplayMessage",
                "SetAudioStreamIndex",
                "SetSubtitleStreamIndex",
                "SetRepeatMode",
                "Mute",
                "Unmute",
                "SetVolume",
                "PlayNext",
                "PlayMediaSource",
            ],
            "DeviceProfile": {},
        }

        logging.debug("set_capabilities payload: %s", message_data)
        response = self.client.set_capabilities(message_data)
        logging.debug("set_capabilities response: %s", response.text)
        self._refresh_session_info()
        return response

    def get_item_info(self, user_id, item_id):
        return self.client.get_item_info(user_id, item_id)

    def get_media_source_info(self, user_id, item_id, mediasource_id):
        item_data = self.client.get_item_info(user_id, item_id)

        for mediasource in item_data["MediaSources"]:
            if mediasource["Id"] == mediasource_id:
                return mediasource

        return item_data

    def is_item_path_in_library(self, view_id, item_path):
        media_folders = self.client.get_selectable_media_folders()

        for folder in media_folders:
            if folder["Id"] == view_id:
                for subfolder in folder["SubFolders"]:
                    if item_path.startswith(subfolder["Path"]):
                        return True

        return False

    def resolve_audio_track_index(self, user_id, item_id, index):
        response = self.get_item_info(user_id, item_id)
        return source_audio_to_player_index(response["MediaStreams"], index)

    def resolve_subtitle_track_index(self, user_id, item_id, index):
        response = self.get_item_info(user_id, item_id)
        logging.debug("MediaStreams: %s", response["MediaStreams"])
        return source_subtitle_to_player_index(response["MediaStreams"], index)

    def _session_info(self):
        session_info = (self.user_info or {}).get("SessionInfo")

        if session_info and session_info.get("Id"):
            return session_info

        self._refresh_session_info()
        session_info = (self.user_info or {}).get("SessionInfo")

        if session_info and session_info.get("Id"):
            return session_info

        raise RuntimeError(
            "Emby session is not available for Home Cinema Control client."
        )

    def _refresh_session_info(self):
        session = self._find_own_session()

        if not session:
            logging.warning(
                "Could not resolve Emby session for bridge client | device_id=%s",
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
