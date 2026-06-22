from urllib.parse import quote

from home_cinema_control.media_servers.emby.constants import DEVICE_ID
from home_cinema_control.network.http import get_http_session


class EmbyClient:
    """Low-level HTTP client for the Emby API."""

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
        self._http = http_session or get_http_session("emby")
        self.user_info = None

    @classmethod
    def from_config(cls, config):
        media_server = _media_server_config(config)

        return cls(
            server_url=_config_value(media_server, "server_url"),
            access_token=_config_value(media_server, "access_token"),
            user_id=_config_value(media_server, "user_id"),
            display_name=_config_value(media_server, "display_name"),
        )

    def authenticate(self):
        if not self.access_token:
            raise RuntimeError("Emby authentication is not configured: missing media_server.access_token")

        if not self.user_id:
            raise RuntimeError("Emby authentication is not configured: missing media_server.user_id")

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
            'Version="0.5.1"'
        )

        if user_info:
            auth_string += ',UserId="' + user_info["User"]["Id"] + '"'

        headers = {
            "Accept-encoding": "gzip",
            "Accept-Charset": "UTF-8,*",
            "X-Emby-Authorization": auth_string,
        }

        if user_info:
            headers["X-Emby-Token"] = user_info["AccessToken"]

        return headers

    def notify_playback_started(self, payload):
        return self.post(
            "/emby/Sessions/Playing/?format=json",
            json=payload,
        )

    def report_playback_progress(self, payload):
        return self.post(
            "/emby/Sessions/Playing/Progress?format=json",
            json=payload,
        )

    def notify_playback_stopped(self, payload):
        return self.post(
            "/emby/Sessions/Playing/Stopped?format=json",
            json=payload,
        )

    def mark_item_unplayed(self, user_id, item_id):
        return self.delete(f"/emby/Users/{user_id}/PlayedItems/{item_id}")

    def set_item_playback_position(self, user_id, item_id, payload):
        return self.post(
            f"/emby/Users/{user_id}/Items/{item_id}/UserData?format=json",
            json=payload,
        )

    def stop_session_playback(self, session_id, payload):
        return self.post(
            f"/emby/Sessions/{session_id}/Playing/Stop?format=json",
            data=payload,
        )

    def send_session_message(self, session_id, message, timeout):
        return self.post(
            f"/emby/Sessions/{session_id}/Message"
            f"?Text={quote(message, safe='')}&Header=Notification&TimeoutMs={timeout}",
            data={},
        )

    def set_capabilities(self, payload):
        return self.post(
            "/emby/Sessions/Capabilities/Full?format=json",
            data=payload,
        )

    def get_sessions_by_user(self, user_id):
        return self.get_json(f"/emby/Sessions?ControllableByUserId={user_id}")

    def get_sessions_by_user_and_device(self, user_id, device_id):
        return self.get_json(
            f"/emby/Sessions?ControllableByUserId={user_id}&DeviceID={device_id}"
        )

    def get_sessions_by_device(self, device_id):
        return self.get_json(f"/emby/Sessions?DeviceId={device_id}")

    def get_item_info(self, user_id, item_id):
        return self.get_json(f"/emby/Users/{user_id}/Items/{item_id}")

    def get_item_ancestors(self, item_id):
        return self.get_json(f"/emby/Items/{item_id}/Ancestors")

    def get_user_views(self, user_id):
        return self.get_json(
            f"/emby/Users/{user_id}/Views?IncludeExternalContent=false"
        )

    def get_view_items(self, view_id):
        return self.get_json(f"/emby/Items?parentId={view_id}")

    def get_user_view_items(self, user_id, view_id, item_id):
        return self.get_json(
            f"/emby/Users/{user_id}/Items?parentId={view_id}&item_id={item_id}"
        )

    def get_devices(self):
        return self.get_json("/emby/Devices?")

    def get_selectable_media_folders(self):
        return self.get_json("/emby/Library/SelectableMediaFolders?")

    def get_library_paths(self) -> list[dict]:
        """Return [{library_name, source_path}] for each Emby virtual folder location."""
        folders = self.get_json("/emby/Library/VirtualFolders")
        if not isinstance(folders, list):
            folders = []
        result = []
        for folder in folders:
            name = folder.get("Name", "")
            for loc in folder.get("Locations", []):
                result.append({"library_name": name, "source_path": loc})
        return result

    def get_text(self, path):
        response = self._http.get(
            self._url(path),
            headers=self.get_headers(self._authenticated_user_info()),
        )
        return response.text

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
            raise RuntimeError("EmbyClient must be authenticated before API calls.")

        return self.user_info

    def _url(self, path: str) -> str:
        if path.startswith(("http://", "https://")):
            return path

        if not path.startswith("/"):
            path = "/" + path

        return self.server_url + path


def _media_server_config(config):
    if hasattr(config, "media_server"):
        return config.media_server
    return config.get("media_server") or {}


def _config_value(config, key: str, default=""):
    if hasattr(config, key):
        return getattr(config, key)
    return config.get(key, default)
