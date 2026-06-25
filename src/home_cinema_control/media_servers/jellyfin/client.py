from __future__ import annotations

from home_cinema_control import __version__
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
            f'Version="{__version__}"'
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
        # Unlike Emby's equivalent (Text/Header/TimeoutMs as query params,
        # empty body), Jellyfin's /Sessions/{Id}/Message binds these from a
        # JSON request body — confirmed against a real Jellyfin server,
        # which 400s with "The Text field is required" when Text is only on
        # the query string. quote() is no longer needed: a JSON body doesn't
        # have query-string escaping concerns.
        return self.post(
            f"/Sessions/{session_id}/Message",
            json={"Text": message, "Header": "Notification", "TimeoutMs": timeout},
        )

    def get_sessions_by_device(self, device_id):
        return self.get_json(f"/Sessions?deviceId={device_id}")

    def get_sessions_by_user(self, user_id):
        """Sessions narrowed server-side to one user.

        `controllableByUserId` (`Guid?`) confirmed against Jellyfin server
        source — `SessionController.GetSessions`,
        Jellyfin.Api/Controllers/SessionController.cs (jellyfin/jellyfin,
        master branch) — not a guess. Callers still filter the result
        client-side too (see JellyfinSession.find_controlling_session_id),
        since that's the actual correctness guarantee; this param is purely
        the bandwidth optimization Pedro asked for.
        """
        return self.get_json(f"/Sessions?controllableByUserId={user_id}")

    def get_item_info(self, user_id, item_id):
        return self.get_json(f"/Users/{user_id}/Items/{item_id}")

    def get_user_views(self, user_id):
        # Real bug, found by checking this against Jellyfin's server source
        # rather than assuming the old code was right: /Users/{userId}/Views
        # is not a route Jellyfin's UserViewsController defines at all. The
        # real route is GET /UserViews, with userId as a query parameter, not
        # a path segment (UserViewsController.GetUserViews,
        # Jellyfin.Api/Controllers/UserViewsController.cs). This had never
        # been exercised successfully this session: the discard-return-value
        # bug in ModuleMediaServerSetupService (fixed earlier) was silently
        # absorbing whatever this call actually did, masking whether it
        # worked at all.
        return self.get_json(f"/UserViews?userId={user_id}&includeExternalContent=false")

    def get_devices(self):
        # Confirmed route against Jellyfin server source — DevicesController
        # has no own [Route], so this relies on the framework's per-controller
        # convention (matches every other un-prefixed PascalCase route this
        # client already uses successfully, e.g. /Sessions, /Devices was
        # also the route this integration was originally built and verified
        # against). Separately confirmed via source: DevicesController is
        # [Authorize(Policy = Policies.RequiresElevation)] — this call 403s
        # unless the authenticated Jellyfin user is an administrator. Not
        # exercised this session; if Jellyfin device discovery in HCC's setup
        # screen fails, check that first.
        return self.get_json("/Devices")

    def get_virtual_folders(self):
        # Confirmed route against Jellyfin server source: LibraryStructureController
        # has [Route("Library/VirtualFolders")]. Also [Authorize(Policy =
        # Policies.FirstTimeSetupOrElevated)] — same administrator requirement
        # as get_devices above, not exercised this session.
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
