import hashlib
import logging
from typing import Any

from home_cinema_control.media_servers.emby.constants import DEVICE_ID
from home_cinema_control.config.manager import (
    get_config_path,
    merge_existing_secrets,
)
from home_cinema_control.media_servers.emby.client import EmbyClient
from home_cinema_control.network.http import get_http_session


BRIDGE_DEVICE_IDS = {DEVICE_ID}
BRIDGE_APP_NAMES = {DEVICE_ID, "Home Cinema Control"}


def check_emby_connection(config: dict):
    client = _authenticated_client(config)
    response = client.set_capabilities(_client_capabilities_payload())
    return response


def load_devices(config: dict) -> None:
    try:
        client = _authenticated_client(config)
        devices = client.get_devices()
        config["devices"] = build_control_device_config(_items_from_response(devices))
    except Exception:
        logging.exception("Error loading Emby control devices")


def load_libraries(config: dict) -> None:
    try:
        client = _authenticated_client(config)
        user_id = _authenticated_user_id(client)
        views = client.get_user_views(user_id)
        playback = config.setdefault("playback", {})
        playback["libraries"] = build_library_config(
            _items_from_response(views),
            existing_libraries=playback.get("libraries", []),
        )
    except Exception:
        logging.exception("Error loading Emby libraries")


def load_selectable_folders(config: dict) -> None:
    try:
        client = _authenticated_client(config)
        media_folders = client.get_selectable_media_folders()
        playback = config.setdefault("playback", {})
        playback["path_mappings"] = build_selectable_folder_servers(
            _items_from_response(media_folders),
            libraries=playback.get("libraries", []),
            existing_servers=playback.get("path_mappings", []),
            enable_all_libraries=bool(playback.get("use_all_libraries", False)),
        )
    except Exception:
        logging.exception("Error loading Emby selectable folders")


def load_selectable_media_folders(config: dict) -> None:
    load_selectable_folders(config)


def fetch_library_paths(config: dict) -> list[dict]:
    """Return [{library_name, source_path}] from Emby virtual folders. config must include secrets."""
    client = _authenticated_client(config)
    return client.get_library_paths()


