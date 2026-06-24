from __future__ import annotations

from home_cinema_control.config.manager import active_media_server_config
from home_cinema_control.media_servers.common.constants import DEVICE_ID
from home_cinema_control.network.http import get_http_session


class JellyfinClient:
    """Low-level HTTP client for the Jellyfin API."""

    def __init__(
        self,
        server_url: str,
        access_token: str,
        user_id: str,
        display_name: str = "",
        *,
        http_session=None,
    ):
        self.server_url = server_url.rstrip("/")
        self.access_token = access_token
        self.user_id = user_id
        self.display_name = display_name
        self._http = http_session or get_http_session("jellyfin")
        self.user_info = None

    @classmethod
    def from_config(cls, config):
        media_server = active_media_server_config(config)

        return cls(
            server_url=_config_value(media_server, "server_url"),
            access_token=_config_value(media_server, "access_token"),
            user_id=_config_value(media_server, "user_id"),
            display_name=_config_value(media_server, "display_name"),
        )

    def authenticate(self):
        if not self.access_token:
            raise RuntimeError(
                "Jellyfin authentication is not configured: missing media_server.access_token"
            )

        if not self.user_id:
            raise RuntimeError(
                "Jellyfin authentication is not configured: missing media_server.user_id"
            )

        self.user_info = {
            "AccessToken": self.access_token,
            "User": {
                "Id": self.user_id,
                "Name": self.display_name,
            },
        }
        return self.user_info

    def get_headers(self, user_info=None):
        auth_string = (
            'MediaBrowser Client="Home Cinema Control",'
            'Device="Home Cinema Control",'
            f'DeviceId="{DEVICE_ID}",'
            'Version="1.0.0"'
        )

        if user_info:
            auth_string += ',UserId="' + user_info["User"]["Id"] + '"'

        headers = {
            "Accept-encoding": "gzip",
            "Accept-Charset": "UTF-8,*",
            "X-Emby-Authorization": auth_string,
        }

        if user_info:
            token = user_info["AccessToken"]
            headers["X-Emby-Token"] = token
            headers["X-MediaBrowser-Token"] = token

        return headers

    def set_capabilities(self, payload):
        return self.post("/Sessions/Capabilities/Full", json=payload)

    def notify_playback_started(self, payload):
        return self.post("/Sessions/Playing", json=payload)

    def report_playback_progress(self, payload):
        return self.post("/Sessions/Playing/Progress", json=payload)

    def notify_playback_stopped(self, payload):
        return self.post("/Sessions/Playing/Stopped", json=payload)

    def mark_item_unplayed(self, user_id, item_id):
        return self.delete(f"/UserPlayedItems/{item_id}?userId={user_id}")

    def set_item_playback_position(self, user_id, item_id, payload):
        return self.post(f"/UserItems/{item_id}/UserData?userId={user_id}", json=payload)

    def stop_session_playback(self, session_id, payload):
        return self.post(f"/Sessions/{session_id}/Playing/Stop", data=payload)

    def send_session_message(self, session_id, message, timeout):
        return self.post(
            f"/Sessions/{session_id}/Message"
            f"?Text={message}&Header=Notification&TimeoutMs={timeout}",
            data={},
        )

    def get_sessions_by_device(self, device_id):
        return self.get_json(f"/Sessions?deviceId={device_id}")

    def get_item_info(self, user_id, item_id):
        return self.get_json(f"/Users/{user_id}/Items/{item_id}")

    def get_user_views(self, user_id):
        return self.get_json(f"/Users/{user_id}/Views?IncludeExternalContent=false")

    def get_devices(self):
        return self.get_json("/Devices")

    def get_virtual_folders(self):
        folders = self.get_json("/Library/VirtualFolders")
        return folders if isinstance(folders, list) else []

    def get_library_paths(self) -> list[dict]:
        result = []
        for folder in self.get_virtual_folders():
            name = folder.get("Name", "")
            for loc in folder.get("Locations", []):
                result.append({"library_name": name, "source_path": loc})
        return result

    def get_json(self, path):
        response = self._http.get(
            self._url(path),
            headers=self.get_headers(self._authenticated_user_info()),
        )
        return response.json()

    def post(self, path, *, data=None, json=None):
        return self._http.post(
            self._url(path),
            data=data,
            json=json,
            headers=self.get_headers(self._authenticated_user_info()),
        )

    def delete(self, path):
        return self._http.delete(
            self._url(path),
            headers=self.get_headers(self._authenticated_user_info()),
        )

    def _authenticated_user_info(self):
        if self.user_info is None:
            raise RuntimeError("JellyfinClient must be authenticated before API calls.")

        return self.user_info

    def _url(self, path: str) -> str:
        if path.startswith(("http://", "https://")):
            return path

        if not path.startswith("/"):
            path = "/" + path

        return self.server_url + path


def _config_value(config, key: str, default=""):
    if hasattr(config, key):
        return getattr(config, key)
    return config.get(key, default)