def build_library_config(
    views: list[dict[str, Any]],
    *,
    existing_libraries: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    existing_by_id = {
        str(library.get("Id", "")): library
        for library in existing_libraries
        if library.get("Id")
    }

    libraries = []
    for view in views:
        view_id = str(view.get("Id", ""))
        if not view_id:
            continue

        existing_library = existing_by_id.get(view_id, {})
        libraries.append(
            {
                "Name": view.get("Name", ""),
                "Id": view_id,
                "Active": bool(existing_library.get("Active", False)),
            }
        )

    return libraries


def build_selectable_folder_servers(
    media_folders: list[dict[str, Any]],
    *,
    libraries: list[dict[str, Any]],
    existing_servers: list[dict[str, Any]],
    enable_all_libraries: bool,
) -> list[dict[str, Any]]:
    existing_by_emby_path = {
        str(server.get("source_path", "")): server
        for server in existing_servers
        if server.get("source_path")
    }

    servers = []
    for folder in media_folders:
        folder_name = str(folder.get("Name", ""))
        if not enable_all_libraries and not is_library_active(libraries, folder_name):
            continue

        for index, subfolder in enumerate(folder.get("SubFolders", []), start=1):
            emby_path = str(subfolder.get("Path", ""))
            if not emby_path:
                continue

            server = {
                "Id": subfolder.get("Id", ""),
                "name": folder_name if index == 1 else f"{folder_name}({index})",
                "source_path": emby_path,
                "player_path": "/",
            }

            existing_server = existing_by_emby_path.get(emby_path)
            if existing_server:
                server.update(
                    {
                        "name": existing_server.get("name", server["name"]),
                        "player_path": existing_server.get("player_path", server["player_path"]),
                    }
                )
                if "verified" in existing_server:
                    server["verified"] = existing_server["verified"]

            servers.append(server)

    return servers


def build_control_device_config(devices: list[dict[str, Any]]) -> list[dict[str, Any]]:
    control_devices = []

    for device in devices:
        reported_device_id = str(device.get("ReportedDeviceId", "")).strip()
        if not reported_device_id or reported_device_id in BRIDGE_DEVICE_IDS:
            continue

        app_name = str(device.get("AppName", "")).strip()
        if app_name in BRIDGE_APP_NAMES:
            continue

        name = str(device.get("Name", "")).strip()
        if not name:
            continue

        display_name = f"{name} / {app_name}" if app_name else name
        control_device = dict(device)
        control_device["Name"] = display_name
        control_device["Id"] = reported_device_id
        control_devices.append(control_device)

    return control_devices


def is_library_active(libraries: list[dict[str, Any]], library_name: str) -> bool:
    for library in libraries:
        if library.get("Name") == library_name:
            return bool(library.get("Active", False))

    return False


def configure_emby_token(config: dict, credentials: dict) -> dict:
    config = _public_config_with_existing_secrets(config)

    media_server = dict(config.get("media_server") or {})

    server_url = str(media_server.get("server_url", "")).strip().rstrip("/")
    user_name = str(credentials.get("user_name", "")).strip()
    password = str(credentials.get("password", ""))

    if not server_url:
        raise RuntimeError("Missing media_server.server_url")

    if not user_name:
        raise RuntimeError("Missing temporary Emby user name")

    if not password:
        raise RuntimeError("Missing temporary Emby password")

    auth_response = _authenticate_with_temporary_password(
        server_url=server_url,
        user_name=user_name,
        password=password,
    )

    access_token = auth_response.get("AccessToken", "")
    user = auth_response.get("User") or {}
    user_id = user.get("Id", "")
    display_name = user.get("Name") or user_name

    if not access_token or not user_id:
        raise RuntimeError("Emby authentication response did not include AccessToken/User.Id")

    media_server["type"] = "emby"
    media_server["server_url"] = server_url
    media_server["display_name"] = display_name
    media_server["access_token"] = access_token
    media_server["user_id"] = user_id
    media_server["access_token_configured"] = True

    config["media_server"] = media_server

    _remove_legacy_emby_keys(config)

    return config

def _authenticated_client(config: dict) -> EmbyClient:
    effective_config = _public_config_with_existing_secrets(config)

    client = EmbyClient.from_config(effective_config)
    client.authenticate()

    return client


def _public_config_with_existing_secrets(config: dict) -> dict:
    return merge_existing_secrets(get_config_path(), config)


def _authenticated_user_id(client: EmbyClient) -> str:
    user_info = client.user_info or {}
    user = user_info.get("User") or {}
    user_id = user.get("Id", "")

    if not user_id:
        raise RuntimeError("Emby authentication is not configured: missing media_server.user_id")

    return user_id


def _authenticate_with_temporary_password(
    *,
    server_url: str,
    user_name: str,
    password: str,
) -> dict:
    password_bytes = password.encode("utf-8")
    password_sha = hashlib.sha1(password_bytes).hexdigest()

    response = get_http_session("emby").post(
        f"{server_url}/Users/AuthenticateByName?format=json",
        data={
            "username": user_name,
            "password": password_sha,
            "pw": password,
        },
        headers={
            "X-Emby-Authorization": (
                f'MediaBrowser Client="Home Cinema Control",'
                f'Device="Home Cinema Control",'
                f"DeviceId=${DEVICE_ID},"
                f'Version="0.5"'
            )
        },
    )

    response.raise_for_status()
    return response.json()


def _items_from_response(response: Any) -> list[dict[str, Any]]:
    if isinstance(response, dict):
        items = response.get("Items", [])
        return items if isinstance(items, list) else []

    return response if isinstance(response, list) else []


def _client_capabilities_payload() -> dict:
    return {
        "IconUrl": "https://img.alicdn.com/imgextra/i1/1840220527/O1CN018lXYlv1FlPES6Bgcw_!!1840220527.png",
        "SupportsMediaControl": True,
        "PlayableMediaTypes": [
            "Video",
            "Audio",
        ],
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


def _remove_legacy_emby_keys(config: dict) -> None:
    for key in [
        "emby_server",
        "user_name",
        "user_password",
        "user_password_configured",
        "emby_access_token",
        "emby_user_id",
        "emby_access_token_configured",
        "media_server_login",
    ]:
        config.pop(key, None)
